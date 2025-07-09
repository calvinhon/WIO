#!/usr/bin/env python3
"""
Personal Data Setup Utility
This script helps you set up personal data that will be used for PDF password generation.
"""

import sqlite3
from datetime import datetime
import json
import re

class PersonalDataManager:
    
    def __init__(self, db_path='email_data.db'):
        self.db_path = db_path
        self._init_db()
        self._insert_default_data_if_empty()
    
    def _init_db(self):
        """Initialize database if it doesn't exist"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Check if table exists and get its schema
        c.execute("PRAGMA table_info(personal_data)")
        columns = [column[1] for column in c.fetchall()]
        
        if not columns:
            # Create new table with all columns
            c.execute('''
                CREATE TABLE personal_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data_type TEXT,
                    data_value TEXT,
                    description TEXT,
                    created_date TEXT,
                    source TEXT DEFAULT 'manual',
                    confidence REAL DEFAULT 1.0
                )
            ''')
            print("✅ Created new personal_data table with enhanced schema")
        else:
            # Check if we need to add new columns
            if 'source' not in columns:
                c.execute('ALTER TABLE personal_data ADD COLUMN source TEXT DEFAULT "manual"')
                print("✅ Added 'source' column to personal_data table")
            
            if 'confidence' not in columns:
                c.execute('ALTER TABLE personal_data ADD COLUMN confidence REAL DEFAULT 1.0')
                print("✅ Added 'confidence' column to personal_data table")
        
        conn.commit()
        conn.close()
    
    def _insert_default_data_if_empty(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM personal_data')
        count = c.fetchone()[0]
        if count == 0:
            # Add default values — customize as needed
            default_data = [
                ('date_of_birth', '10031984', 'Default DOB', 'manual', 1.0),
                ('mobile_number', '971525562885', 'UAE mobile', 'manual', 1.0),
                ('first_name', 'Nguyen', 'first name', 'manual', 1.0),
                ('last_name', 'Hoach', 'last name', 'manual', 1.0),
                ('card_number_last4', '1234', 'Dummy card last 4', 'manual', 1.0),
                ('account_number_last4', '5678', 'Dummy account last 4', 'manual', 1.0),
                ('national_id_last4', '9012', 'Dummy national ID', 'manual', 1.0),
                ('custom_hint', '19842885', 'DOB + mobile suffix', 'manual', 1.0),
            ]
            for data_type, value, description, source, confidence in default_data:
                c.execute('''
                    INSERT INTO personal_data (data_type, data_value, description, created_date, source, confidence)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (data_type, value, description, datetime.now().isoformat(), source, confidence))
            conn.commit()
            print("✅ Default personal data inserted.")
        conn.close()
    
    def add_personal_data(self, data_type, data_value, description="", source="manual", confidence=1.0):
        """Add personal data with source tracking"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Check if this exact data already exists
        c.execute('SELECT id FROM personal_data WHERE data_type = ? AND data_value = ?', (data_type, data_value))
        existing = c.fetchone()
        
        if existing:
            # Update confidence if auto-extracted data matches manual data
            if source == "auto_extract" and confidence > 0.8:
                c.execute('''
                    UPDATE personal_data 
                    SET confidence = MAX(confidence, ?), description = ?, source = ?
                    WHERE id = ?
                ''', (confidence, description, "verified", existing[0]))
                print(f"✅ Verified existing {data_type}: {data_value}")
            else:
                print(f"ℹ️ {data_type}: {data_value} already exists")
        else:
            c.execute('''
                INSERT INTO personal_data (data_type, data_value, description, created_date, source, confidence)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (data_type, data_value, description, datetime.now().isoformat(), source, confidence))
            print(f"✅ Added {data_type}: {data_value} (confidence: {confidence:.2f})")
        
        conn.commit()
        conn.close()
    
    def extract_from_emails(self, min_confidence=0.6):
        """Automatically extract personal data from emails in database"""
        print("\n🔍 Scanning emails for personal data...")
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # First, check what columns exist in the emails table
        try:
            c.execute("PRAGMA table_info(emails)")
            columns = [column[1] for column in c.fetchall()]
            print(f"📋 Available email columns: {', '.join(columns)}")
            
            # Build query based on available columns
            select_columns = ['id', 'subject', 'sender']
            
            # Check for various body/content column names
            body_columns = []
            for col in ['body_text', 'body_html', 'body', 'content', 'message_body', 'email_body']:
                if col in columns:
                    body_columns.append(col)
                    select_columns.append(col)
            
            # Check for attachments column
            if 'attachments' in columns:
                select_columns.append('attachments')
            else:
                select_columns.append('NULL as attachments')
            
            # Build the query
            query = f"SELECT {', '.join(select_columns)} FROM emails WHERE "
            
            # Build WHERE clause for content columns
            where_conditions = []
            for col in body_columns:
                where_conditions.append(f"{col} IS NOT NULL")
            
            if where_conditions:
                query += " OR ".join(where_conditions)
            else:
                # If no body columns, just get emails with subject
                query += "subject IS NOT NULL"
            
            print(f"🔍 Running query: {query}")
            c.execute(query)
            emails = c.fetchall()
            
        except Exception as e:
            print(f"❌ Error querying emails: {e}")
            # Fallback: try to get basic email info
            try:
                c.execute("SELECT id, subject, sender FROM emails WHERE subject IS NOT NULL")
                emails = c.fetchall()
                # Pad with None values for missing columns
                emails = [row + (None, None, None) for row in emails]
                body_columns = []
                print("⚠️ Using fallback query - only subject and sender available")
            except Exception as e2:
                print(f"❌ Fallback query also failed: {e2}")
                conn.close()
                return 0
        
        conn.close()
        
        if not emails:
            print("❌ No emails found in database")
            return 0
        
        print(f"📧 Found {len(emails)} emails to scan")
        extracted_count = 0
        
        for email_data in emails:
            # Unpack email data based on what we have
            email_id = email_data[0]
            subject = email_data[1] if len(email_data) > 1 else ""
            sender = email_data[2] if len(email_data) > 2 else ""
            
            # Combine all available content
            content = ""
            if subject:
                content += subject + " "
            if sender:
                content += sender + " "
            
            # Add body content if available
            body_start_index = 3
            for i, col in enumerate(body_columns):
                body_content = email_data[body_start_index + i] if len(email_data) > body_start_index + i else None
                if body_content:
                    content += str(body_content) + " "
            
            # Skip if no content to analyze
            if not content.strip():
                continue
            
            # Extract various data types
            try:
                extracted = self._extract_patterns(content, email_id, subject, sender)
                extracted_count += len(extracted)
                
                if extracted:
                    print(f"  📧 Email {email_id}: Found {len(extracted)} data points")
                    
            except Exception as e:
                print(f"  ❌ Error processing email {email_id}: {e}")
                continue
        
        print(f"✅ Extraction complete! Found {extracted_count} new data points")
        return extracted_count

    def check_email_table_schema(self):
        """Check and display the email table schema"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            # Check if emails table exists
            c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='emails'")
            if not c.fetchone():
                print("❌ No 'emails' table found in database")
                conn.close()
                return None
            
            # Get table schema
            c.execute("PRAGMA table_info(emails)")
            columns = c.fetchall()
            
            print("\n📋 Email Table Schema:")
            print("-" * 50)
            for col in columns:
                col_id, name, data_type, not_null, default, pk = col
                null_str = "NOT NULL" if not_null else "NULL"
                pk_str = "PRIMARY KEY" if pk else ""
                print(f"  {name} ({data_type}) {null_str} {pk_str}")
            
            # Get sample data
            c.execute("SELECT * FROM emails LIMIT 1")
            sample = c.fetchone()
            if sample:
                print(f"\n📊 Sample data (first row):")
                column_names = [col[1] for col in columns]
                for i, (col_name, value) in enumerate(zip(column_names, sample)):
                    value_preview = str(value)[:50] + "..." if value and len(str(value)) > 50 else str(value)
                    print(f"  {col_name}: {value_preview}")
            
            # Get count of emails with content
            content_columns = ['body_text', 'body_html', 'body', 'content', 'message_body', 'email_body']
            existing_content_cols = [col for col in content_columns if col in [c[1] for c in columns]]
            
            if existing_content_cols:
                conditions = [f"{col} IS NOT NULL AND {col} != ''" for col in existing_content_cols]
                query = f"SELECT COUNT(*) FROM emails WHERE " + " OR ".join(conditions)
                c.execute(query)
                content_count = c.fetchone()[0]
                print(f"\n📊 Emails with content: {content_count}")
            else:
                print("\n⚠️ No content columns found - extraction will be limited to subject/sender")
            
            conn.close()
            return [col[1] for col in columns]
            
        except Exception as e:
            print(f"❌ Error checking email schema: {e}")
            conn.close()
            return None

    def _extract_patterns(self, content, email_id, subject, sender):
        """Extract patterns from email content"""
        extracted = []
        
        # Bank names (common banks)
        bank_patterns = [
            r'\b(Emirates NBD|ADCB|FAB|HSBC|Citibank|Standard Chartered|Mashreq|DIB|RAKBANK|CBD|NBAD)\b',
            r'\b(Chase|Bank of America|Wells Fargo|Citibank|Capital One|American Express)\b',
            r'\b(Barclays|Lloyds|HSBC|NatWest|Santander|Halifax)\b'
        ]
        
        for pattern in bank_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                bank_name = match.upper()
                self.add_personal_data(
                    'bank_name', bank_name, 
                    f'Extracted from email: {subject[:50]}...', 
                    'auto_extract', 0.9
                )
                extracted.append(('bank_name', bank_name))
        
        # Card numbers (last 4 digits, masked format)
        card_patterns = [
            r'\*{4,12}(\d{4})',  # ****1234
            r'x{4,12}(\d{4})',   # xxxx1234
            r'\d{4}[\s\-]*\*{4,12}[\s\-]*\*{4,12}[\s\-]*(\d{4})',  # 1234 **** **** 5678
            r'ending\s+in\s+(\d{4})',  # ending in 1234
            r'last\s+4\s+digits?\s*:?\s*(\d{4})'  # last 4 digits: 1234
        ]
        
        for pattern in card_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                last4 = match if isinstance(match, str) else match[0] if match else ""
                if last4 and len(last4) == 4 and last4.isdigit():
                    self.add_personal_data(
                        'card_number_last4', last4,
                        f'Extracted from email: {subject[:50]}...',
                        'auto_extract', 0.8
                    )
                    extracted.append(('card_number_last4', last4))
        
        # Account numbers (various patterns)
        account_patterns = [
            r'account\s+(?:number\s+)?(?:ending\s+in\s+)?(\d{4,8})',
            r'a/c\s+(?:no\.?\s+)?(\d{4,12})',
            r'account\s*:\s*\*+(\d{4,8})',
            r'(\d{10,16})',  # Full account numbers
        ]
        
        for pattern in account_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                acc_num = match.strip()
                if acc_num and acc_num.isdigit():
                    if len(acc_num) >= 10:  # Full account number
                        # Store last 4 digits
                        last4 = acc_num[-4:]
                        self.add_personal_data(
                            'account_number_last4', last4,
                            f'From full account: {acc_num[:4]}...{last4}',
                            'auto_extract', 0.9
                        )
                        extracted.append(('account_number_last4', last4))
                        
                        # Store full number (for password attempts)
                        self.add_personal_data(
                            'account_number_full', acc_num,
                            f'Full account from email: {subject[:50]}...',
                            'auto_extract', 0.8
                        )
                        extracted.append(('account_number_full', acc_num))
                    elif len(acc_num) >= 4:  # Partial account number
                        self.add_personal_data(
                            'account_number_partial', acc_num,
                            f'Partial account from email: {subject[:50]}...',
                            'auto_extract', 0.7
                        )
                        extracted.append(('account_number_partial', acc_num))
        
        # Phone numbers
        phone_patterns = [
            r'(\+?\d{1,4}[\s\-]?\d{3}[\s\-]?\d{3}[\s\-]?\d{4})',  # International format
            r'(\d{10})',  # Simple 10 digit
            r'(\d{3}[\s\-]\d{3}[\s\-]\d{4})'  # US format
        ]
        
        for pattern in phone_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                phone = re.sub(r'[\s\-\+]', '', match)
                if len(phone) >= 10:
                    self.add_personal_data(
                        'mobile_number', phone,
                        f'Extracted from email: {subject[:50]}...',
                        'auto_extract', 0.7
                    )
                    extracted.append(('mobile_number', phone))
        
        # Dates (potential DOB or important dates)
        date_patterns = [
            r'\b(\d{1,2}/\d{1,2}/\d{4})\b',  # MM/DD/YYYY or DD/MM/YYYY
            r'\b(\d{1,2}-\d{1,2}-\d{4})\b',  # MM-DD-YYYY or DD-MM-YYYY
            r'\b(\d{8})\b',  # DDMMYYYY
            r'\b(\d{4}\d{2}\d{2})\b'  # YYYYMMDD
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                date_str = match.replace('/', '').replace('-', '')
                if len(date_str) == 8 and date_str.isdigit():
                    # Check if it looks like a reasonable date
                    try:
                        # Try DDMMYYYY format
                        day, month, year = int(date_str[:2]), int(date_str[2:4]), int(date_str[4:])
                        if 1 <= day <= 31 and 1 <= month <= 12 and 1900 <= year <= 2030:
                            self.add_personal_data(
                                'date_potential', date_str,
                                f'Potential date from email: {subject[:50]}...',
                                'auto_extract', 0.6
                            )
                            extracted.append(('date_potential', date_str))
                    except:
                        pass
        
        # Names (from sender information)
        if sender and '@' in sender:
            # Extract name from email sender
            name_part = sender.split('@')[0]
            name_match = re.search(r'([A-Za-z]+)\s+([A-Za-z]+)', sender)
            if name_match:
                first_name, last_name = name_match.groups()
                self.add_personal_data(
                    'first_name', first_name.title(),
                    f'From sender: {sender}',
                    'auto_extract', 0.6
                )
                self.add_personal_data(
                    'last_name', last_name.title(),
                    f'From sender: {sender}',
                    'auto_extract', 0.6
                )
                extracted.extend([('first_name', first_name), ('last_name', last_name)])
        
        return extracted
    
    def list_personal_data(self, show_auto_extracted=True):
        """List all personal data with source information"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        if show_auto_extracted:
            c.execute('SELECT id, data_type, data_value, description, created_date, source, confidence FROM personal_data ORDER BY data_type, confidence DESC')
        else:
            c.execute('SELECT id, data_type, data_value, description, created_date, source, confidence FROM personal_data WHERE source != "auto_extract" ORDER BY data_type')
        
        rows = c.fetchall()
        conn.close()
        
        if not rows:
            print("No personal data found.")
            return
        
        print(f"\n📋 Personal Data ({len(rows)} items):")
        print("-" * 100)
        
        current_type = None
        for row in rows:
            id_val, data_type, data_value, description, created_date, source, confidence = row
            
            if data_type != current_type:
                if current_type is not None:
                    print()
                print(f"🔸 {data_type.upper().replace('_', ' ')}")
                current_type = data_type
            
            source_icon = "🤖" if source == "auto_extract" else "✅" if source == "verified" else "👤"
            confidence_str = f" ({confidence:.1%})" if source == "auto_extract" else ""
            
            print(f"  {source_icon} ID:{id_val} | {data_value} | {description}{confidence_str}")
        print("-" * 100)
    
    def delete_personal_data(self, data_id):
        """Delete personal data by ID"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('DELETE FROM personal_data WHERE id = ?', (data_id,))
        conn.commit()
        deleted = c.rowcount > 0
        conn.close()
        
        if deleted:
            print(f"✅ Deleted personal data with ID: {data_id}")
        else:
            print(f"❌ No personal data found with ID: {data_id}")
    
    def cleanup_low_confidence_data(self, min_confidence=0.5):
        """Remove auto-extracted data with low confidence"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('SELECT COUNT(*) FROM personal_data WHERE source = "auto_extract" AND confidence < ?', (min_confidence,))
        count = c.fetchone()[0]
        
        if count == 0:
            print("No low-confidence data to clean up.")
            return
        
        print(f"Found {count} low-confidence entries. Delete them? (y/n): ", end="")
        if input().lower() == 'y':
            c.execute('DELETE FROM personal_data WHERE source = "auto_extract" AND confidence < ?', (min_confidence,))
            conn.commit()
            deleted = c.rowcount
            print(f"✅ Deleted {deleted} low-confidence entries")
        
        conn.close()
    
    def setup_interactive(self):
        """Interactive setup of personal data"""
        print("🔧 Personal Data Setup for PDF Password Generation")
        print("=" * 60)
        
        # Check email table schema first
        print("\n🔍 Step 0: Checking email database schema...")
        email_columns = self.check_email_table_schema()
        
        if not email_columns:
            print("⚠️ No email data found. Skipping auto-extraction.")
            auto_extract = False
        else:
            print(f"✅ Email table found with {len(email_columns)} columns")
            auto_extract = True
        
        # Try auto-extraction if possible
        if auto_extract:
            print("\n🤖 Step 1: Auto-extracting data from emails...")
            try:
                extracted_count = self.extract_from_emails()
                if extracted_count > 0:
                    print(f"✅ Found {extracted_count} data points from emails!")
                    print("\n📋 Review auto-extracted data:")
                    self.list_personal_data()
                    
                    print("\nDo you want to clean up low-confidence data? (y/n): ", end="")
                    if input().lower() == 'y':
                        self.cleanup_low_confidence_data()
            except Exception as e:
                print(f"❌ Auto-extraction failed: {e}")
                print("💡 Continuing with manual setup...")
        
        print("\n👤 Step 2: Manual data entry...")
        
        # Common personal data types
        data_types = [
            ('date_of_birth', 'Date of birth (DDMMYYYY format)', 'e.g., 10031984'),
            ('mobile_number', 'Mobile/Phone number', 'e.g., 971525562885'),
            ('first_name', 'First name', 'e.g., Calvin'),
            ('last_name', 'Last name', 'e.g., Hon'),
            ('card_number_last4', 'Last 4 digits of credit card', 'e.g., 1234'),
            ('account_number_last4', 'Last 4 digits of account number', 'e.g., 5678'),
            ('national_id_last4', 'Last 4 digits of national ID', 'e.g., 9012'),
            ('bank_name', 'Bank name', 'e.g., Emirates NBD, HSBC'),
            ('custom', 'Custom password hint', 'Any custom hint you know')
        ]
        
        for data_type, description, example in data_types:
            print(f"\n📝 {description}")
            print(f"Example: {example}")
            
            if data_type == 'custom':
                # Allow multiple custom entries
                while True:
                    value = input(f"Enter custom password hint (or press Enter to skip): ").strip()
                    if not value:
                        break
                    desc = input(f"Enter description for '{value}': ").strip()
                    self.add_personal_data('custom_hint', value, desc, 'manual', 1.0)
                break
            else:
                value = input(f"Enter {description} (or press Enter to skip): ").strip()
                if value:
                    self.add_personal_data(data_type, value, description, 'manual', 1.0)
        
        print("\n✅ Personal data setup complete!")
        print("You can now run the email processing script to unlock PDFs.")

def main():
    manager = PersonalDataManager()
    
    while True:
        print("\n🔐 Personal Data Manager")
        print("1. Interactive Setup")
        print("2. List Personal Data")
        print("3. Add Single Item")
        print("4. Delete Item")
        print("5. Auto-Extract from Emails")
        print("6. Clean Low-Confidence Data")
        print("7. List Manual Data Only")
        print("8. Check Email Table Schema")
        print("9. Exit")
        
        choice = input("\nSelect option (1-9): ").strip()
        
        if choice == '1':
            manager.setup_interactive()
        
        elif choice == '2':
            manager.list_personal_data()
        
        elif choice == '3':
            data_type = input("Enter data type: ").strip()
            data_value = input("Enter data value: ").strip()
            description = input("Enter description (optional): ").strip()
            if data_type and data_value:
                manager.add_personal_data(data_type, data_value, description, 'manual', 1.0)
            else:
                print("❌ Data type and value are required!")
        
        elif choice == '4':
            manager.list_personal_data()
            try:
                data_id = int(input("Enter ID to delete: "))
                manager.delete_personal_data(data_id)
            except ValueError:
                print("❌ Invalid ID!")
        
        elif choice == '5':
            print("\n🤖 Auto-extracting personal data from emails...")
            try:
                extracted_count = manager.extract_from_emails()
                print(f"✅ Extraction complete! Found {extracted_count} new data points")
            except Exception as e:
                print(f"❌ Extraction failed: {e}")
        
        elif choice == '6':
            manager.cleanup_low_confidence_data()
        
        elif choice == '7':
            manager.list_personal_data(show_auto_extracted=False)
        
        elif choice == '8':
            manager.check_email_table_schema()
        
        elif choice == '9':
            print("👋 Goodbye!")
            break
        
        else:
            print("❌ Invalid choice!")

if __name__ == "__main__":
    main()