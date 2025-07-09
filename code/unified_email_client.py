#!/usr/bin/env python3
"""
Unified Email Client
Integrates both Gmail and Outlook clients for comprehensive email processing
"""

import os
import json
import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Union
from dataclasses import dataclass
from pathlib import Path

# Import our custom clients
from enhanced_gmail_client import EnhancedGmailClient, PasswordCandidate
from outlook_client import OutlookClient, OutlookConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class EmailProvider:
    """Represents an email provider configuration"""
    name: str
    type: str  # 'gmail' or 'outlook'
    enabled: bool
    config: Union[dict, OutlookConfig]

class UnifiedEmailClient:
    """Unified client that manages both Gmail and Outlook email processing"""
    
    def __init__(self, db_path='email_data.db'):
        self.db_path = db_path
        self.gmail_client = None
        self.outlook_client = None
        self.providers = []
        self._init_db()
        self._load_config()
        
    def _init_db(self):
        """Initialize unified database schema"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Create unified emails table
        c.execute('''
            CREATE TABLE IF NOT EXISTS unified_emails (
                id TEXT PRIMARY KEY,
                provider TEXT,
                original_id TEXT,
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
                unlock_attempts INTEGER DEFAULT 0,
                unlock_success BOOLEAN DEFAULT 0,
                successful_password TEXT
            )
        ''')
        
        # Create email providers configuration table
        c.execute('''
            CREATE TABLE IF NOT EXISTS email_providers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                type TEXT,
                enabled BOOLEAN,
                config TEXT,
                last_sync TEXT,
                total_emails INTEGER DEFAULT 0
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _load_config(self):
        """Load email provider configurations"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('SELECT name, type, enabled, config FROM email_providers')
        rows = c.fetchall()
        
        for name, provider_type, enabled, config_str in rows:
            config = json.loads(config_str) if config_str else {}
            
            if provider_type == 'outlook':
                config = OutlookConfig(**config)
            
            provider = EmailProvider(
                name=name,
                type=provider_type,
                enabled=enabled,
                config=config
            )
            self.providers.append(provider)
        
        conn.close()
    
    def add_gmail_provider(self, name: str = "Gmail", credentials_file: str = "credentials.json"):
        """Add Gmail provider configuration"""
        config = {
            "credentials_file": credentials_file,
            "db_path": self.db_path
        }
        
        self._save_provider_config(name, "gmail", True, config)
        
        # Initialize Gmail client
        if os.path.exists(credentials_file):
            try:
                self.gmail_client = EnhancedGmailClient(credentials_file, self.db_path)
                logger.info(f"✅ Gmail provider '{name}' added successfully")
                return True
            except Exception as e:
                logger.error(f"❌ Failed to initialize Gmail client: {e}")
                return False
        else:
            logger.warning(f"⚠️ Gmail credentials file not found: {credentials_file}")
            return False
    
    def add_outlook_provider(self, name: str = "Outlook", client_id: str = "", tenant_id: str = "common"):
        """Add Outlook provider configuration"""
        if not client_id:
            logger.error("❌ Outlook client_id is required")
            return False
        
        config = {
            "client_id": client_id,
            "tenant_id": tenant_id
        }
        
        self._save_provider_config(name, "outlook", True, config)
        
        # Initialize Outlook client
        try:
            outlook_config = OutlookConfig(client_id=client_id, tenant_id=tenant_id)
            self.outlook_client = OutlookClient(outlook_config, self.db_path)
            logger.info(f"✅ Outlook provider '{name}' added successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to initialize Outlook client: {e}")
            return False
    
    def _save_provider_config(self, name: str, provider_type: str, enabled: bool, config: dict):
        """Save provider configuration to database"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            INSERT OR REPLACE INTO email_providers (name, type, enabled, config, last_sync)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, provider_type, enabled, json.dumps(config), datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    def list_providers(self) -> List[Dict]:
        """List all configured email providers"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            SELECT name, type, enabled, last_sync, total_emails 
            FROM email_providers 
            ORDER BY name
        ''')
        
        providers = []
        for row in c.fetchall():
            providers.append({
                'name': row[0],
                'type': row[1],
                'enabled': row[2],
                'last_sync': row[3],
                'total_emails': row[4]
            })
        
        conn.close()
        return providers
    
    def authenticate_all(self) -> Dict[str, bool]:
        """Authenticate all enabled providers"""
        results = {}
        
        # Authenticate Gmail
        if self.gmail_client:
            try:
                self.gmail_client.authenticate()
                results['gmail'] = True
                logger.info("✅ Gmail authentication successful")
            except Exception as e:
                results['gmail'] = False
                logger.error(f"❌ Gmail authentication failed: {e}")
        
        # Authenticate Outlook
        if self.outlook_client:
            try:
                auth_result = self.outlook_client.authenticate()
                results['outlook'] = auth_result
                if auth_result:
                    logger.info("✅ Outlook authentication successful")
                else:
                    logger.error("❌ Outlook authentication failed")
            except Exception as e:
                results['outlook'] = False
                logger.error(f"❌ Outlook authentication failed: {e}")
        
        return results
    
    def process_all_emails(self, months_back: int = 2) -> Dict[str, int]:
        """Process emails from all enabled providers"""
        results = {}
        
        # Process Gmail emails
        if self.gmail_client:
            try:
                gmail_count = self._process_gmail_emails(months_back)
                results['gmail'] = gmail_count
                logger.info(f"📧 Processed {gmail_count} Gmail emails")
            except Exception as e:
                results['gmail'] = 0
                logger.error(f"❌ Gmail processing failed: {e}")
        
        # Process Outlook emails
        if self.outlook_client:
            try:
                outlook_count = self._process_outlook_emails(months_back)
                results['outlook'] = outlook_count
                logger.info(f"📧 Processed {outlook_count} Outlook emails")
            except Exception as e:
                results['outlook'] = 0
                logger.error(f"❌ Outlook processing failed: {e}")
        
        # Update provider statistics
        self._update_provider_stats(results)
        
        return results
    
    def _process_gmail_emails(self, months_back: int) -> int:
        """Process Gmail emails and store in unified table"""
        # Get Gmail messages
        messages = self.gmail_client.search_credit_card_emails(months_back)
        processed_count = 0
        
        for message in messages:
            msg_id = message['id']
            
            # Skip if already processed
            if self._is_email_processed('gmail', msg_id):
                continue
            
            try:
                # Get message details
                msg_details = self.gmail_client.get_message_details(msg_id)
                if not msg_details:
                    continue
                
                # Extract information
                payload = msg_details.get('payload', {})
                headers = payload.get('headers', [])
                
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), '')
                date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
                snippet = msg_details.get('snippet', '')
                
                # Get email body
                email_body = self.gmail_client.get_email_body(msg_id)
                
                # Extract password hints and rules
                hints, rules = self.gmail_client.extract_password_rules_and_hints(
                    email_body, subject, sender
                )
                
                # Download attachments
                downloaded_files = self.gmail_client.download_pdf_attachments(msg_id, payload)
                
                # Store in unified table
                self._store_unified_email(
                    provider='gmail',
                    original_id=msg_id,
                    subject=subject,
                    sender=sender,
                    sender_email=sender,
                    date=date,
                    snippet=snippet,
                    password_hints=hints,
                    password_rules=rules,
                    attachments=downloaded_files,
                    email_body=email_body
                )
                
                processed_count += 1
                
            except Exception as e:
                logger.error(f"Failed to process Gmail message {msg_id}: {e}")
        
        return processed_count
    
    def _process_outlook_emails(self, months_back: int) -> int:
        """Process Outlook emails and store in unified table"""
        # Get Outlook messages
        messages = self.outlook_client.search_bank_emails(months_back)
        processed_count = 0
        
        for message in messages:
            msg_id = message['id']
            
            # Skip if already processed
            if self._is_email_processed('outlook', msg_id):
                continue
            
            try:
                # Get full message details
                full_message = self.outlook_client.get_email_details(msg_id)
                if not full_message:
                    continue
                
                # Extract email body
                email_body = self.outlook_client.extract_email_body(full_message)
                
                # Extract password hints and rules
                hints, rules = self.outlook_client.extract_password_rules_and_hints(
                    email_body,
                    full_message.get('subject', ''),
                    full_message.get('sender', {}).get('emailAddress', {}).get('address', '')
                )
                
                # Download attachments
                attachments = full_message.get('attachments', [])
                downloaded_files = []
                
                if attachments:
                    downloaded_files = self.outlook_client.download_attachments(msg_id, attachments)
                
                # Extract sender information
                sender_info = full_message.get('sender', {})
                sender_name = sender_info.get('emailAddress', {}).get('name', '')
                sender_email = sender_info.get('emailAddress', {}).get('address', '')
                
                # Store in unified table
                self._store_unified_email(
                    provider='outlook',
                    original_id=msg_id,
                    subject=full_message.get('subject', ''),
                    sender=sender_name,
                    sender_email=sender_email,
                    date=full_message.get('receivedDateTime', ''),
                    snippet=full_message.get('bodyPreview', ''),
                    password_hints=hints,
                    password_rules=rules,
                    attachments=downloaded_files,
                    email_body=email_body
                )
                
                processed_count += 1
                
            except Exception as e:
                logger.error(f"Failed to process Outlook message {msg_id}: {e}")
        
        return processed_count
    
    def _is_email_processed(self, provider: str, original_id: str) -> bool:
        """Check if email is already processed"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            SELECT id FROM unified_emails 
            WHERE provider = ? AND original_id = ?
        ''', (provider, original_id))
        
        result = c.fetchone()
        conn.close()
        
        return result is not None
    
    def _store_unified_email(self, provider: str, original_id: str, subject: str, 
                           sender: str, sender_email: str, date: str, snippet: str,
                           password_hints: List[str], password_rules: List[str],
                           attachments: List[str], email_body: str):
        """Store email in unified table"""
        
        # Generate unified ID
        unified_id = f"{provider}_{original_id}"
        
        # Convert date to timestamp
        try:
            if provider == 'gmail':
                dt = datetime.strptime(date, '%a, %d %b %Y %H:%M:%S %z')
            else:  # outlook
                dt = datetime.fromisoformat(date.replace('Z', '+00:00'))
            timestamp = int(dt.timestamp())
        except:
            timestamp = int(datetime.now().timestamp())
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            INSERT OR REPLACE INTO unified_emails 
            (id, provider, original_id, subject, sender, sender_email, date, snippet,
             password_hints, password_rules, attachments, timestamp, email_body, processed_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            unified_id, provider, original_id, subject, sender, sender_email, date, snippet,
            json.dumps(password_hints), json.dumps(password_rules), json.dumps(attachments),
            timestamp, email_body, datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def _update_provider_stats(self, results: Dict[str, int]):
        """Update provider statistics"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        for provider, count in results.items():
            c.execute('''
                UPDATE email_providers 
                SET last_sync = ?, total_emails = total_emails + ?
                WHERE type = ?
            ''', (datetime.now().isoformat(), count, provider))
        
        conn.commit()
        conn.close()
    
    def get_all_emails(self, limit: int = 100) -> List[Dict]:
        """Get all processed emails from all providers"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            SELECT id, provider, subject, sender, sender_email, date, snippet,
                   password_hints, password_rules, attachments, unlock_attempts,
                   unlock_success, successful_password
            FROM unified_emails 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (limit,))
        
        emails = []
        for row in c.fetchall():
            emails.append({
                'id': row[0],
                'provider': row[1],
                'subject': row[2],
                'sender': row[3],
                'sender_email': row[4],
                'date': row[5],
                'snippet': row[6],
                'password_hints': json.loads(row[7]) if row[7] else [],
                'password_rules': json.loads(row[8]) if row[8] else [],
                'attachments': json.loads(row[9]) if row[9] else [],
                'unlock_attempts': row[10],
                'unlock_success': row[11],
                'successful_password': row[12]
            })
        
        conn.close()
        return emails
    
    def unlock_all_pdfs(self):
        """Unlock PDFs from all providers using the Gmail client's enhanced unlock method"""
        if not self.gmail_client:
            logger.error("❌ Gmail client not initialized. Cannot unlock PDFs.")
            return
        
        # Get all emails with attachments
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            SELECT id, provider, original_id, subject, sender, password_hints, 
                   password_rules, attachments, email_body, unlock_attempts
            FROM unified_emails 
            WHERE attachments IS NOT NULL AND attachments != "[]"
            AND unlock_success = 0
        ''')
        
        rows = c.fetchall()
        conn.close()
        
        unlocked_count = 0
        total_pdfs = 0
        
        for row in rows:
            unified_id, provider, original_id, subject, sender, hints_json, rules_json, attachments_json, email_body, unlock_attempts = row
            
            # Parse JSON data
            hints = json.loads(hints_json) if hints_json else []
            rules = json.loads(rules_json) if rules_json else []
            attachments = json.loads(attachments_json) if attachments_json else []
            
            print(f"\n📧 Processing email: {subject} (Provider: {provider})")
            print(f"🔍 Password rules found: {len(rules)}")
            print(f"💡 Password hints found: {len(hints)}")
            
            # Generate password candidates using Gmail client's enhanced method
            # Create a temporary email ID for the Gmail client
            temp_email_id = f"temp_{unified_id}"
            
            # Store temporary email data in Gmail format for password generation
            self._store_temp_gmail_email(temp_email_id, subject, sender, hints, rules, attachments, email_body)
            
            # Generate candidates
            candidates = self.gmail_client.generate_passwords_for_email(temp_email_id)
            
            # Clean up temporary email
            self._cleanup_temp_gmail_email(temp_email_id)
            
            print(f"🎯 Generated {len(candidates)} password candidates")
            
            # Try to unlock each PDF
            for pdf_path in attachments:
                total_pdfs += 1
                if os.path.exists(pdf_path):
                    unlocked_path = self.gmail_client.try_unlock_pdf_enhanced(pdf_path, candidates, unified_id)
                    if unlocked_path:
                        unlocked_count += 1
                        self._mark_pdf_unlocked(unified_id, candidates[0].password if candidates else "unknown")
                        print(f"✅ Unlocked: {pdf_path}")
                    else:
                        self._update_unlock_attempts(unified_id, unlock_attempts + 1)
                        print(f"❌ Failed to unlock: {pdf_path}")
                else:
                    print(f"⚠️ File not found: {pdf_path}")
        
        print(f"\n📊 Summary: {unlocked_count}/{total_pdfs} PDFs unlocked successfully")
    
    def _store_temp_gmail_email(self, temp_id: str, subject: str, sender: str, hints: List[str], rules: List[str], attachments: List[str], email_body: str):
        """Store temporary email data for Gmail client processing"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            INSERT OR REPLACE INTO emails 
            (id, subject, sender, date, snippet, password_hints, password_rules, attachments, timestamp, email_body, processed_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            temp_id, subject, sender, datetime.now().isoformat(), "",
            json.dumps(hints), json.dumps(rules), json.dumps(attachments),
            int(datetime.now().timestamp()), email_body, datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def _cleanup_temp_gmail_email(self, temp_id: str):
        """Clean up temporary email data"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('DELETE FROM emails WHERE id = ?', (temp_id,))
        
        conn.commit()
        conn.close()
    
    def _mark_pdf_unlocked(self, unified_id: str, password: str):
        """Mark PDF as successfully unlocked"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            UPDATE unified_emails 
            SET unlock_success = 1, successful_password = ?
            WHERE id = ?
        ''', (password, unified_id))
        
        conn.commit()
        conn.close()
    
    def _update_unlock_attempts(self, unified_id: str, attempts: int):
        """Update unlock attempt count"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            UPDATE unified_emails 
            SET unlock_attempts = ?
            WHERE id = ?
        ''', (attempts, unified_id))
        
        conn.commit()
        conn.close()
    
    def get_statistics(self) -> Dict:
        """Get comprehensive statistics"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Total emails by provider
        c.execute('''
            SELECT provider, COUNT(*) as count
            FROM unified_emails 
            GROUP BY provider
        ''')
        provider_counts = dict(c.fetchall())
        
        # Emails with attachments
        c.execute('''
            SELECT COUNT(*) 
            FROM unified_emails 
            WHERE attachments IS NOT NULL AND attachments != "[]"
        ''')
        emails_with_attachments = c.fetchone()[0]
        
        # Successfully unlocked PDFs
        c.execute('''
            SELECT COUNT(*) 
            FROM unified_emails 
            WHERE unlock_success = 1
        ''')
        unlocked_pdfs = c.fetchone()[0]
        
        # Total unlock attempts
        c.execute('''
            SELECT SUM(unlock_attempts) 
            FROM unified_emails
        ''')
        total_attempts = c.fetchone()[0] or 0
        
        conn.close()
        
        return {
            'total_emails': sum(provider_counts.values()),
            'provider_counts': provider_counts,
            'emails_with_attachments': emails_with_attachments,
            'unlocked_pdfs': unlocked_pdfs,
            'total_unlock_attempts': total_attempts,
            'unlock_success_rate': (unlocked_pdfs / emails_with_attachments * 100) if emails_with_attachments > 0 else 0
        }

# Example usage
if __name__ == "__main__":
    # Initialize unified client
    client = UnifiedEmailClient()
    
    # Add Gmail provider
    gmail_added = client.add_gmail_provider("Gmail", "credentials.json")
    
    # Add Outlook provider (replace with your actual client ID)
    outlook_added = client.add_outlook_provider("Outlook", "YOUR_CLIENT_ID")
    
    if gmail_added or outlook_added:
        print("✅ Email providers configured")
        
        # List providers
        providers = client.list_providers()
        print(f"📋 Configured providers: {len(providers)}")
        
        # Authenticate all providers
        auth_results = client.authenticate_all()
        print(f"🔐 Authentication results: {auth_results}")
        
        # Process emails from all providers
        process_results = client.process_all_emails()
        print(f"📧 Processing results: {process_results}")
        
        # Get statistics
        stats = client.get_statistics()
        print(f"📊 Statistics: {stats}")
        
        # Unlock all PDFs
        client.unlock_all_pdfs()
        
    else:
        print("❌ No email providers configured")
