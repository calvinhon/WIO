import os
import base64
import json
import sqlite3
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import re
import itertools
import pikepdf

class EnhancedGmailClient:
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

    def __init__(self, credentials_file='credentials.json', db_path='email_data.db'):
        self.credentials_file = credentials_file
        self.service = None
        self.authenticate()
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS emails (
                id TEXT PRIMARY KEY,
                subject TEXT,
                sender TEXT,
                date TEXT,
                snippet TEXT,
                password_hints TEXT,
                password_rules TEXT,
                attachments TEXT,
                timestamp INTEGER,
                email_body TEXT,
                processed_date TEXT
            )
        ''')
        
        # Create a table for personal data used in password generation
        c.execute('''
            CREATE TABLE IF NOT EXISTS personal_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_type TEXT,
                data_value TEXT,
                description TEXT,
                created_date TEXT
            )
        ''')
        
        conn.commit()
        conn.close()

    def add_personal_data(self, data_type, data_value, description=""):
        """Add personal data that might be used in passwords"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            INSERT OR REPLACE INTO personal_data (data_type, data_value, description, created_date)
            VALUES (?, ?, ?, ?)
        ''', (data_type, data_value, description, datetime.now().isoformat()))
        conn.commit()
        conn.close()

    def get_personal_data(self):
        """Retrieve all personal data for password generation"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT data_type, data_value, description FROM personal_data')
        rows = c.fetchall()
        conn.close()
        return rows

    def get_latest_email_timestamp(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT MAX(timestamp) FROM emails')
        result = c.fetchone()
        conn.close()
        return result[0] if result and result[0] else None

    def authenticate(self):
        creds = None
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', self.SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_file, self.SCOPES)
                creds = flow.run_local_server(port=0)
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        self.service = build('gmail', 'v1', credentials=creds)

    def search_credit_card_emails(self, months_back=2):
        """Search for credit card emails within the last specified months"""
        # Calculate date for query (2 months back)
        past_date = datetime.now() - timedelta(days=months_back * 30)
        after_str = past_date.strftime('%Y/%m/%d')
        
        base_query = (
            'has:attachment filename:pdf '
            'subject:(statement OR "credit card" OR bank OR "account statement") '
            #f'after:{after_str} '
            #'from:('
            #'bankfab.com OR '
            #'emiratesnbd.com OR '
            #'adcb.ae OR adcb.com OR '
            #'adib.ae OR '
            #'dib.ae OR '
            #'emiratesislamic.ae OR '
            #'cbd.ae OR '
            #'mashreqbank.com OR '
            #'rakbank.ae OR '
            #'nbf.ae OR '
            #'nbruq.ae OR '
            #'bankofsharjah.com OR '
            #'uab.ae OR '
            #'hsbc.ae OR '
            #'citibank.ae OR '
            #'sc.com OR '
            #'barclays.ae OR '
            #'bnpparibas.ae OR '
            #'bankofbaroda.ae OR '
            #'hbl.com OR '
            #'habibbank.com OR '
            #'arabbank.ae OR '
            #'alhilalbank.ae OR '
            #'ajmanbank.ae OR '
            #'sib.ae OR '
            #'eibank.com'
            #')'
        )

        # Only fetch emails newer than what we already have
        latest_ts = self.get_latest_email_timestamp()
        if latest_ts:
            after_existing = datetime.utcfromtimestamp(latest_ts).strftime('%Y/%m/%d')
            base_query += f' after:{after_existing}'

        try:
            results = self.service.users().messages().list(
                userId='me', q=base_query, maxResults=100).execute()
            messages = results.get('messages', [])
            print(f"Found {len(messages)} potentially new statement emails")
            return messages
        except HttpError as error:
            print(f'An error occurred: {error}')
            return []

    def is_already_processed(self, msg_id):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT id FROM emails WHERE id = ?', (msg_id,))
        result = c.fetchone()
        conn.close()
        return result is not None

    def get_email_body(self, msg_id):
        """Fetch the plain text body of the email"""
        try:
            message = self.service.users().messages().get(userId='me', id=msg_id, format='full').execute()
        except HttpError as error:
            print(f"Failed to fetch email body for {msg_id}: {error}")
            return ""

        def _get_parts(parts):
            for part in parts:
                mime_type = part.get('mimeType', '')
                body = part.get('body', {})
                data = body.get('data')
                if mime_type == 'text/plain' and data:
                    try:
                        decoded = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                        return decoded
                    except Exception:
                        continue
                elif part.get('parts'):
                    result = _get_parts(part['parts'])
                    if result:
                        return result
            return None

        payload = message.get('payload', {})
        parts = payload.get('parts', [])

        if not parts:
            body = payload.get('body', {}).get('data')
            if body:
                try:
                    return base64.urlsafe_b64decode(body).decode('utf-8', errors='ignore')
                except Exception:
                    return ""

        text_body = _get_parts(parts)
        return text_body if text_body else ""

    def extract_password_rules_and_hints(self, email_body, subject, sender):
        """Extract password rules and hints from email content"""
        rules = []
        hints = []
        
        if not email_body:
            return hints, rules
        
        # Common password rule patterns
        rule_patterns = [
            r'password (is|will be|format|structure|contains)[\s:]*([^\n.]{1,100})',
            r'pdf password[\s:]*([^\n.]{1,100})',
            r'to open.*password[\s:]*([^\n.]{1,100})',
            r'statement password[\s:]*([^\n.]{1,100})',
            r'password.*last (\d+) digits',
            r'password.*birth date',
            r'password.*mobile number',
            r'password.*card number',
            r'password.*account number',
            r'password.*first name',
            r'password.*last name',
            r'password.*date of birth',
            r'password.*phone number',
            r'password.*DDMMYYYY',
            r'password.*DD/MM/YYYY',
            r'password.*YYYYMMDD',
            r'combination of.*password',
            r'password.*combination.*of'
        ]
        
        # Extract rules
        for pattern in rule_patterns:
            matches = re.finditer(pattern, email_body, re.IGNORECASE)
            for match in matches:
                rule_text = match.group(0).strip()
                if len(rule_text) > 10:  # Filter out very short matches
                    rules.append(rule_text)
        
        # Extract specific password hints
        hint_patterns = [
            r'password[\s:=]*([A-Za-z0-9@#$%^&*()_+-=\[\]{}|;:,.<>?]{4,20})',
            r'pdf password[\s:=]*([A-Za-z0-9@#$%^&*()_+-=\[\]{}|;:,.<>?]{4,20})',
            r'to open.*password[\s:=]*([A-Za-z0-9@#$%^&*()_+-=\[\]{}|;:,.<>?]{4,20})',
        ]
        
        for pattern in hint_patterns:
            matches = re.finditer(pattern, email_body, re.IGNORECASE)
            for match in matches:
                hint = match.group(1).strip()
                if hint and len(hint) >= 4:
                    hints.append(hint)
        
        # Extract dates and numbers that might be passwords
        dates = re.findall(r'\b\d{2}/\d{2}/\d{4}\b', email_body)
        hints.extend([d.replace('/', '') for d in dates])
        
        dates_dash = re.findall(r'\b\d{2}-\d{2}-\d{4}\b', email_body)
        hints.extend([d.replace('-', '') for d in dates_dash])
        
        four_to_eight_digits = re.findall(r'\b\d{4,8}\b', email_body)
        hints.extend(four_to_eight_digits)
        
        # Extract words that might be hints (containing both letters and numbers)
        mixed_hints = re.findall(r'\b[A-Za-z]*\d+[A-Za-z]*\b|\b\d+[A-Za-z]+\d*\b', email_body)
        hints.extend([h for h in mixed_hints if len(h) >= 4])
        
        return list(set(hints)), list(set(rules))

    def download_pdf_attachments(self, msg_id, payload, download_dir='downloads'):
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
        downloaded_files = []

        def extract(parts):
            for part in parts:
                filename = part.get('filename', '')
                if filename.lower().endswith('.pdf'):
                    body = part['body']
                    data = body.get('data')
                    if not data and 'attachmentId' in body:
                        att = self.service.users().messages().attachments().get(
                            userId='me', messageId=msg_id, id=body['attachmentId']).execute()
                        data = att['data']
                    if data:
                        # Create unique filename with timestamp
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        name, ext = os.path.splitext(filename)
                        unique_filename = f"{name}_{timestamp}{ext}"
                        filepath = os.path.join(download_dir, unique_filename)
                        with open(filepath, 'wb') as f:
                            f.write(base64.urlsafe_b64decode(data))
                        downloaded_files.append(filepath)
                if 'parts' in part:
                    extract(part['parts'])

        extract(payload.get('parts', []))
        return downloaded_files

    def store_email_metadata(self, msg_id, subject, sender, date, snippet, password_hints, password_rules, attachments, email_body):
        try:
            timestamp = int(datetime.strptime(date, '%a, %d %b %Y %H:%M:%S %z').timestamp())
        except Exception:
            timestamp = int(datetime.utcnow().timestamp())

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            INSERT OR REPLACE INTO emails (id, subject, sender, date, snippet, password_hints, password_rules, attachments, timestamp, email_body, processed_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (msg_id, subject, sender, date, snippet, 
              json.dumps(password_hints), json.dumps(password_rules), 
              json.dumps(attachments), timestamp, email_body, datetime.now().isoformat()))
        conn.commit()
        conn.close()

    def get_message_details(self, msg_id):
        try:
            message = self.service.users().messages().get(userId='me', id=msg_id, format='full').execute()
            return message
        except HttpError as error:
            print(f'An error occurred: {error}')
            return None

    def process_new_statements(self):
        """Process new statement emails and store enhanced metadata"""
        new_emails = self.search_credit_card_emails()
        processed_count = 0
        
        for msg in new_emails:
            msg_id = msg['id']
            if self.is_already_processed(msg_id):
                continue

            message = self.get_message_details(msg_id)
            if not message:
                continue

            headers = message['payload'].get('headers', [])
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), '')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
            snippet = message.get('snippet', '')
            payload = message.get('payload', {})

            # Get full email body
            email_body = self.get_email_body(msg_id)
            
            # Extract password rules and hints
            password_hints, password_rules = self.extract_password_rules_and_hints(email_body, subject, sender)
            
            # Download attachments
            attachments = self.download_pdf_attachments(msg_id, payload)

            # Store everything in database
            self.store_email_metadata(msg_id, subject, sender, date, snippet, 
                                    password_hints, password_rules, attachments, email_body)
            
            print(f"Processed email: {subject}")
            print(f"  Password hints: {password_hints}")
            print(f"  Password rules: {password_rules}")
            print(f"  Attachments: {len(attachments)}")
            processed_count += 1

        if processed_count == 0:
            print("No new statement emails to process.")
        else:
            print(f"Successfully processed {processed_count} new emails.")

    def generate_password_candidates(self, hints, rules, personal_data):
        """Generate password candidates based on hints, rules, and personal data"""
        candidates = set()
        
        # Add direct hints
        candidates.update(hints)
        
        # Add personal data
        for data_type, data_value, description in personal_data:
            candidates.add(data_value)
            
            # Generate variations based on data type
            if data_type == 'date_of_birth':
                # Try different date formats
                if len(data_value) == 8:  # DDMMYYYY
                    candidates.add(data_value)
                    candidates.add(data_value[:6])  # DDMMYY
                    candidates.add(data_value[4:] + data_value[:4])  # YYYYMMDD
                    candidates.add(data_value[2:6])  # MMYY
                    
            elif data_type == 'mobile_number':
                # Last 4, 6, 8 digits
                candidates.add(data_value[-4:])
                candidates.add(data_value[-6:])
                candidates.add(data_value[-8:])
                
            elif data_type == 'card_number':
                # Last 4 digits
                candidates.add(data_value[-4:])
                
            elif data_type == 'name':
                # Lowercase, uppercase, title case
                candidates.add(data_value.lower())
                candidates.add(data_value.upper())
                candidates.add(data_value.title())
        
        # Generate combinations
        personal_values = [data_value for _, data_value, _ in personal_data]
        
        # Combine hints with personal data
        for hint in hints:
            for personal_value in personal_values:
                candidates.add(f"{hint}{personal_value}")
                candidates.add(f"{personal_value}{hint}")
        
        # Generate date-based passwords
        now = datetime.now()
        for i in range(12):  # Last 12 months
            date = now - timedelta(days=30 * i)
            candidates.add(date.strftime("%d%m%Y"))
            candidates.add(date.strftime("%d%m%y"))
            candidates.add(date.strftime("%Y%m%d"))
            candidates.add(date.strftime("%m%Y"))
        
        return list(candidates)

    def unlock_pdfs(self):
        """Unlock PDFs using extracted hints and personal data"""
        # Get personal data
        personal_data = self.get_personal_data()
        
        # Get all emails with attachments
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            SELECT id, subject, sender, password_hints, password_rules, attachments 
            FROM emails 
            WHERE attachments IS NOT NULL AND attachments != "[]"
        ''')
        rows = c.fetchall()
        conn.close()
        
        unlocked_count = 0
        total_pdfs = 0
        
        for row in rows:
            msg_id, subject, sender, hints_json, rules_json, attachments_json = row
            
            # Parse JSON data
            hints = json.loads(hints_json) if hints_json else []
            rules = json.loads(rules_json) if rules_json else []
            attachments = json.loads(attachments_json) if attachments_json else []
            
            print(f"\nProcessing email: {subject}")
            print(f"Password rules found: {len(rules)}")
            print(f"Password hints found: {len(hints)}")
            
            # Generate password candidates
            candidates = self.generate_password_candidates(hints, rules, personal_data)
            print(f"Generated {len(candidates)} password candidates")
            
            # Try to unlock each PDF
            for pdf_path in attachments:
                total_pdfs += 1
                if os.path.exists(pdf_path):
                    unlocked_path = self.try_unlock_pdf(pdf_path, candidates)
                    if unlocked_path:
                        unlocked_count += 1
                        print(f"✅ Unlocked: {pdf_path}")
                    else:
                        print(f"❌ Failed to unlock: {pdf_path}")
                else:
                    print(f"⚠️ File not found: {pdf_path}")
        
        print(f"\n📊 Summary: {unlocked_count}/{total_pdfs} PDFs unlocked successfully")

    def try_unlock_pdf(self, pdf_path, password_candidates):
        """Try to unlock a PDF with given password candidates"""
        try:
            # Try without password first
            pdf = pikepdf.open(pdf_path)
            pdf.close()
            print(f"📄 PDF is not password protected: {pdf_path}")
            return pdf_path
        except pikepdf._qpdf.PasswordError:
            pass
        
        # Try each password candidate
        for password in password_candidates:
            try:
                pdf = pikepdf.open(pdf_path, password=str(password))
                
                # Save unlocked version
                unlocked_path = pdf_path.replace('.pdf', '_unlocked.pdf')
                pdf.save(unlocked_path)
                pdf.close()
                
                print(f"🔓 Unlocked with password: {password}")
                return unlocked_path
                
            except pikepdf._qpdf.PasswordError:
                continue
            except Exception as e:
                print(f"Error trying password {password}: {e}")
                continue
        
        return None


# Example usage and setup
if __name__ == "__main__":
    # Initialize client
    client = EnhancedGmailClient()
    
    # Add some sample personal data (you should customize this)
    client.add_personal_data('date_of_birth', '01011990', 'Date of birth in DDMMYYYY format')
    client.add_personal_data('mobile_number', '1234567890', 'Mobile number')
    client.add_personal_data('name', 'John', 'First name')
    client.add_personal_data('card_number', '1234567890123456', 'Credit card number')
    
    # Process new emails
    print("Processing new statement emails...")
    client.process_new_statements()
    
    # Try to unlock PDFs
    print("\nAttempting to unlock PDFs...")
    client.unlock_pdfs()