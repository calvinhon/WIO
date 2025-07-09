#!/usr/bin/env python3
"""
Outlook Email Client for PDF Statement Processing
This module provides functionality to fetch emails from Outlook/Office 365 using Microsoft Graph API

Setup Instructions:
1. Install required packages:
   pip install msal requests

2. Register your app in Azure Portal:
   - Go to https://portal.azure.com
   - Navigate to Azure Active Directory > App registrations
   - Click "New registration"
   - Set redirect URI to "http://localhost"
   - Under Authentication, enable "Allow public client flows"
   - Copy the Application (client) ID

3. Update the client_id in the config below with your actual client ID
"""

import os
import json
import sqlite3
import logging
import requests
import base64
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import msal
import webbrowser
from urllib.parse import urlencode
import re
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class OutlookConfig:
    """Configuration for Outlook/Office 365 integration"""
    # IMPORTANT: Replace this with your actual client ID from Azure Portal
    client_id: str = "86fd58c9-45de-44cb-9fca-615de1513036"  # Replace with your actual client ID
    client_secret: str = ""  # Optional for public clients
    tenant_id: str = "common"  # Use "common" for personal accounts
    redirect_uri: str = "http://localhost"
    scopes: List[str] = None
    
    def __post_init__(self):
        if self.scopes is None:
            self.scopes = [
                "https://graph.microsoft.com/Mail.Read",
                "https://graph.microsoft.com/Mail.ReadBasic",
                "https://graph.microsoft.com/User.Read"
            ]

class OutlookClient:
    """Enhanced Outlook client for fetching and processing bank statement emails"""
    
    def __init__(self, config: OutlookConfig, db_path='email_data.db'):
        self.config = config
        self.db_path = db_path
        self.access_token = None
        self.app = None
        self.token_cache_file = 'outlook_token_cache.json'
        self._init_db()
        self._setup_msal_app()
        
    def _init_db(self):
        """Initialize database with Outlook-specific tables"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # Create outlook_emails table
            c.execute('''
                CREATE TABLE IF NOT EXISTS outlook_emails (
                    id TEXT PRIMARY KEY,
                    subject TEXT,
                    sender TEXT,
                    sender_email TEXT,
                    date TEXT,
                    snippet TEXT,
                    password_hints TEXT,
                    password_rules TEXT,
                    attachments TEXT,
                    timestamp INTEGER,
                    email_body TEXT,
                    processed_date TEXT,
                    folder_id TEXT,
                    importance TEXT,
                    has_attachments BOOLEAN
                )
            ''')
            
            # Create outlook_folders table
            c.execute('''
                CREATE TABLE IF NOT EXISTS outlook_folders (
                    id TEXT PRIMARY KEY,
                    display_name TEXT,
                    parent_folder_id TEXT,
                    child_folder_count INTEGER,
                    unread_item_count INTEGER,
                    total_item_count INTEGER
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    def _setup_msal_app(self):
        """Setup MSAL application for authentication"""
        try:
            # Load token cache if exists
            token_cache = msal.SerializableTokenCache()
            if os.path.exists(self.token_cache_file):
                with open(self.token_cache_file, 'r') as cache_file:
                    token_cache.deserialize(cache_file.read())
            
            # Create MSAL app
            self.app = msal.PublicClientApplication(
                client_id=self.config.client_id,
                authority=f"https://login.microsoftonline.com/{self.config.tenant_id}",
                token_cache=token_cache
            )
            logger.info("MSAL app setup completed")
            
        except Exception as e:
            logger.error(f"MSAL app setup failed: {e}")
            raise
    
    def authenticate(self) -> bool:
        """Authenticate with Microsoft Graph API"""
        try:
            # First, try to get token from cache
            accounts = self.app.get_accounts()
            if accounts:
                result = self.app.acquire_token_silent(self.config.scopes, account=accounts[0])
                if result and 'access_token' in result:
                    self.access_token = result['access_token']
                    self._save_token_cache()
                    logger.info("✅ Authenticated silently using cached token")
                    return True

            # Use device code flow for authentication (recommended for public clients)
            print("\n🔐 Starting authentication process...")
            
            # Debug: Print configuration details
            print(f"📋 Using Client ID: {self.config.client_id}")
            print(f"📋 Using Tenant: {self.config.tenant_id}")
            print(f"📋 Using Scopes: {self.config.scopes}")
            
            flow = self.app.initiate_device_flow(scopes=self.config.scopes)
            
            if "user_code" not in flow:
                logger.error("Failed to create device flow")
                if "error" in flow:
                    logger.error(f"Error details: {flow.get('error')}")
                    logger.error(f"Error description: {flow.get('error_description')}")
                print("\n❌ Device flow creation failed!")
                print("🔧 This usually means:")
                print("   1. Invalid Client ID")
                print("   2. App not configured for public client flows")
                print("   3. Network connectivity issues")
                print("\n📝 Please check your Azure app registration:")
                print("   - Go to Azure Portal > App registrations")
                print("   - Find your app and check the Client ID")
                print("   - Go to Authentication > Allow public client flows = Yes")
                return False
            
            print(f"\n📱 Please visit: {flow['verification_uri']}")
            print(f"🔑 Enter this code: {flow['user_code']}")
            print("⏳ Waiting for authentication...")
            
            # Try to open browser automatically
            try:
                webbrowser.open(flow['verification_uri'])
            except:
                pass
            
            result = self.app.acquire_token_by_device_flow(flow)
            
            if "access_token" in result:
                self.access_token = result["access_token"]
                self._save_token_cache()
                logger.info("✅ Authentication successful!")
                return True
            else:
                logger.error(f"❌ Authentication failed: {result.get('error_description', result)}")
                print(f"\n❌ Authentication failed!")
                print(f"Error: {result.get('error', 'Unknown error')}")
                print(f"Description: {result.get('error_description', 'No description')}")
                return False
                
        except Exception as e:
            logger.error(f"Authentication exception: {e}")
            print(f"\n❌ Authentication exception: {e}")
            return False
    
    def _save_token_cache(self):
        """Save token cache to file"""
        try:
            if self.app.token_cache.has_state_changed:
                with open(self.token_cache_file, 'w') as cache_file:
                    cache_file.write(self.app.token_cache.serialize())
        except Exception as e:
            logger.warning(f"Failed to save token cache: {e}")
    
    def _make_graph_request(self, endpoint: str, params: dict = None) -> dict:
        """Make authenticated request to Microsoft Graph API"""
        if not self.access_token:
            raise Exception("Not authenticated. Please call authenticate() first.")
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        url = f"https://graph.microsoft.com/v1.0{endpoint}"
        
        try:
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 401:
                # Token might be expired, try to refresh
                logger.info("🔄 Token expired, attempting to refresh...")
                if self.authenticate():
                    headers['Authorization'] = f'Bearer {self.access_token}'
                    response = requests.get(url, headers=headers, params=params)
            
            if response.status_code != 200:
                logger.error(f"Graph API error: {response.status_code} - {response.text}")
                raise Exception(f"Graph API error: {response.status_code} - {response.text}")
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise
    
    def get_folders(self) -> List[dict]:
        """Get all mail folders"""
        try:
            result = self._make_graph_request("/me/mailFolders")
            folders = result.get('value', [])
            
            # Save folders to database
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            for folder in folders:
                c.execute('''
                    INSERT OR REPLACE INTO outlook_folders 
                    (id, display_name, parent_folder_id, child_folder_count, unread_item_count, total_item_count)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    folder['id'],
                    folder['displayName'],
                    folder.get('parentFolderId'),
                    folder.get('childFolderCount', 0),
                    folder.get('unreadItemCount', 0),
                    folder.get('totalItemCount', 0)
                ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Retrieved {len(folders)} folders")
            return folders
            
        except Exception as e:
            logger.error(f"Failed to get folders: {e}")
            return []
    
    def search_bank_emails(self, months_back: int = 2, folder_id: str = None) -> List[dict]:
        """Search for bank statement emails"""
        try:
            # Calculate date filter
            past_date = datetime.now() - timedelta(days=months_back * 30)
            date_filter = past_date.strftime('%Y-%m-%dT%H:%M:%SZ')
            
            # Build search query
            search_params = {
                '$filter': f"hasAttachments eq true and receivedDateTime ge {date_filter}",
                '$select': 'id,subject,sender,receivedDateTime,bodyPreview,hasAttachments,importance,body',
                '$orderby': 'receivedDateTime desc',
                '$top': 100
            }
            
            # Use specific folder if provided, otherwise search in inbox
            endpoint = f"/me/mailFolders/{folder_id}/messages" if folder_id else "/me/messages"
            
            result = self._make_graph_request(endpoint, search_params)
            messages = result.get('value', [])
            
            logger.info(f"Found {len(messages)} potential bank statement emails")
            return messages
            
        except Exception as e:
            logger.error(f"Failed to search emails: {e}")
            return []
    
    def get_email_details(self, message_id: str) -> dict:
        """Get detailed email information including body and attachments"""
        try:
            # Get message details
            message = self._make_graph_request(f"/me/messages/{message_id}")
            
            # Get attachments if they exist
            if message.get('hasAttachments'):
                attachments = self._make_graph_request(f"/me/messages/{message_id}/attachments")
                message['attachments'] = attachments.get('value', [])
            
            return message
            
        except Exception as e:
            logger.error(f"Failed to get email details for {message_id}: {e}")
            return {}
    
    def extract_email_body(self, message: dict) -> str:
        """Extract plain text body from email message"""
        body = message.get('body', {})
        
        if body.get('contentType') == 'text':
            return body.get('content', '')
        elif body.get('contentType') == 'html':
            # Simple HTML to text conversion
            html_content = body.get('content', '')
            text_content = re.sub(r'<[^>]+>', ' ', html_content)
            text_content = re.sub(r'\s+', ' ', text_content)
            return text_content.strip()
        
        return message.get('bodyPreview', '')
    
    def download_attachments(self, message_id: str, attachments: List[dict], download_dir: str = 'downloads') -> List[str]:
        """Download PDF attachments from email"""
        try:
            if not os.path.exists(download_dir):
                os.makedirs(download_dir)
            
            downloaded_files = []
            
            for attachment in attachments:
                if (attachment.get('contentType') == 'application/pdf' or 
                    attachment.get('name', '').lower().endswith('.pdf')):
                    
                    try:
                        # Get attachment content
                        attachment_data = self._make_graph_request(f"/me/messages/{message_id}/attachments/{attachment['id']}")
                        
                        # Decode base64 content
                        content = base64.b64decode(attachment_data['contentBytes'])
                        
                        # Create unique filename
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        name, ext = os.path.splitext(attachment['name'])
                        unique_filename = f"{name}_{timestamp}{ext}"
                        filepath = os.path.join(download_dir, unique_filename)
                        
                        # Save file
                        with open(filepath, 'wb') as f:
                            f.write(content)
                        
                        downloaded_files.append(filepath)
                        logger.info(f"Downloaded: {unique_filename}")
                        
                    except Exception as e:
                        logger.error(f"Failed to download attachment {attachment.get('name', 'unknown')}: {e}")
            
            return downloaded_files
            
        except Exception as e:
            logger.error(f"Failed to download attachments: {e}")
            return []
    
    def extract_password_rules_and_hints(self, email_body: str, subject: str, sender: str) -> Tuple[List[str], List[str]]:
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
                if len(rule_text) > 10:
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
        
        # Extract dates and numbers
        dates = re.findall(r'\b\d{2}/\d{2}/\d{4}\b', email_body)
        hints.extend([d.replace('/', '') for d in dates])
        
        four_to_eight_digits = re.findall(r'\b\d{4,8}\b', email_body)
        hints.extend(four_to_eight_digits)
        
        return list(set(hints)), list(set(rules))
    
    def store_email_metadata(self, message: dict, password_hints: List[str], password_rules: List[str], attachments: List[str]):
        """Store email metadata in database"""
        try:
            sender_info = message.get('sender', {})
            sender_name = sender_info.get('emailAddress', {}).get('name', '')
            sender_email = sender_info.get('emailAddress', {}).get('address', '')
            
            # Convert datetime
            received_time = message.get('receivedDateTime', '')
            try:
                dt = datetime.fromisoformat(received_time.replace('Z', '+00:00'))
                timestamp = int(dt.timestamp())
            except:
                timestamp = int(datetime.now().timestamp())
            
            email_body = self.extract_email_body(message)
            
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            c.execute('''
                INSERT OR REPLACE INTO outlook_emails 
                (id, subject, sender, sender_email, date, snippet, password_hints, password_rules, 
                 attachments, timestamp, email_body, processed_date, folder_id, importance, has_attachments)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                message['id'],
                message.get('subject', ''),
                sender_name,
                sender_email,
                received_time,
                message.get('bodyPreview', ''),
                json.dumps(password_hints),
                json.dumps(password_rules),
                json.dumps(attachments),
                timestamp,
                email_body,
                datetime.now().isoformat(),
                message.get('parentFolderId'),
                message.get('importance', 'normal'),
                message.get('hasAttachments', False)
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to store email metadata: {e}")
    
    def process_new_emails(self, months_back: int = 2) -> int:
        """Process new emails and return count of processed emails"""
        if not self.access_token:
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
                    
                    # Extract email body
                    email_body = self.extract_email_body(full_message)
                    
                    # Extract password hints and rules
                    hints, rules = self.extract_password_rules_and_hints(
                        email_body,
                        full_message.get('subject', ''),
                        full_message.get('sender', {}).get('emailAddress', {}).get('address', '')
                    )
                    
                    # Download attachments
                    attachments = full_message.get('attachments', [])
                    downloaded_files = []
                    
                    if attachments:
                        downloaded_files = self.download_attachments(message['id'], attachments)
                    
                    # Store metadata
                    self.store_email_metadata(full_message, hints, rules, downloaded_files)
                    
                    processed_count += 1
                    logger.info(f"Processed email: {full_message.get('subject', 'No Subject')}")
                    
                    # Add small delay to avoid rate limiting
                    time.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Failed to process email {message['id']}: {e}")
                    continue
            
            logger.info(f"✅ Processed {processed_count} emails from Outlook")
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
                       password_hints, password_rules, attachments, has_attachments
                FROM outlook_emails 
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
                    'password_hints': json.loads(row[6]) if row[6] else [],
                    'password_rules': json.loads(row[7]) if row[7] else [],
                    'attachments': json.loads(row[8]) if row[8] else [],
                    'has_attachments': row[9]
                })
            
            return emails
            
        except Exception as e:
            logger.error(f"Failed to get processed emails: {e}")
            return []

def main():
    """Main function to run the Outlook client"""
    print("🚀 Starting Outlook Email Client")
    print("="*50)
    
    # Check if client ID is configured
    if OutlookConfig().client_id == "YOUR_CLIENT_ID_HERE":
        print("❌ CLIENT ID NOT CONFIGURED!")
        print("\n🔧 You need to set up Azure App Registration first:")
        print("   1. Go to https://portal.azure.com")
        print("   2. Navigate to Azure Active Directory > App registrations")
        print("   3. Click 'New registration'")
        print("   4. Set Name: 'Outlook Email Client'")
        print("   5. Set Redirect URI: 'http://localhost'")
        print("   6. Under Authentication, enable 'Allow public client flows'")
        print("   7. Copy the Application (client) ID")
        print("   8. Replace 'YOUR_CLIENT_ID_HERE' in the code with your actual client ID")
        print("\n💡 Alternative: Use a pre-configured client ID for testing:")
        
        use_test_id = input("\n🤔 Do you want to use a test client ID? (y/n): ").lower().strip()
        if use_test_id == 'y':
            test_client_id = "04b07795-8ddb-461a-bbee-02f9e1bf7b46"  # Microsoft Graph Explorer client ID
            print(f"📝 Using test client ID: {test_client_id}")
            config = OutlookConfig(client_id=test_client_id)
        else:
            print("👋 Please configure your client ID and try again.")
            return
    else:
        # Configuration
        config = OutlookConfig()
    
    try:
        # Initialize client
        print("📧 Initializing Outlook client...")
        client = OutlookClient(config)
        
        # Authenticate
        print("🔐 Authenticating...")
        if not client.authenticate():
            print("❌ Authentication failed. Please check your configuration.")
            return
        
        print("✅ Successfully authenticated with Outlook")
        
        # Get folders
        print("\n📁 Getting mail folders...")
        folders = client.get_folders()
        print(f"Found {len(folders)} folders:")
        for folder in folders[:5]:  # Show first 5 folders
            print(f"  - {folder['displayName']} ({folder.get('totalItemCount', 0)} items)")
        
        # Process emails
        print(f"\n📧 Processing emails from the last 2 months...")
        processed_count = client.process_new_emails(months_back=2)
        print(f"Processed {processed_count} emails")
        
        # Get processed emails
        print("\n📊 Getting processed emails from database...")
        emails = client.get_processed_emails()
        print(f"Total emails in database: {len(emails)}")
        
        # Display summary
        if emails:
            print("\n📋 Recent emails:")
            for email in emails[:3]:  # Show first 3 emails
                print(f"  - {email['subject']} (from {email['sender']})")
                if email['attachments']:
                    print(f"    📎 {len(email['attachments'])} attachments")
                if email['password_hints']:
                    print(f"    🔑 {len(email['password_hints'])} password hints found")
        
        print("\n✅ Email processing completed successfully!")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Process interrupted by user")
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        logger.error(f"Main function error: {e}")

if __name__ == "__main__":
    main()