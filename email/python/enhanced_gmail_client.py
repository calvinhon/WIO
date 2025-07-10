
#!/usr/bin/env python3
"""
Enhanced Gmail Client for PDF Statement Processing
This module provides functionality to fetch emails from Gmail using Gmail API

Setup Instructions:
1. Install required packages:
   pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client

2. Setup Gmail API:
   - Go to https://console.cloud.google.com/
   - Create a new project or select existing one
   - Enable Gmail API
   - Create OAuth 2.0 credentials (Desktop application)
   - Download credentials.json file

3. Place credentials.json in ./secret/ directory
"""

import os
import json
import sqlite3
import logging
import base64
import pickle
import re
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
from email.mime.text import MIMEText

# Gmail API imports
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class GmailConfig:
    """Configuration for Gmail integration"""
    credentials_file: str = './secret/credentials.json'
    token_file: str = './secret/gmail_token.pickle'
    scopes: List[str] = None
    
    def __post_init__(self):
        if self.scopes is None:
            self.scopes = [
                'https://www.googleapis.com/auth/gmail.readonly',
                'https://www.googleapis.com/auth/gmail.modify'
            ]

class EnhancedGmailClient:
    """Enhanced Gmail client for fetching and processing bank statement emails"""
    
    def __init__(self, config: GmailConfig, db_path='email_data.db'):
        self.config = config
        self.db_path = db_path
        self.service = None
        self.creds = None
        self._init_db()
        
    def _init_db(self):
        """Initialize database with Gmail-specific tables"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # Create gmail_emails table
            c.execute('''
                CREATE TABLE IF NOT EXISTS gmail_emails (
                    id TEXT PRIMARY KEY,
                    subject TEXT,
                    sender TEXT,
                    sender_email TEXT,
                    date TEXT,
                    snippet TEXT,
                    attachments TEXT,
                    timestamp INTEGER,
                    email_body TEXT,
                    processed_date TEXT,
                    labels TEXT,
                    thread_id TEXT,
                    has_attachments BOOLEAN
                )
            ''')
            
            # Create gmail_labels table
            c.execute('''
                CREATE TABLE IF NOT EXISTS gmail_labels (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    type TEXT,
                    messages_total INTEGER,
                    messages_unread INTEGER
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    def authenticate(self) -> bool:
        """Authenticate with Gmail API"""
        try:
            # Load existing credentials
            if os.path.exists(self.config.token_file):
                with open(self.config.token_file, 'rb') as token:
                    self.creds = pickle.load(token)
            
            # If there are no (valid) credentials available, let the user log in
            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    try:
                        self.creds.refresh(Request())
                        logger.info("✅ Refreshed existing credentials")
                    except Exception as e:
                        logger.warning(f"Failed to refresh credentials: {e}")
                        self.creds = None
                
                if not self.creds:
                    if not os.path.exists(self.config.credentials_file):
                        logger.error(f"❌ Credentials file not found: {self.config.credentials_file}")
                        print(f"\n📁 Please ensure credentials.json exists at: {self.config.credentials_file}")
                        return False
                    
                    print("\n🔐 Starting Gmail authentication...")
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.config.credentials_file, self.config.scopes)
                    self.creds = flow.run_local_server(port=0)
                    logger.info("✅ New credentials obtained")
                
                # Save the credentials for the next run
                with open(self.config.token_file, 'wb') as token:
                    pickle.dump(self.creds, token)
            
            # Build the service
            self.service = build('gmail', 'v1', credentials=self.creds)
            logger.info("✅ Gmail service authenticated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False
    
    def get_labels(self) -> List[dict]:
        """Get all Gmail labels"""
        try:
            if not self.service:
                raise Exception("Not authenticated. Please call authenticate() first.")
            
            results = self.service.users().labels().list(userId='me').execute()
            labels = results.get('labels', [])
            
            # Save labels to database
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            for label in labels:
                c.execute('''
                    INSERT OR REPLACE INTO gmail_labels 
                    (id, name, type, messages_total, messages_unread)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    label['id'],
                    label['name'],
                    label['type'],
                    label.get('messagesTotal', 0),
                    label.get('messagesUnread', 0)
                ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Retrieved {len(labels)} labels")
            return labels
            
        except Exception as e:
            logger.error(f"Failed to get labels: {e}")
            return []
    
    def search_bank_emails(self, months_back: int = 2, label_ids: List[str] = None) -> List[dict]:
        """Search for bank statement emails with attachments in the last N months"""
        try:
            if not self.service:
                raise Exception("Not authenticated. Please call authenticate() first.")
            
            # Get previously processed email IDs
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("SELECT id FROM gmail_emails")
            processed_ids = set(row[0] for row in c.fetchall())
            conn.close()
            
            # Build search query
            past_date = datetime.now() - timedelta(days=months_back * 30)
            date_str = past_date.strftime('%Y/%m/%d')
            
            # Bank-related keywords
            keywords = ["credit card", "bank statement"]
            keyword_query = " OR ".join([f'"{kw}"' for kw in keywords])
            
            # Build Gmail search query
            query_parts = [
                f"after:{date_str}",
                "has:attachment",
                f"({keyword_query})"
            ]
            
            if label_ids:
                for label_id in label_ids:
                    query_parts.append(f"label:{label_id}")
            
            query = " ".join(query_parts)
            logger.info(f"🔍 Gmail search query: {query}")
            
            # Execute search
            result = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=50
            ).execute()
            
            messages = result.get('messages', [])
            
            # Filter out already processed emails
            new_messages = [msg for msg in messages if msg['id'] not in processed_ids]
            
            logger.info(f"✅ Found {len(new_messages)} new bank statement emails")
            return new_messages
            
        except Exception as e:
            logger.error(f"❌ Failed to search bank emails: {e}")
            return []
    
    def get_email_details(self, message_id: str) -> dict:
        """Get detailed email information including body and attachments"""
        try:
            if not self.service:
                raise Exception("Not authenticated. Please call authenticate() first.")
            
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            return message
            
        except Exception as e:
            logger.error(f"Failed to get email details for {message_id}: {e}")
            return {}
    
    def extract_email_body(self, message: dict) -> str:
        """Extract plain text body from Gmail message"""
        try:
            payload = message.get('payload', {})
            
            # Function to recursively extract text from parts
            def extract_text_from_part(part):
                mime_type = part.get('mimeType', '')
                
                if mime_type == 'text/plain':
                    data = part.get('body', {}).get('data', '')
                    if data:
                        return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                elif mime_type == 'text/html':
                    data = part.get('body', {}).get('data', '')
                    if data:
                        html_content = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                        # Simple HTML to text conversion
                        text_content = re.sub(r'<[^>]+>', ' ', html_content)
                        text_content = re.sub(r'\s+', ' ', text_content)
                        return text_content.strip()
                elif 'parts' in part:
                    # Multipart message
                    text_parts = []
                    for sub_part in part['parts']:
                        sub_text = extract_text_from_part(sub_part)
                        if sub_text:
                            text_parts.append(sub_text)
                    return '\n'.join(text_parts)
                
                return ''
            
            # Extract text from the message
            body_text = extract_text_from_part(payload)
            
            # Fallback to snippet if no body found
            if not body_text:
                body_text = message.get('snippet', '')
            
            return body_text
            
        except Exception as e:
            logger.error(f"Failed to extract email body: {e}")
            return message.get('snippet', '')
    
    def download_attachments(self, message_id: str, message: dict, download_dir: str = 'assets') -> List[str]:
        """Download PDF attachments from Gmail message"""
        try:
            if not os.path.exists(download_dir):
                os.makedirs(download_dir)
            
            downloaded_files = []
            
            def process_parts(parts):
                for part in parts:
                    if part.get('filename'):
                        filename = part['filename']
                        if not (filename.lower().endswith('.pdf') or filename.lower().endswith('.html')):
                            continue
                        if filename.lower().endswith('.pdf'):
                            attachment_id = part['body'].get('attachmentId')
                            if attachment_id:
                                try:
                                    attachment = self.service.users().messages().attachments().get(
                                        userId='me',
                                        messageId=message_id,
                                        id=attachment_id
                                    ).execute()
                                    
                                    # Decode attachment data
                                    data = attachment['data']
                                    file_data = base64.urlsafe_b64decode(data)
                                    
                                    # Create unique filename
                                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                                    name, ext = os.path.splitext(filename)
                                    unique_filename = f"{name}_{timestamp}{ext}"
                                    filepath = os.path.join(download_dir, unique_filename)
                                    
                                    # Save file
                                    with open(filepath, 'wb') as f:
                                        f.write(file_data)
                                    
                                    downloaded_files.append(filepath)
                                    logger.info(f"Downloaded: {unique_filename}")
                                    
                                except Exception as e:
                                    logger.error(f"Failed to download attachment {filename}: {e}")
                    
                    # Process nested parts
                    if 'parts' in part:
                        process_parts(part['parts'])
            
            # Process message parts
            payload = message.get('payload', {})
            if 'parts' in payload:
                process_parts(payload['parts'])
            elif payload.get('filename'):
                # Single attachment
                process_parts([payload])
            
            return downloaded_files
            
        except Exception as e:
            logger.error(f"Failed to download attachments: {e}")
            return []
    
    def store_email_metadata(self, message: dict, attachments: List[str]):
        """Store email metadata in database"""
        try:
            # Extract headers
            headers = {h['name']: h['value'] for h in message.get('payload', {}).get('headers', [])}
            
            subject = headers.get('Subject', '')
            sender = headers.get('From', '')
            date = headers.get('Date', '')
            
            # Extract sender email
            sender_email = ''
            if '<' in sender and '>' in sender:
                sender_email = sender.split('<')[1].split('>')[0]
            elif '@' in sender:
                sender_email = sender
            
            # Convert date to timestamp
            timestamp = int(datetime.now().timestamp())
            try:
                from email.utils import parsedate_to_datetime
                dt = parsedate_to_datetime(date)
                timestamp = int(dt.timestamp())
            except:
                pass
            
            # Extract email body
            email_body = self.extract_email_body(message)
            
            # Get labels
            labels = message.get('labelIds', [])
            
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            c.execute('''
                INSERT OR REPLACE INTO gmail_emails 
                (id, subject, sender, sender_email, date, snippet, attachments, 
                 timestamp, email_body, processed_date, labels, thread_id, has_attachments)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                message['id'],
                subject,
                sender,
                sender_email,
                date,
                message.get('snippet', ''),
                json.dumps(attachments),
                timestamp,
                email_body,
                datetime.now().isoformat(),
                json.dumps(labels),
                message.get('threadId', ''),
                len(attachments) > 0
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to store email metadata: {e}")
    
    def process_new_emails(self, months_back: int = 2) -> int:
        """Process new emails and return count of processed emails"""
        if not self.service:
            logger.error("Not authenticated. Please call authenticate() first.")
            return 0
        
        try:
            # Search for bank emails
            messages = self.search_bank_emails(months_back)
            processed_count = 0
            
            for message in messages:
                try:
                    # Get full email details
                    full_message = self.get_email_details(message['id'])
                    
                    if not full_message:
                        continue
                    
                    # Download attachments
                    downloaded_files = self.download_attachments(message['id'], full_message)
                    
                    # Store metadata
                    self.store_email_metadata(full_message, downloaded_files)
                    
                    processed_count += 1
                    
                    # Extract subject for logging
                    headers = {h['name']: h['value'] for h in full_message.get('payload', {}).get('headers', [])}
                    subject = headers.get('Subject', 'No Subject')
                    logger.info(f"Processed email: {subject}")
                    
                    # Add small delay to avoid rate limiting
                    time.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Failed to process email {message['id']}: {e}")
                    continue
            
            logger.info(f"✅ Processed {processed_count} emails from Gmail")
            return processed_count
            
        except Exception as e:
            logger.error(f"Failed to process emails: {e}")
            return 0
    
    def get_processed_emails(self) -> List[dict]:
        """Get all processed emails from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            c.execute('''
                SELECT id, subject, sender, sender_email, date, snippet, 
                       attachments, labels, thread_id, has_attachments
                FROM gmail_emails 
                ORDER BY timestamp DESC
            ''')
            
            rows = c.fetchall()
            conn.close()
            
            emails = []
            for row in rows:
                emails.append({
                    'id': row[0],
                    'subject': row[1],
                    'sender': row[2],
                    'sender_email': row[3],
                    'date': row[4],
                    'snippet': row[5],
                    'attachments': json.loads(row[6]) if row[6] else [],
                    'labels': json.loads(row[7]) if row[7] else [],
                    'thread_id': row[8],
                    'has_attachments': row[9]
                })
            
            return emails
            
        except Exception as e:
            logger.error(f"Failed to get processed emails: {e}")
            return []
    
    def get_email_stats(self) -> dict:
        """Get email processing statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # Total emails
            c.execute("SELECT COUNT(*) FROM gmail_emails")
            total_emails = c.fetchone()[0]
            
            # Emails with attachments
            c.execute("SELECT COUNT(*) FROM gmail_emails WHERE has_attachments = 1")
            emails_with_attachments = c.fetchone()[0]
            
            # Recent emails (last 7 days)
            week_ago = datetime.now() - timedelta(days=7)
            week_ago_timestamp = int(week_ago.timestamp())
            c.execute("SELECT COUNT(*) FROM gmail_emails WHERE timestamp > ?", (week_ago_timestamp,))
            recent_emails = c.fetchone()[0]
            
            # Top senders
            c.execute('''
                SELECT sender_email, COUNT(*) as count 
                FROM gmail_emails 
                WHERE sender_email != '' 
                GROUP BY sender_email 
                ORDER BY count DESC 
                LIMIT 5
            ''')
            top_senders = c.fetchall()
            
            conn.close()
            
            return {
                'total_emails': total_emails,
                'emails_with_attachments': emails_with_attachments,
                'recent_emails': recent_emails,
                'top_senders': [{'email': sender, 'count': count} for sender, count in top_senders]
            }
            
        except Exception as e:
            logger.error(f"Failed to get email stats: {e}")
            return {}

def main():
    """Main function to run the Gmail client"""
    print("🚀 Starting Enhanced Gmail Client")
    print("=" * 50)
    
    # Configuration
    config = GmailConfig()
    
    try:
        # Initialize client
        print("📧 Initializing Gmail client...")
        client = EnhancedGmailClient(config)
        
        # Authenticate
        print("🔐 Authenticating...")
        if not client.authenticate():
            print("❌ Authentication failed. Please check your configuration.")
            return
        
        print("✅ Successfully authenticated with Gmail")
        
        # Get labels
        print("\n📁 Getting Gmail labels...")
        labels = client.get_labels()
        print(f"Found {len(labels)} labels:")
        for label in labels[:5]:  # Show first 5 labels
            print(f"  - {label['name']} ({label.get('messagesTotal', 0)} messages)")
        
        # Process emails
        print(f"\n📧 Processing emails from the last 2 months...")
        processed_count = client.process_new_emails(months_back=2)
        print(f"Processed {processed_count} emails")
        
        # Get processed emails
        print("\n📊 Getting processed emails from database...")
        emails = client.get_processed_emails()
        print(f"Total emails in database: {len(emails)}")
        
        # Get statistics
        print("\n📈 Email Statistics:")
        stats = client.get_email_stats()
        print(f"  Total emails: {stats.get('total_emails', 0)}")
        print(f"  With attachments: {stats.get('emails_with_attachments', 0)}")
        print(f"  Recent (7 days): {stats.get('recent_emails', 0)}")
        
        # Display summary
        if emails:
            print("\n📋 Recent emails:")
            for email in emails[:3]:  # Show first 3 emails
                print(f"  - {email['subject']} (from {email['sender_email']})")
                if email['attachments']:
                    print(f"    📎 {len(email['attachments'])} attachments")
        
        print("\n✅ Email processing completed successfully!")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Process interrupted by user")
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        logger.error(f"Main function error: {e}")

if __name__ == "__main__":
    main()
