#!/usr/bin/env python3
"""
Main Email Processing Script
This script processes emails, extracts password rules, and unlocks PDFs.
Supports both Gmail and Outlook email providers.
"""

import sys
import os
import json
import sqlite3
from datetime import datetime
from enhanced_gmail_client import EnhancedGmailClient
from personal_data_manager import PersonalDataManager
from unified_email_client import UnifiedEmailClient
from outlook_client import OutlookClient, OutlookConfig

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
    """Main function with updated menu including Outlook support"""
    print("📬 Enhanced Gmail PDF Statement Processor")
    print("==================================================")
    
    while True:
        print("\n🔧 Main Menu")
        print("1. Setup Personal Data")
        print("2. Setup Email Providers")
        print("3. Process New Emails (All Providers)")
        print("4. Process Gmail Only")
        print("5. Process Outlook Only")
        print("6. View Email Statistics")
        print("7. View Recent Emails")
        print("8. Test PDF Unlock")
        print("9. Unlock All PDFs")
        print("10. Database Management")
        print("11. Exit")
        
        choice = input("\nSelect option (1-11): ").strip()
        
        if choice == '1':
            manager = PersonalDataManager()
            manager.setup_interactive()
        
        elif choice == '2':
            setup_email_providers()
        
        elif choice == '3':
            process_all_providers()
        
        elif choice == '4':
            process_gmail_only()
        
        elif choice == '5':
            process_outlook_only()
        
        elif choice == '6':
            display_unified_email_stats()
        
        elif choice == '7':
            try:
                limit = int(input("How many recent emails to show? (default 10): ") or "10")
                display_recent_emails(limit=limit)
            except ValueError:
                display_recent_emails()
        
        elif choice == '8':
            test_pdf_unlock()
        
        elif choice == '9':
            unlock_all_pdfs_unified()
        
        elif choice == '10':
            database_management_menu()
        
        elif choice == '11':
            print("👋 Goodbye!")
            break
        
        else:
            print("❌ Invalid choice!")

def setup_email_providers():
    """Setup email providers (Gmail and Outlook)"""
    print("\n📧 Email Provider Setup")
    print("=" * 30)
    
    client = UnifiedEmailClient()
    
    while True:
        providers = client.list_providers()
        
        print(f"\n📋 Current providers ({len(providers)}):")
        for i, provider in enumerate(providers, 1):
            status = "✅ Enabled" if provider['enabled'] else "❌ Disabled"
            print(f"{i}. {provider['name']} ({provider['type']}) - {status}")
            print(f"   Last sync: {provider['last_sync'] or 'Never'}")
            print(f"   Total emails: {provider['total_emails']}")
        
        print("\n🔧 Options:")
        print("1. Add Gmail Provider")
        print("2. Add Outlook Provider")
        print("3. Test All Providers")
        print("4. Back to Main Menu")
        
        choice = input("\nSelect option (1-4): ").strip()
        
        if choice == '1':
            setup_gmail_provider(client)
        
        elif choice == '2':
            setup_outlook_provider(client)
        
        elif choice == '3':
            test_all_providers(client)
        
        elif choice == '4':
            break
        
        else:
            print("❌ Invalid choice!")

def setup_gmail_provider(client):
    """Setup Gmail provider"""
    print("\n📧 Gmail Provider Setup")
    print("=" * 25)
    
    credentials_file = input("Enter Gmail credentials file path (default: credentials.json): ").strip()
    if not credentials_file:
        credentials_file = "./secret/credentials.json"
    
    if not os.path.exists(credentials_file):
        print(f"❌ Credentials file not found: {credentials_file}")
        print("\n📋 To setup Gmail:")
        print("1. Go to Google Cloud Console (https://console.cloud.google.com/)")
        print("2. Create/select a project")
        print("3. Enable Gmail API")
        print("4. Create OAuth 2.0 credentials (Desktop application)")
        print("5. Download credentials as credentials.json")
        print("6. Place in the same directory as this script")
        return
    
    success = client.add_gmail_provider("Gmail", credentials_file)
    if success:
        print("✅ Gmail provider added successfully!")
        print("� You can now process Gmail emails")
    else:
        print("❌ Failed to add Gmail provider")

def setup_outlook_provider(client):
    """Setup Outlook provider"""
    print("\n📧 Outlook Provider Setup")
    print("=" * 27)
    
    print("📋 To setup Outlook, you need:")
    print("1. Azure App Registration client ID")
    print("2. Optional: Tenant ID (use 'common' for personal accounts)")
    print("\n📋 Setup instructions:")
    print("1. Go to Azure Portal (https://portal.azure.com/)")
    print("2. Navigate to Azure Active Directory > App registrations")
    print("3. Click 'New registration'")
    print("4. Enter app name (e.g., 'Email PDF Processor')")
    print("5. Select 'Accounts in any organizational directory and personal Microsoft accounts'")
    print("6. Add redirect URI: http://localhost:8080/callback (Web platform)")
    print("7. After creation, copy the 'Application (client) ID'")
    print("8. Go to 'API permissions' > 'Add a permission' > 'Microsoft Graph'")
    print("9. Add these permissions: Mail.Read, Mail.ReadBasic, User.Read")
    print("10. Grant admin consent if required")
    
    client_id = input("\nEnter Outlook Client ID: ").strip()
    if not client_id:
        client_id = "86fd58c9-45de-44cb-9fca-615de1513036"
        print(f"Using default Client ID: {client_id}")
    
    tenant_id = input("Enter Tenant ID (default: common): ").strip()
    if not tenant_id:
        tenant_id = "common"
    
    success = client.add_outlook_provider("Outlook", client_id, tenant_id)
    if success:
        print("✅ Outlook provider added successfully!")
        print("📧 You can now process Outlook emails")
    else:
        print("❌ Failed to add Outlook provider")

def test_all_providers(client):
    """Test authentication for all providers"""
    print("\n🔐 Testing Provider Authentication")
    print("=" * 35)
    
    auth_results = client.authenticate_all()
    
    for provider, success in auth_results.items():
        if success:
            print(f"✅ {provider.upper()}: Authentication successful")
        else:
            print(f"❌ {provider.upper()}: Authentication failed")
    
    if any(auth_results.values()):
        print("\n✅ At least one provider is working!")
    else:
        print("\n❌ No providers are working. Please check your setup.")

def process_all_providers():
    """Process emails from all enabled providers"""
    print("\n📥 Processing emails from all providers...")
    
    try:
        client = UnifiedEmailClient()
        
        # Authenticate all providers
        print("🔐 Authenticating providers...")
        auth_results = client.authenticate_all()
        
        working_providers = [p for p, success in auth_results.items() if success]
        
        if not working_providers:
            print("❌ No providers authenticated successfully!")
            return
        
        print(f"✅ Authenticated: {', '.join(working_providers)}")
        
        # Process emails
        print("📧 Processing emails...")
        process_results = client.process_all_emails()
        
        print("\n📊 Processing Results:")
        for provider, count in process_results.items():
            print(f"  {provider.upper()}: {count} emails processed")
        
        total_processed = sum(process_results.values())
        print(f"\n✅ Total: {total_processed} emails processed")
        
    except Exception as e:
        print(f"❌ Error processing emails: {e}")

def process_gmail_only():
    """Process Gmail emails only"""
    print("\n📥 Processing Gmail emails only...")
    
    try:
        client = EnhancedGmailClient()
        client.process_new_statements()
        print("✅ Gmail processing completed!")
    except Exception as e:
        print(f"❌ Error processing Gmail: {e}")

def process_outlook_only():
    """Process Outlook emails only"""
    print("\n📥 Processing Outlook emails only...")
    
    try:
        # Get Outlook configuration
        unified_client = UnifiedEmailClient()
        providers = unified_client.list_providers()
        
        outlook_provider = None
        for provider in providers:
            if provider['type'] == 'outlook' and provider['enabled']:
                outlook_provider = provider
                break
        
        if not outlook_provider:
            print("❌ No Outlook provider configured!")
            print("Please setup Outlook provider first (Option 2 in main menu)")
            return
        
        # Load Outlook config
        conn = sqlite3.connect('email_data.db')
        c = conn.cursor()
        c.execute('SELECT config FROM email_providers WHERE type = "outlook"')
        config_row = c.fetchone()
        conn.close()
        
        if not config_row:
            print("❌ Outlook configuration not found!")
            return
        
        config_data = json.loads(config_row[0])
        outlook_config = OutlookConfig(**config_data)
        
        # Create Outlook client
        outlook_client = OutlookClient(outlook_config)
        
        # Authenticate
        if outlook_client.authenticate():
            print("✅ Outlook authentication successful")
            
            # Process emails
            processed_count = outlook_client.process_new_emails()
            print(f"✅ Processed {processed_count} Outlook emails")
        else:
            print("❌ Outlook authentication failed")
            
    except Exception as e:
        print(f"❌ Error processing Outlook: {e}")

def display_unified_email_stats():
    """Display statistics for unified email system"""
    print("\n📊 Unified Email Statistics")
    print("=" * 30)
    
    try:
        client = UnifiedEmailClient()
        stats = client.get_statistics()
        
        print(f"Total emails processed: {stats['total_emails']}")
        print(f"Emails with attachments: {stats['emails_with_attachments']}")
        print(f"Successfully unlocked PDFs: {stats['unlocked_pdfs']}")
        print(f"Total unlock attempts: {stats['total_unlock_attempts']}")
        print(f"Unlock success rate: {stats['unlock_success_rate']:.1f}%")
        
        print("\n📧 By Provider:")
        for provider, count in stats['provider_counts'].items():
            print(f"  {provider.upper()}: {count} emails")
        
        # Also show traditional Gmail stats
        print("\n📊 Gmail-specific Statistics:")
        display_email_stats()
        
    except Exception as e:
        print(f"❌ Error getting statistics: {e}")

def unlock_all_pdfs_unified():
    """Unlock all PDFs using unified system"""
    print("\n🔓 Unlocking all PDFs (Unified System)...")
    
    try:
        client = UnifiedEmailClient()
        
        # Check if Gmail client is available for enhanced unlocking
        if not client.gmail_client:
            print("⚠️ Gmail client not available. Initializing...")
            if os.path.exists('./secret/credentials.json'):
                client.add_gmail_provider("Gmail", "credentials.json")
            else:
                print("❌ Gmail credentials required for advanced PDF unlocking")
                return
        
        client.unlock_all_pdfs()
        print("✅ PDF unlocking completed!")
        
    except Exception as e:
        print(f"❌ Error unlocking PDFs: {e}")

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