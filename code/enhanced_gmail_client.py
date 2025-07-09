import os
import base64
import json
import sqlite3
import logging
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import re
import itertools
import pikepdf

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PasswordCandidate:
    password: str
    confidence: float
    source: str
    reasoning: str

class EnhancedGmailClient:
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

    def __init__(self, credentials_file='credentials.json', db_path='email_data.db'):
        self.credentials_file = credentials_file
        self.service = None
        self.authenticate()
        self.db_path = db_path
        self._init_db()
        self.llm_manager = None
        self._setup_llm()

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
        
        # Create table for password candidates
        c.execute('''
            CREATE TABLE IF NOT EXISTS password_candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_id TEXT,
                password TEXT,
                confidence REAL,
                source TEXT,
                reasoning TEXT,
                tested BOOLEAN DEFAULT 0,
                works BOOLEAN DEFAULT 0,
                created_date TEXT,
                FOREIGN KEY (email_id) REFERENCES emails (id)
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
    
    def get_personal_data_organized(self) -> Dict[str, List[str]]:
        """Retrieve personal data organized by type"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT data_type, data_value, description FROM personal_data')
        rows = c.fetchall()
        conn.close()
        
        data = {}
        for data_type, data_value, description in rows:
            if data_type not in data:
                data[data_type] = []
            data[data_type].append(data_value)
        
        return data

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

    def extract_bank_context(self, email_body: str, sender: str) -> Dict[str, str]:
        """Extract bank-specific context from email"""
        bank_patterns = {
            'fab': r'(fab|first abu dhabi bank)',
            'adcb': r'(adcb|abu dhabi commercial bank)',
            'enbd': r'(enbd|emirates nbd)',
            'adib': r'(adib|abu dhabi islamic bank)',
            'dib': r'(dib|dubai islamic bank)',
            'mashreq': r'mashreq',
            'rakbank': r'(rak|rakbank)',
            'nbf': r'(nbf|national bank of fujairah)',
            'hsbc': r'hsbc',
            'citibank': r'citi',
            'sc': r'standard chartered'
        }
        
        context = {
            'bank': 'unknown',
            'account_numbers': [],
            'card_numbers': [],
            'dates': [],
            'amounts': []
        }
        
        # Identify bank
        sender_lower = sender.lower()
        email_lower = email_body.lower()
        
        for bank, pattern in bank_patterns.items():
            if re.search(pattern, sender_lower) or re.search(pattern, email_lower):
                context['bank'] = bank
                break
        
        # Extract account numbers (masked)
        account_patterns = [
            r'account.*?(\d{4,6})',
            r'a/c.*?(\d{4,6})',
            r'account ending.*?(\d{4,6})'
        ]
        
        for pattern in account_patterns:
            matches = re.finditer(pattern, email_body, re.IGNORECASE)
            context['account_numbers'].extend([m.group(1) for m in matches])
        
        # Extract card numbers (last 4 digits)
        card_patterns = [
            r'card.*?(\d{4})',
            r'credit card.*?(\d{4})',
            r'ending.*?(\d{4})'
        ]
        
        for pattern in card_patterns:
            matches = re.finditer(pattern, email_body, re.IGNORECASE)
            context['card_numbers'].extend([m.group(1) for m in matches])
        
        # Extract dates
        date_patterns = [
            r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b',
            r'\b(\d{2,4}[/-]\d{1,2}[/-]\d{1,2})\b'
        ]
        
        for pattern in date_patterns:
            matches = re.finditer(pattern, email_body)
            context['dates'].extend([m.group(1) for m in matches])
        
        return context

    def generate_llm_prompt(self, email_body: str, password_rules: List[str], 
                          password_hints: List[str], personal_data: Dict[str, List[str]], 
                          bank_context: Dict[str, str]) -> str:
        """Generate a comprehensive prompt for the LLM"""
        
        prompt = f"""You are an expert password analyst. Your task is to analyze bank statement emails and generate the most likely PDF password based on the provided information.

EMAIL CONTENT:
{email_body[:1000]}...

PASSWORD RULES FOUND:
{chr(10).join(password_rules) if password_rules else 'None specified'}

PASSWORD HINTS FOUND:
{', '.join(password_hints) if password_hints else 'None found'}

PERSONAL DATA AVAILABLE:
"""
        
        for data_type, values in personal_data.items():
            prompt += f"- {data_type}: {', '.join(values[:3])}\n"
        
        prompt += f"""
BANK CONTEXT:
- Bank: {bank_context['bank']}
- Account Numbers: {', '.join(bank_context['account_numbers'])}
- Card Numbers: {', '.join(bank_context['card_numbers'])}
- Dates Found: {', '.join(bank_context['dates'][:5])}

COMMON BANK PASSWORD PATTERNS:
1. Last 4 digits of card/account number
2. Date of birth (DDMMYYYY, MMDDYYYY)
3. Mobile number last 4 digits
4. First name + last 4 digits of card
5. DDMMYYYY format dates
6. Account number variations

TASK: Generate the 5 most likely passwords based on this analysis. For each password, provide:
1. The password itself
2. Confidence level (1-10)
3. Reasoning for this choice

Format your response as JSON:
{{
  "passwords": [
    {{
      "password": "12345678",
      "confidence": 8,
      "reasoning": "Based on rule mentioning last 4 digits of card number (5678) combined with birth date (1234)"
    }}
  ]
}}

RESPOND ONLY WITH THE JSON, NO OTHER TEXT.
"""
        
        return prompt
    
    def parse_llm_response(self, response: str) -> List[PasswordCandidate]:
        """Parse LLM response into password candidates"""
        candidates = []
        
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                data = json.loads(json_str)
                
                for pwd_data in data.get('passwords', []):
                    candidate = PasswordCandidate(
                        password=pwd_data.get('password', ''),
                        confidence=float(pwd_data.get('confidence', 0)),
                        source='llm',
                        reasoning=pwd_data.get('reasoning', '')
                    )
                    candidates.append(candidate)
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
        
        return candidates
    
    def generate_rule_based_passwords(self, email_body: str, password_rules: List[str], 
                                    password_hints: List[str], personal_data: Dict[str, List[str]], 
                                    bank_context: Dict[str, str]) -> List[PasswordCandidate]:
        """Generate password candidates using rule-based approach"""
        candidates = []
        
        # Direct hints
        for hint in password_hints:
            if len(hint) >= 4:
                candidates.append(PasswordCandidate(
                    password=hint,
                    confidence=9.0,
                    source='direct_hint',
                    reasoning=f'Found direct password hint: {hint}'
                ))
        
        # Personal data combinations
        if 'birth_date' in personal_data:
            for date in personal_data['birth_date']:
                # Different date formats
                date_clean = re.sub(r'[/-]', '', date)
                candidates.append(PasswordCandidate(
                    password=date_clean,
                    confidence=7.0,
                    source='birth_date',
                    reasoning=f'Birth date format: {date_clean}'
                ))
        
        # Card/Account number combinations
        for card_num in bank_context['card_numbers']:
            candidates.append(PasswordCandidate(
                password=card_num,
                confidence=8.0,
                source='card_number',
                reasoning=f'Last 4 digits of card: {card_num}'
            ))
        
        for acc_num in bank_context['account_numbers']:
            candidates.append(PasswordCandidate(
                password=acc_num,
                confidence=7.0,
                source='account_number',
                reasoning=f'Account number digits: {acc_num}'
            ))
        
        # Date combinations from email
        for date in bank_context['dates']:
            date_clean = re.sub(r'[/-]', '', date)
            if len(date_clean) >= 6:
                candidates.append(PasswordCandidate(
                    password=date_clean,
                    confidence=6.0,
                    source='email_date',
                    reasoning=f'Date from email: {date_clean}'
                ))
        
        # Mobile number combinations
        if 'mobile_number' in personal_data:
            for mobile in personal_data['mobile_number']:
                last_4 = mobile[-4:] if len(mobile) >= 4 else mobile
                candidates.append(PasswordCandidate(
                    password=last_4,
                    confidence=6.0,
                    source='mobile_number',
                    reasoning=f'Last 4 digits of mobile: {last_4}'
                ))
        
        # Name combinations
        if 'first_name' in personal_data and bank_context['card_numbers']:
            for name in personal_data['first_name']:
                for card in bank_context['card_numbers']:
                    combo = name.lower() + card
                    candidates.append(PasswordCandidate(
                        password=combo,
                        confidence=5.0,
                        source='name_card_combo',
                        reasoning=f'First name + card digits: {combo}'
                    ))
        
        return candidates
    
    def generate_passwords_for_email(self, email_id: str) -> List[PasswordCandidate]:
        """Generate password candidates for a specific email"""
        # Get email data
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            SELECT email_body, password_hints, password_rules, sender, subject 
            FROM emails WHERE id = ?
        ''', (email_id,))
        
        row = c.fetchone()
        conn.close()
        
        if not row:
            return []
        
        email_body, password_hints_str, password_rules_str, sender, subject = row
        
        # Parse stored data
        password_hints = json.loads(password_hints_str) if password_hints_str else []
        password_rules = json.loads(password_rules_str) if password_rules_str else []
        
        # Get personal data and bank context
        personal_data = self.get_personal_data_organized()
        bank_context = self.extract_bank_context(email_body, sender)
        
        candidates = []
        
        # Try LLM generation first
        if self.llm_manager:
            try:
                prompt = self.generate_llm_prompt(
                    email_body, password_rules, password_hints, 
                    personal_data, bank_context
                )
                
                response = self.llm_manager.generate_response(prompt)
                llm_candidates = self.parse_llm_response(response)
                candidates.extend(llm_candidates)
                
                logger.info(f"Generated {len(llm_candidates)} candidates from LLM")
                
            except Exception as e:
                logger.error(f"LLM generation failed: {e}")
        
        # Always generate rule-based candidates as backup
        rule_candidates = self.generate_rule_based_passwords(
            email_body, password_rules, password_hints, 
            personal_data, bank_context
        )
        candidates.extend(rule_candidates)
        
        # Sort by confidence and remove duplicates
        seen = set()
        unique_candidates = []
        for candidate in sorted(candidates, key=lambda x: x.confidence, reverse=True):
            if candidate.password not in seen:
                seen.add(candidate.password)
                unique_candidates.append(candidate)
        
        return unique_candidates[:20]  # Return top 20 candidates
    
    def save_password_candidates(self, email_id: str, candidates: List[PasswordCandidate]):
        """Save password candidates to database"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Clear existing candidates for this email
        c.execute('DELETE FROM password_candidates WHERE email_id = ?', (email_id,))
        
        # Insert new candidates
        for candidate in candidates:
            c.execute('''
                INSERT INTO password_candidates 
                (email_id, password, confidence, source, reasoning, created_date)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                email_id, candidate.password, candidate.confidence, 
                candidate.source, candidate.reasoning, datetime.now().isoformat()
            ))
        
        conn.commit()
        conn.close()
    
    def mark_password_result(self, email_id: str, password: str, works: bool):
        """Mark password test result in database"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            UPDATE password_candidates 
            SET tested = 1, works = ? 
            WHERE email_id = ? AND password = ?
        ''', (works, email_id, password))
        conn.commit()
        conn.close()

    def unlock_pdfs(self):
        """Enhanced PDF unlocking using integrated password generation"""
        # Get personal data
        personal_data = self.get_personal_data()
        
        # Get all emails with attachments
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            SELECT id, subject, sender, password_hints, password_rules, attachments, email_body
            FROM emails 
            WHERE attachments IS NOT NULL AND attachments != "[]"
        ''')
        rows = c.fetchall()
        conn.close()
        
        unlocked_count = 0
        total_pdfs = 0
        
        for row in rows:
            msg_id, subject, sender, hints_json, rules_json, attachments_json, email_body = row
            
            # Parse JSON data
            hints = json.loads(hints_json) if hints_json else []
            rules = json.loads(rules_json) if rules_json else []
            attachments = json.loads(attachments_json) if attachments_json else []
            
            print(f"\nProcessing email: {subject}")
            print(f"Password rules found: {len(rules)}")
            print(f"Password hints found: {len(hints)}")
            
            # Generate enhanced password candidates
            candidates = self.generate_passwords_for_email(msg_id)
            
            # If no candidates from enhanced method, fallback to basic method
            if not candidates:
                basic_candidates = self.generate_password_candidates(hints, rules, personal_data, email_body, sender, msg_id)
                candidates = [PasswordCandidate(password=pwd, confidence=5.0, source='fallback', reasoning='Basic generation') for pwd in basic_candidates]
            
            # Save candidates to database
            self.save_password_candidates(msg_id, candidates)
            
            print(f"Generated {len(candidates)} password candidates")
            
            # Try to unlock each PDF
            for pdf_path in attachments:
                total_pdfs += 1
                if os.path.exists(pdf_path):
                    unlocked_path = self.try_unlock_pdf_enhanced(pdf_path, candidates, msg_id)
                    if unlocked_path:
                        unlocked_count += 1
                        print(f"✅ Unlocked: {pdf_path}")
                    else:
                        print(f"❌ Failed to unlock: {pdf_path}")
                else:
                    print(f"⚠️ File not found: {pdf_path}")
        
        print(f"\n📊 Summary: {unlocked_count}/{total_pdfs} PDFs unlocked successfully")

    def try_unlock_pdf_enhanced(self, pdf_path: str, password_candidates: List[PasswordCandidate], email_id: str) -> Optional[str]:
        """Enhanced PDF unlocking with candidate tracking"""
        try:
            # Try without password first
            pdf = pikepdf.open(pdf_path)
            pdf.close()
            print(f"📄 PDF is not password protected: {pdf_path}")
            return pdf_path
        except pikepdf._qpdf.PasswordError:
            pass
        
        # Try each password candidate in order of confidence
        for candidate in password_candidates:
            try:
                pdf = pikepdf.open(pdf_path, password=str(candidate.password))
                
                # Save unlocked version
                unlocked_path = pdf_path.replace('.pdf', '_unlocked.pdf')
                pdf.save(unlocked_path)
                pdf.close()
                
                # Mark this password as working
                self.mark_password_result(email_id, candidate.password, True)
                
                print(f"🔓 Unlocked with password: {candidate.password}")
                print(f"🧠 Reasoning: {candidate.reasoning}")
                print(f"📊 Confidence: {candidate.confidence}")
                print(f"🔍 Source: {candidate.source}")
                
                return unlocked_path
                
            except pikepdf._qpdf.PasswordError:
                # Mark this password as not working
                self.mark_password_result(email_id, candidate.password, False)
                continue
            except Exception as e:
                print(f"Error trying password {candidate.password}: {e}")
                continue
        
        return None

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

    def _setup_llm(self):
        """Setup the best available local LLM"""
        backends = [
            ("ollama", "llama3.1"),
            ("lmstudio", "llama-3.1-8b-instruct"),
            ("llamacpp", "llama-3.1-8b-instruct")
        ]
        
        for backend, model in backends:
            try:
                llm = LocalLLMManager(backend, model)
                if llm.is_available():
                    self.llm_manager = llm
                    logger.info(f"Using {backend} with model {model}")
                    return
            except Exception as e:
                logger.warning(f"Failed to setup {backend}: {e}")
        
        logger.warning("No local LLM available, falling back to rule-based generation")
        self.llm_manager = None

    def generate_password_candidates(self, hints, rules, personal_data, email_body="", sender="", email_id=""):
        """Enhanced password generation using integrated LLM and rule-based approach"""
        # Use new enhanced method if email_id is provided
        if email_id:
            candidates = self.generate_passwords_for_email(email_id)
            return [candidate.password for candidate in candidates]
        
        # Fallback to basic generation for backward compatibility
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

    def process_new_statements(self, months_back=2):
        """Process new credit card statement emails"""
        logger.info("Starting to process new statement emails...")
        
        try:
            # Search for new statement emails
            messages = self.search_credit_card_emails(months_back)
            
            if not messages:
                logger.info("No new statement emails found")
                return 0
            
            processed_count = 0
            
            for message in messages:
                msg_id = message['id']
                
                # Skip if already processed
                if self.is_already_processed(msg_id):
                    logger.debug(f"Email {msg_id} already processed, skipping")
                    continue
                
                try:
                    # Get message details
                    msg_details = self.get_message_details(msg_id)
                    if not msg_details:
                        logger.warning(f"Could not get details for message {msg_id}")
                        continue
                    
                    # Extract basic information
                    payload = msg_details.get('payload', {})
                    headers = payload.get('headers', [])
                    
                    subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
                    sender = next((h['value'] for h in headers if h['name'] == 'From'), '')
                    date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
                    snippet = msg_details.get('snippet', '')
                    
                    # Get email body
                    email_body = self.get_email_body(msg_id)
                    
                    # Extract password rules and hints
                    password_hints, password_rules = self.extract_password_rules_and_hints(
                        email_body, subject, sender
                    )
                    
                    # Download PDF attachments if any
                    attachments = self.download_pdf_attachments(msg_id, payload)
                    
                    # Store email metadata in database
                    self.store_email_metadata(
                        msg_id, subject, sender, date, snippet, 
                        password_hints, password_rules, attachments, email_body
                    )
                    
                    # Generate password candidates for this email
                    if password_hints or password_rules:
                        password_candidates = self.generate_passwords_for_email(msg_id)
                        if password_candidates:
                            self.save_password_candidates(msg_id, password_candidates)
                            logger.info(f"Generated {len(password_candidates)} password candidates for email {msg_id}")
                    
                    processed_count += 1
                    logger.info(f"✅ Processed email from {sender}: {subject}")
                    
                except Exception as e:
                    logger.error(f"❌ Error processing email {msg_id}: {e}")
                    continue
            
            logger.info(f"✅ Successfully processed {processed_count} new statement emails")
            return processed_count
            
        except Exception as e:
            logger.error(f"❌ Error in process_new_statements: {e}")
            raise

class LocalLLMManager:
    """Manages different local LLM backends"""
    
    def __init__(self, backend="ollama", model="llama3.1"):
        self.backend = backend
        self.model = model
        self.base_url = "http://localhost:11434"  # Default Ollama URL
        
    def is_available(self) -> bool:
        """Check if the LLM service is available"""
        try:
            if self.backend == "ollama":
                response = requests.get(f"{self.base_url}/api/tags", timeout=5)
                return response.status_code == 200
            elif self.backend == "lmstudio":
                response = requests.get("http://localhost:1234/v1/models", timeout=5)
                return response.status_code == 200
            elif self.backend == "llamacpp":
                response = requests.get("http://localhost:8080/health", timeout=5)
                return response.status_code == 200
        except:
            return False
        return False
    
    def generate_response(self, prompt: str, max_tokens: int = 500) -> str:
        """Generate response using the configured LLM backend"""
        try:
            if self.backend == "ollama":
                return self._ollama_generate(prompt, max_tokens)
            elif self.backend == "lmstudio":
                return self._lmstudio_generate(prompt, max_tokens)
            elif self.backend == "llamacpp":
                return self._llamacpp_generate(prompt, max_tokens)
            else:
                raise ValueError(f"Unsupported backend: {self.backend}")
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return ""
    
    def _ollama_generate(self, prompt: str, max_tokens: int) -> str:
        """Generate using Ollama API"""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": 0.1
            }
        }
        
        response = requests.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json().get("response", "")
        else:
            raise Exception(f"Ollama API error: {response.status_code}")
    
    def _lmstudio_generate(self, prompt: str, max_tokens: int) -> str:
        """Generate using LM Studio API"""
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.1
        }
        
        response = requests.post(
            "http://localhost:1234/v1/chat/completions",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            raise Exception(f"LM Studio API error: {response.status_code}")
    
    def _llamacpp_generate(self, prompt: str, max_tokens: int) -> str:
        """Generate using llama.cpp server"""
        payload = {
            "prompt": prompt,
            "n_predict": max_tokens,
            "temperature": 0.1,
            "stop": ["</s>", "\n\n"]
        }
        
        response = requests.post(
            "http://localhost:8080/completion",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json().get("content", "")
        else:
            raise Exception(f"llama.cpp server error: {response.status_code}")

# Example usage and setup
if __name__ == "__main__":
    # Initialize client
    client = EnhancedGmailClient()
    
    # Add some sample personal data (you should customize this)
    client.add_personal_data('date_of_birth', '10031984', 'Date of birth in DDMMYYYY format')
    client.add_personal_data('mobile_number', '971525562885', 'Mobile number')
    client.add_personal_data('name', 'John', 'First name')
    client.add_personal_data('card_number', '1234567890123456', 'Credit card number')
    
    # Process new emails
    print("Processing new statement emails...")
    client.process_new_statements()
    
    # Try to unlock PDFs
    print("\nAttempting to unlock PDFs...")
    client.unlock_pdfs()