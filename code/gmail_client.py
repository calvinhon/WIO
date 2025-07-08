import os
import base64
import json
import sqlite3
from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import re

class GmailClient:
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
                attachments TEXT,
                timestamp INTEGER
            )
        ''')
        conn.commit()
        conn.close()

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

    def search_credit_card_emails(self, query=None):
        base_query = (
            'has:attachment filename:pdf '
            'subject:(statement OR "credit card" OR bank) '
            '-from: ('
            '@bankfab.com OR '
            '@emiratesnbd.com OR '
            '@adcb.ae OR @adcb.com OR '
            '@adib.ae OR '
            '@dib.ae OR '
            '@emiratesislamic.ae OR '
            '@cbd.ae OR '
            '@mashreqbank.com OR '
            '@rakbank.ae OR '
            '@nbf.ae OR '
            '@nbruq.ae OR '
            '@bankofsharjah.com OR '
            '@uab.ae OR '
            '@hsbc.ae OR '
            '@citibank.ae OR '
            '@sc.com OR '
            '@barclays.ae OR '
            '@bnpparibas.ae OR '
            '@bankofbaroda.ae OR '
            '@hbl.com OR '
            '@habibbank.com OR '
            '@arabbank.ae OR '
            '@alhilalbank.ae OR '
            '@ajmanbank.ae OR '
            '@sib.ae OR '
            '@eibank.com'
            ')'
        )

        latest_ts = self.get_latest_email_timestamp()
        if latest_ts:
            after_str = datetime.utcfromtimestamp(latest_ts).strftime('%Y/%m/%d')
            base_query += f' after:{after_str}'

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
        """
        Fetch the plain text body of the email with given message ID.
        Returns a string with the email content.
        """
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

        # If no parts and payload body data exists, try to decode it
        if not parts:
            body = payload.get('body', {}).get('data')
            if body:
                try:
                    return base64.urlsafe_b64decode(body).decode('utf-8', errors='ignore')
                except Exception:
                    return ""

        text_body = _get_parts(parts)
        return text_body if text_body else ""

    def extract_password_hints(self, snippet, payload, email_body=""):
        hints = []
        # Extract hints from snippet
        if snippet:
            hints.extend([w for w in snippet.split() if len(w) >= 4 and any(c.isdigit() for c in w)])

        # Extract hints from payload text parts
        text_parts = self._get_text_parts(payload)
        for text in text_parts:
            hints.extend([w.strip('.,') for w in text.split() if len(w) >= 4 and any(c.isdigit() for c in w)])

        # Extract hints from full email body (better coverage)
        if email_body:
            # Simple regex for password-like hints e.g., "password is 1234"
            pattern = re.compile(
                r'password (is|:|=|to open|for pdf|hint|your pdf password)?\s*([^\s.,;]+)', re.I)
            matches = pattern.findall(email_body)
            for _, candidate in matches:
                hints.append(candidate.strip())

            # Extract dates like dd/mm/yyyy
            dates = re.findall(r'\d{2}/\d{2}/\d{4}', email_body)
            hints.extend([d.replace('/', '') for d in dates])

            # Extract 4-digit sequences
            four_digits = re.findall(r'\b\d{4}\b', email_body)
            hints.extend(four_digits)

        return list(set(hints))

    def _get_text_parts(self, payload):
        texts = []
        if 'body' in payload and 'data' in payload['body']:
            try:
                text = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')
                texts.append(text)
            except:
                pass
        if 'parts' in payload:
            for part in payload['parts']:
                texts.extend(self._get_text_parts(part))
        return texts

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
                        filepath = os.path.join(download_dir, filename)
                        with open(filepath, 'wb') as f:
                            f.write(base64.urlsafe_b64decode(data))
                        downloaded_files.append(filepath)
                if 'parts' in part:
                    extract(part['parts'])

        extract(payload.get('parts', []))
        return downloaded_files

    def store_email_metadata(self, msg_id, subject, sender, date, snippet, password_hints, attachments):
        try:
            timestamp = int(datetime.strptime(date, '%a, %d %b %Y %H:%M:%S %z').timestamp())
        except Exception:
            timestamp = int(datetime.utcnow().timestamp())

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            INSERT OR REPLACE INTO emails (id, subject, sender, date, snippet, password_hints, attachments, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (msg_id, subject, sender, date, snippet, json.dumps(password_hints), json.dumps(attachments), timestamp))
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

            email_body = self.get_email_body(msg_id)

            password_hints = self.extract_password_hints(snippet, payload, email_body)
            attachments = self.download_pdf_attachments(msg_id, payload)

            self.store_email_metadata(msg_id, subject, sender, date, snippet, password_hints, attachments)
            print(f"Processed and stored new email: {subject}")
            processed_count += 1

        if processed_count == 0:
            print("No new statement emails to process.")
