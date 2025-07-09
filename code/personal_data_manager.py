#!/usr/bin/env python3
"""
Personal Data Setup Utility
This script helps you set up personal data that will be used for PDF password generation.
"""

import sqlite3
from datetime import datetime
import json

class PersonalDataManager:
    
    def _insert_default_data_if_empty(self):
	    conn = sqlite3.connect(self.db_path)
	    c = conn.cursor()
	    c.execute('SELECT COUNT(*) FROM personal_data')
	    count = c.fetchone()[0]
	    if count == 0:
	        # Add default values — customize as needed
	        default_data = [
	            ('date_of_birth', '10031984', 'Default DOB'),
	            ('mobile_number', '971525562885', 'UAE mobile'),
	            ('first_name', 'Nguyen', 'Vietnamese first name'),
	            ('last_name', 'Hoach', 'Vietnamese last name'),
	            ('card_number_last4', '1234', 'Dummy card last 4'),
	            ('account_number_last4', '5678', 'Dummy account last 4'),
	            ('national_id_last4', '9012', 'Dummy national ID'),
	            ('custom_hint', '19842885', 'DOB + mobile suffix'),
	        ]
	        for data_type, value, description in default_data:
	            c.execute('''
	                INSERT INTO personal_data (data_type, data_value, description, created_date)
	                VALUES (?, ?, ?, ?)
	            ''', (data_type, value, description, datetime.now().isoformat()))
	        conn.commit()
	        print("✅ Default personal data inserted.")
	    conn.close()
    
    def __init__(self, db_path='email_data.db'):
        self.db_path = db_path
        self._init_db()
        self._insert_default_data_if_empty()
    
    def _init_db(self):
        """Initialize database if it doesn't exist"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
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
        """Add personal data"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            INSERT OR REPLACE INTO personal_data (data_type, data_value, description, created_date)
            VALUES (?, ?, ?, ?)
        ''', (data_type, data_value, description, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        print(f"✅ Added {data_type}: {data_value}")
    
    def list_personal_data(self):
        """List all personal data"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT id, data_type, data_value, description, created_date FROM personal_data ORDER BY data_type')
        rows = c.fetchall()
        conn.close()
        
        if not rows:
            print("No personal data found.")
            return
        
        print("\n📋 Personal Data:")
        print("-" * 80)
        for row in rows:
            id_val, data_type, data_value, description, created_date = row
            print(f"ID: {id_val}")
            print(f"Type: {data_type}")
            print(f"Value: {data_value}")
            print(f"Description: {description}")
            print(f"Created: {created_date}")
            print("-" * 80)
    
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
    
    def setup_interactive(self):
        """Interactive setup of personal data"""
        print("🔧 Personal Data Setup for PDF Password Generation")
        print("=" * 60)
        
        # Common personal data types
        data_types = [
            ('date_of_birth', 'Date of birth (DDMMYYYY format)', 'e.g., 100384'),
            ('mobile_number', 'Mobile/Phone number', 'e.g., 912525562885'),
            ('first_name', 'First name', 'e.g., Calvin'),
            ('last_name', 'Last name', 'e.g., Hon'),
            ('card_number_last4', 'Last 4 digits of credit card', 'e.g., 1234'),
            ('account_number_last4', 'Last 4 digits of account number', 'e.g., 5678'),
            ('national_id_last4', 'Last 4 digits of national ID', 'e.g., 9012'),
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
                    self.add_personal_data('custom_hint', value, desc)
                break
            else:
                value = input(f"Enter {description} (or press Enter to skip): ").strip()
                if value:
                    self.add_personal_data(data_type, value, description)
        
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
        print("5. Exit")
        
        choice = input("\nSelect option (1-5): ").strip()
        
        if choice == '1':
            manager.setup_interactive()
        
        elif choice == '2':
            manager.list_personal_data()
        
        elif choice == '3':
            data_type = input("Enter data type: ").strip()
            data_value = input("Enter data value: ").strip()
            description = input("Enter description (optional): ").strip()
            if data_type and data_value:
                manager.add_personal_data(data_type, data_value, description)
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
            print("👋 Goodbye!")
            break
        
        else:
            print("❌ Invalid choice!")

if __name__ == "__main__":
    main()