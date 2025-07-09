#!/usr/bin/env python3
"""
Main Email Processing Script
This script processes emails, extracts password rules, and unlocks PDFs.
"""

import sys
import os
import json
import sqlite3
from datetime import datetime
from enhanced_gmail_client import EnhancedGmailClient
from personal_data_manager import PersonalDataManager

def display_email_stats(db_path='email_data.db'):
    """Display statistics about processed emails"""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Get total emails
    c.execute('SELECT COUNT(*) FROM emails')
    total_emails = c.fetchone()[0]
    
    # Get emails with attachments
    c.execute('SELECT COUNT(*) FROM emails WHERE attachments IS NOT NULL AND attachments != "[]"')
    emails_with_attachments = c.fetchone()[0]
    
    # Get emails with password hints
    c.execute('SELECT COUNT(*) FROM emails WHERE password_hints IS NOT NULL AND password_hints != "[]"')
    emails_with_hints = c.fetchone()[0]
    
    # Get emails with password rules
    c.execute('SELECT COUNT(*) FROM emails WHERE password_rules IS NOT NULL AND password_rules != "[]"')
    emails_with_rules = c.fetchone()[0]
    
    # Get recent emails (last 7 days)
    c.execute('SELECT COUNT(*) FROM emails WHERE processed_date > datetime("now", "-7 days")')
    recent_emails = c.fetchone()[0]
    
    conn.close()
    
    print("\n📊 Email Processing Statistics")
    print("=" * 50)
    print(f"Total emails processed: {total_emails}")
    print(f"Emails with PDF attachments: {emails_with_attachments}")
    print(f"Emails with password hints: {emails_with_hints}")
    print(f"Emails with password rules: {emails_with_rules}")
    print(f"Recently processed (last 7 days): {recent_emails}")

def display_recent_emails(db_path='email_data.db', limit=10):
    """Display recently processed emails with their password info"""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    c.execute('''
        SELECT subject, sender, password_hints, password_rules, attachments, processed_date
        FROM emails 
        ORDER BY processed_date DESC 
        LIMIT ?
    ''', (limit,))
    
    rows = c.fetchall()
    conn.close()
    
    if not rows:
        print("No emails found.")
        return
    
    print(f"\n📧 Last {len(rows)} Processed Emails")
    print("=" * 80)
    
    for i, row in enumerate(rows, 1):
        subject, sender, hints_json, rules_json, attachments_json, processed_date = row
        
        hints = json.loads(hints_json) if hints_json else []
        rules = json.loads(rules_json) if rules_json else []
        attachments = json.loads(attachments_json) if attachments_json else []
        
        print(f"\n{i}. Subject: {subject}")
        print(f"   From: {sender}")
        print(f"   Processed: {processed_date}")
        print(f"   Attachments: {len(attachments)}")
        print(f"   Password hints: {len(hints)}")
        if hints:
            print(f"   Hints: {', '.join(hints[:3])}{'...' if len(hints) > 3 else ''}")
        print(f"   Password rules: {len(rules)}")
        if rules:
            print(f"   Rules: {rules[0][:50]}{'...' if len(rules[0]) > 50 else ''}")

def test_pdf_unlock(db_path='email_data.db'):
    """Test PDF unlocking with current data"""
    client = EnhancedGmailClient(db_path=db_path)
    
    # Get personal data count
    personal_data = client.get_personal_data()
    print(f"\n🔐 Personal data entries: {len(personal_data)}")
    
    if len(personal_data) == 0:
        print("⚠️ No personal data found! Please run setup first.")
        return
    
    # Show personal data types
    data_types = list(set([data[0] for data in personal_data]))
    print(f"Data types available: {', '.join(data_types)}")
    
    # Get PDFs to unlock
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''
        SELECT COUNT(*) FROM emails 
        WHERE attachments IS NOT NULL AND attachments != "[]"
    ''')
    pdf_count = c.fetchone()[0]
    conn.close()
    
    print(f"📄 Emails with PDFs to unlock: {pdf_count}")
    
    if pdf_count == 0:
        print("No PDFs found to unlock.")
        return
    
    # Perform unlock
    print("\n🔓 Starting PDF unlock process...")
    client.unlock_pdfs()

def main():
    """Main function with interactive menu"""
    print("📬 Enhanced Gmail PDF Statement Processor")
    print("=" * 50)
    
    # Check if credentials exist
    if not os.path.exists('credentials.json'):
        print("❌ credentials.json not found!")
        print("Please download it from Google Cloud Console and place it in the current directory.")
        return
    
    while True:
        print("\n🔧 Main Menu")
        print("1. Setup Personal Data")
        print("2. Process New Emails")
        print("3. View Email Statistics")
        print("4. View Recent Emails")
        print("5. Test PDF Unlock")
        print("6. Unlock All PDFs")
        print("7. Database Management")
        print("8. Exit")
        
        choice = input("\nSelect option (1-8): ").strip()
        
        if choice == '1':
            manager = PersonalDataManager()
            manager.setup_interactive()
        
        elif choice == '2':
            print("\n📥 Processing new emails...")
            try:
                client = EnhancedGmailClient()
                client.process_new_statements()
            except Exception as e:
                print(f"❌ Error processing emails: {e}")
        
        elif choice == '3':
            display_email_stats()
        
        elif choice == '4':
            try:
                limit = int(input("How many recent emails to show? (default 10): ") or "10")
                display_recent_emails(limit=limit)
            except ValueError:
                display_recent_emails()
        
        elif choice == '5':
            test_pdf_unlock()
        
        elif choice == '6':
            print("\n🔓 Unlocking all PDFs...")
            try:
                client = EnhancedGmailClient()
                client.unlock_pdfs()
            except Exception as e:
                print(f"❌ Error unlocking PDFs: {e}")
        
        elif choice == '7':
            database_management_menu()
        
        elif choice == '8':
            print("👋 Goodbye!")
            break
        
        else:
            print("❌ Invalid choice!")

def database_management_menu():
    """Database management submenu"""
    while True:
        print("\n🗄️ Database Management")
        print("1. View Personal Data")
        print("2. Add Personal Data")
        print("3. Delete Personal Data")
        print("4. Clear All Emails")
        print("5. Export Data")
        print("6. Back to Main Menu")
        
        choice = input("\nSelect option (1-6): ").strip()
        
        if choice == '1':
            manager = PersonalDataManager()
            manager.list_personal_data()
        
        elif choice == '2':
            manager = PersonalDataManager()
            data_type = input("Enter data type: ").strip()
            data_value = input("Enter data value: ").strip()
            description = input("Enter description (optional): ").strip()
            if data_type and data_value:
                manager.add_personal_data(data_type, data_value, description)
            else:
                print("❌ Data type and value are required!")
        
        elif choice == '3':
            manager = PersonalDataManager()
            manager.list_personal_data()
            try:
                data_id = int(input("Enter ID to delete: "))
                manager.delete_personal_data(data_id)
            except ValueError:
                print("❌ Invalid ID!")
        
        elif choice == '4':
            confirm = input("⚠️ Are you sure you want to clear all emails? (yes/no): ").strip().lower()
            if confirm == 'yes':
                clear_all_emails()
            else:
                print("Operation cancelled.")
        
        elif choice == '5':
            export_data()
        
        elif choice == '6':
            break
        
        else:
            print("❌ Invalid choice!")

def clear_all_emails(db_path='email_data.db'):
    """Clear all email data"""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('DELETE FROM emails')
    deleted = c.rowcount
    conn.commit()
    conn.close()
    print(f"✅ Deleted {deleted} email records.")

def export_data(db_path='email_data.db'):
    """Export data to JSON file"""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Export emails
    c.execute('SELECT * FROM emails')
    emails = c.fetchall()
    
    # Export personal data
    c.execute('SELECT * FROM personal_data')
    personal_data = c.fetchall()
    
    conn.close()
    
    export_data = {
        'emails': emails,
        'personal_data': personal_data,
        'exported_at': datetime.now().isoformat()
    }
    
    filename = f"email_data_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(export_data, f, indent=2)
    
    print(f"✅ Data exported to {filename}")

if __name__ == "__main__":
    main()