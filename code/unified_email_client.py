#!/usr/bin/env python3
"""
Unified Email Client
Manages multiple email providers (Gmail, Outlook) with a unified interface
"""

import json
import sqlite3
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

# Import email clients
try:
    from enhanced_gmail_client import EnhancedGmailClient, GmailConfig
except ImportError:
    print("Warning: Gmail client not available")
    EnhancedGmailClient = None
    GmailConfig = None

try:
    from outlook_client import OutlookClient, OutlookConfig
except ImportError:
    print("Warning: Outlook client not available")
    OutlookClient = None
    OutlookConfig = None

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class EmailProvider:
    """Email provider configuration"""
    name: str
    provider_type: str  # 'gmail' or 'outlook'
    config: Any  # GmailConfig or OutlookConfig
    enabled: bool = True

class UnifiedEmailClient:
    """Unified client for managing multiple email providers"""
    
    def __init__(self, db_path: str = 'email_data.db'):
        self.db_path = db_path
        self.providers: Dict[str, EmailProvider] = {}
        
        # Initialize database
        self._init_db()
        
        # Load existing providers
        self._load_providers()
    
    def _init_db(self):
        """Initialize the unified database with proper schema migration and type safety"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # Check if email_providers table exists
            c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='email_providers'")
            table_exists = c.fetchone() is not None
            
            if not table_exists:
                # Create new table with correct schema and explicit types
                c.execute('''
                    CREATE TABLE email_providers (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        provider_type TEXT NOT NULL,
                        config TEXT NOT NULL,
                        enabled INTEGER DEFAULT 1,
                        created_date TEXT,
                        last_sync TEXT
                    )
                ''')
                logger.info("Created email_providers table with proper schema")
            else:
                # Check and update existing table schema
                c.execute("PRAGMA table_info(email_providers)")
                columns = [column[1] for column in c.fetchall()]
                
                # Add missing columns with proper types
                if 'provider_type' not in columns:
                    c.execute('ALTER TABLE email_providers ADD COLUMN provider_type TEXT')
                    logger.info("Added provider_type column")
                
                if 'last_sync' not in columns:
                    c.execute('ALTER TABLE email_providers ADD COLUMN last_sync TEXT')
                    logger.info("Added last_sync column")
                
                if 'created_date' not in columns:
                    c.execute('ALTER TABLE email_providers ADD COLUMN created_date TEXT')
                    logger.info("Added created_date column")
                
                # Check for type mismatches and fix them
                try:
                    c.execute("SELECT id, enabled FROM email_providers LIMIT 1")
                    test_row = c.fetchone()
                    if test_row and not isinstance(test_row[1], int):
                        # Fix boolean/integer type issues
                        c.execute("UPDATE email_providers SET enabled = CASE WHEN enabled = 'True' OR enabled = '1' THEN 1 ELSE 0 END")
                        logger.info("Fixed enabled column data types")
                except Exception as type_error:
                    logger.warning(f"Type check/fix failed: {type_error}")
                
                # Migrate old 'type' column to 'provider_type' if needed
                if 'type' in columns and 'provider_type' not in columns:
                    c.execute('ALTER TABLE email_providers ADD COLUMN provider_type TEXT')
                    c.execute('UPDATE email_providers SET provider_type = type')
                    logger.info("Migrated type column to provider_type")
            
            # Create unified emails table with proper types
            c.execute('''
                CREATE TABLE IF NOT EXISTS emails (
                    id TEXT PRIMARY KEY,
                    provider_type TEXT,
                    provider_id TEXT,
                    subject TEXT,
                    sender TEXT,
                    sender_email TEXT,
                    date TEXT,
                    snippet TEXT,
                    attachments TEXT,
                    timestamp INTEGER DEFAULT 0,
                    email_body TEXT,
                    processed_date TEXT,
                    has_attachments INTEGER DEFAULT 0
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Unified database initialized successfully")
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    def _load_providers(self):
        """Load existing providers from database with improved error handling"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # Check which columns exist
            c.execute("PRAGMA table_info(email_providers)")
            columns = [column[1] for column in c.fetchall()]
            
            if not columns:
                logger.info("No email_providers table found - will be created when needed")
                conn.close()
                return
            
            if 'provider_type' in columns:
                c.execute('SELECT id, name, provider_type, config, enabled FROM email_providers')
            elif 'type' in columns:
                # Fallback to old column name
                c.execute('SELECT id, name, type as provider_type, config, enabled FROM email_providers')
            else:
                logger.warning("No provider_type or type column found in email_providers table")
                conn.close()
                return
            
            rows = c.fetchall()
            conn.close()
            
            for row in rows:
                try:
                    provider_id, name, provider_type, config_str, enabled = row
                    
                    # Skip rows with missing critical data
                    if not provider_id or not name or not provider_type:
                        logger.warning(f"Skipping provider with missing data: {row}")
                        continue
                    
                    config_data = json.loads(config_str) if config_str else {}
                    
                    if provider_type == 'gmail' and GmailConfig:
                        config = GmailConfig(**config_data)
                    elif provider_type == 'outlook' and OutlookConfig:
                        config = OutlookConfig(**config_data)
                    else:
                        logger.warning(f"Unknown or unavailable provider type: {provider_type}")
                        continue
                    
                    provider = EmailProvider(
                        name=name,
                        provider_type=provider_type,
                        config=config,
                        enabled=bool(enabled)
                    )
                    
                    self.providers[provider_id] = provider
                    
                except Exception as e:
                    logger.error(f"Failed to load provider {row}: {e}")
                    continue
                
            logger.info(f"Loaded {len(self.providers)} email providers")
            
        except Exception as e:
            logger.error(f"Failed to load providers: {e}")
            # Initialize empty providers dict if loading fails
            self.providers = {}
    
    def add_gmail_provider(self, name: str, credentials_file: str) -> bool:
        """Add a Gmail provider with improved error handling"""
        if not GmailConfig or not EnhancedGmailClient:
            logger.error("Gmail client not available")
            return False
            
        try:
            provider_id = f"gmail_{name.lower().replace(' ', '_')}"
            
            # Create Gmail config
            config = GmailConfig(
                credentials_file=credentials_file,
                token_file=f'./secret/gmail_token_{name.lower()}.pickle'
            )
            
            # Test the configuration
            client = EnhancedGmailClient(config, self.db_path)
            if not client.authenticate():
                logger.error("Gmail authentication failed")
                return False
            
            # Prepare config data as JSON string
            config_json = json.dumps({
                'credentials_file': config.credentials_file,
                'token_file': config.token_file
            })
            
            # Save to database with explicit data type conversion
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # First ensure the table has the correct schema
            c.execute("PRAGMA table_info(email_providers)")
            columns = [col[1] for col in c.fetchall()]
            
            if 'provider_type' not in columns:
                c.execute('ALTER TABLE email_providers ADD COLUMN provider_type TEXT')
                logger.info("Added provider_type column during Gmail provider setup")
            
            if 'created_date' not in columns:
                c.execute('ALTER TABLE email_providers ADD COLUMN created_date TEXT')
                logger.info("Added created_date column during Gmail provider setup")
            
            # Insert with explicit type casting
            c.execute('''
                INSERT OR REPLACE INTO email_providers 
                (id, name, provider_type, config, enabled, created_date)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                str(provider_id),           # Ensure string
                str(name),                  # Ensure string  
                str('gmail'),               # Ensure string
                str(config_json),           # Ensure string
                int(1),                     # Ensure integer (True as 1)
                str(datetime.now().isoformat())  # Ensure string
            ))
            
            conn.commit()
            conn.close()
            
            # Add to active providers
            provider = EmailProvider(
                name=name,
                provider_type='gmail',
                config=config,
                enabled=True
            )
            self.providers[provider_id] = provider
            
            logger.info(f"Gmail provider '{name}' added successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add Gmail provider: {e}")
            # Log more details for debugging
            logger.error(f"Provider name: {name}, credentials: {credentials_file}")
            return False
    
    def add_outlook_provider(self, name: str, client_id: str, tenant_id: str = "common") -> bool:
        """Add an Outlook provider with improved error handling"""
        if not OutlookConfig or not OutlookClient:
            logger.error("Outlook client not available")
            return False
            
        try:
            provider_id = f"outlook_{name.lower().replace(' ', '_')}"
            
            # Create Outlook config
            config = OutlookConfig(
                client_id=client_id,
                tenant_id=tenant_id
            )
            
            # Test the configuration
            client = OutlookClient(config, self.db_path)
            if not client.authenticate():
                logger.error("Outlook authentication failed")
                return False
            
            # Prepare config data as JSON string
            config_json = json.dumps({
                'client_id': config.client_id,
                'tenant_id': config.tenant_id
            })
            
            # Save to database with explicit data type conversion
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # First ensure the table has the correct schema
            c.execute("PRAGMA table_info(email_providers)")
            columns = [col[1] for col in c.fetchall()]
            
            if 'provider_type' not in columns:
                c.execute('ALTER TABLE email_providers ADD COLUMN provider_type TEXT')
                logger.info("Added provider_type column during Outlook provider setup")
            
            if 'created_date' not in columns:
                c.execute('ALTER TABLE email_providers ADD COLUMN created_date TEXT')
                logger.info("Added created_date column during Outlook provider setup")
            
            # Insert with explicit type casting
            c.execute('''
                INSERT OR REPLACE INTO email_providers 
                (id, name, provider_type, config, enabled, created_date)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                str(provider_id),           # Ensure string
                str(name),                  # Ensure string
                str('outlook'),             # Ensure string
                str(config_json),           # Ensure string
                int(1),                     # Ensure integer (True as 1)
                str(datetime.now().isoformat())  # Ensure string
            ))
            
            conn.commit()
            conn.close()
            
            # Add to active providers
            provider = EmailProvider(
                name=name,
                provider_type='outlook',
                config=config,
                enabled=True
            )
            self.providers[provider_id] = provider
            
            logger.info(f"Outlook provider '{name}' added successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add Outlook provider: {e}")
            # Log more details for debugging
            logger.error(f"Provider name: {name}, client_id: {client_id}, tenant_id: {tenant_id}")
            return False
    
    def list_providers(self) -> List[dict]:
        """List all configured providers with enhanced information and error handling"""
        providers = []
        
        try:
            # Get additional stats from database
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            for provider_id, provider in self.providers.items():
                try:
                    # Get email count for this provider (safe query)
                    c.execute('SELECT COUNT(*) FROM emails WHERE provider_id = ?', (provider_id,))
                    result = c.fetchone()
                    email_count = result[0] if result else 0
                    
                    # Get last sync info (safe query)
                    c.execute('SELECT last_sync FROM email_providers WHERE id = ?', (provider_id,))
                    last_sync_result = c.fetchone()
                    last_sync = last_sync_result[0] if last_sync_result else None
                    
                    providers.append({
                        'id': provider_id,
                        'name': provider.name,
                        'type': provider.provider_type,
                        'enabled': provider.enabled,
                        'last_sync': last_sync,
                        'total_emails': email_count
                    })
                except Exception as provider_error:
                    logger.warning(f"Error getting stats for provider {provider_id}: {provider_error}")
                    # Add provider without stats
                    providers.append({
                        'id': provider_id,
                        'name': provider.name,
                        'type': provider.provider_type,
                        'enabled': provider.enabled,
                        'last_sync': None,
                        'total_emails': 0
                    })
            
            conn.close()
            return providers
            
        except Exception as e:
            logger.error(f"Failed to list providers: {e}")
            # Return basic provider list without database stats
            basic_providers = []
            for provider_id, provider in self.providers.items():
                basic_providers.append({
                    'id': provider_id,
                    'name': provider.name,
                    'type': provider.provider_type,
                    'enabled': provider.enabled,
                    'last_sync': None,
                    'total_emails': 0
                })
            return basic_providers
    
    def authenticate_all(self) -> Dict[str, bool]:
        """Authenticate all providers with improved error handling"""
        results = {}
        
        if not self.providers:
            logger.warning("No providers configured for authentication")
            return results
        
        for provider_id, provider in self.providers.items():
            if not provider.enabled:
                results[provider.name.lower()] = False
                continue
            
            try:
                if provider.provider_type == 'gmail' and EnhancedGmailClient:
                    client = EnhancedGmailClient(provider.config, self.db_path)
                    success = client.authenticate()
                elif provider.provider_type == 'outlook' and OutlookClient:
                    client = OutlookClient(provider.config, self.db_path)
                    success = client.authenticate()
                else:
                    logger.warning(f"Unknown or unavailable provider type: {provider.provider_type}")
                    success = False
                
                results[provider.name.lower()] = success
                
                if success:
                    logger.info(f"✅ {provider.name} authenticated successfully")
                else:
                    logger.warning(f"❌ {provider.name} authentication failed")
                    
            except Exception as e:
                logger.error(f"❌ {provider.name} authentication error: {e}")
                results[provider.name.lower()] = False
        
        return results
    
    def process_all_emails(self, months_back: int = 2) -> Dict[str, int]:
        """Process emails from all enabled providers"""
        results = {}
        
        for provider_id, provider in self.providers.items():
            if not provider.enabled:
                continue
            
            try:
                processed_count = 0
                
                if provider.provider_type == 'gmail' and EnhancedGmailClient:
                    client = EnhancedGmailClient(provider.config, self.db_path)
                    if client.authenticate():
                        processed_count = client.process_new_emails(months_back)
                        # Copy to unified table
                        self._sync_gmail_emails(client, provider_id)
                        
                elif provider.provider_type == 'outlook' and OutlookClient:
                    client = OutlookClient(provider.config, self.db_path)
                    if client.authenticate():
                        # Use the correct method name: process_new_emails
                        processed_count = client.process_new_emails(months_back)
                        # Copy to unified table
                        self._sync_outlook_emails(client, provider_id)
                
                results[provider.name.lower()] = processed_count
                
                # Update last sync time
                self._update_last_sync(provider_id)
                
            except Exception as e:
                logger.error(f"Failed to process emails for {provider.name}: {e}")
                results[provider.name.lower()] = 0
        
        return results
    
    def _sync_gmail_emails(self, client, provider_id: str):
        """Sync Gmail emails to unified table"""
        try:
            # This would sync emails from Gmail client to unified table
            # Implementation depends on Gmail client structure
            pass
        except Exception as e:
            logger.error(f"Failed to sync Gmail emails: {e}")
    
    def _sync_outlook_emails(self, client, provider_id: str):
        """Sync Outlook emails to unified table"""
        try:
            # This would sync emails from Outlook client to unified table
            # Implementation depends on Outlook client structure
            pass
        except Exception as e:
            logger.error(f"Failed to sync Outlook emails: {e}")
    
    def _update_last_sync(self, provider_id: str):
        """Update last sync timestamp for provider"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            c.execute('''
                UPDATE email_providers 
                SET last_sync = ? 
                WHERE id = ?
            ''', (datetime.now().isoformat(), provider_id))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to update last sync for {provider_id}: {e}")
    
    def get_email_stats(self) -> dict:
        """Get unified email statistics with error handling"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # Check if emails table exists
            c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='emails'")
            if not c.fetchone():
                conn.close()
                return {
                    'total_emails': 0,
                    'by_provider': {},
                    'with_attachments': 0
                }
            
            # Total emails
            c.execute("SELECT COUNT(*) FROM emails")
            result = c.fetchone()
            total_emails = result[0] if result else 0
            
            # Emails by provider
            c.execute("SELECT provider_type, COUNT(*) FROM emails GROUP BY provider_type")
            by_provider = dict(c.fetchall())
            
            # Emails with attachments
            c.execute("SELECT COUNT(*) FROM emails WHERE has_attachments = 1")
            result = c.fetchone()
            with_attachments = result[0] if result else 0
            
            conn.close()
            
            return {
                'total_emails': total_emails,
                'by_provider': by_provider,
                'with_attachments': with_attachments
            }
            
        except Exception as e:
            logger.error(f"Failed to get email stats: {e}")
            return {
                'total_emails': 0,
                'by_provider': {},
                'with_attachments': 0
            }
    
    def get_statistics(self) -> dict:
        """Get comprehensive statistics for the unified system with error handling"""
        try:
            email_stats = self.get_email_stats()
            
            # Mock PDF unlock stats (you can implement real tracking later)
            unlocked_pdfs = 0
            total_unlock_attempts = 0
            unlock_success_rate = 0.0
            
            return {
                'total_emails': email_stats['total_emails'],
                'emails_with_attachments': email_stats['with_attachments'],
                'unlocked_pdfs': unlocked_pdfs,
                'total_unlock_attempts': total_unlock_attempts,
                'unlock_success_rate': unlock_success_rate,
                'provider_counts': email_stats['by_provider']
            }
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {
                'total_emails': 0,
                'emails_with_attachments': 0,
                'unlocked_pdfs': 0,
                'total_unlock_attempts': 0,
                'unlock_success_rate': 0.0,
                'provider_counts': {}
            }