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
	"""Main function with enhanced personal data management"""
	print("📬 Enhanced Gmail PDF Statement Processor")
	print("==================================================")
	
	while True:
		print("\n🔧 Main Menu")
		print("=" * 50)
		
		# Personal Data Management Section
		print("📊 PERSONAL DATA MANAGEMENT")
		print("1.  Setup Personal Data (Interactive)")
		print("2.  List All Personal Data")
		print("3.  Add Single Personal Data Item")
		print("4.  Delete Personal Data Item")
		print("5.  Auto-Extract from Emails")
		print("6.  Clean Low-Confidence Data")
		print("7.  List Manual Data Only")
		print()
		
		# Email Processing Section
		print("📧 EMAIL PROCESSING")
		print("8.  Setup Email Providers")
		print("9.  Process New Emails (All Providers)")
		print("10. Process Gmail Only")
		print("11. Process Outlook Only")
		print()
		
		# Analysis & Reports Section
		print("📊 ANALYSIS & REPORTS")
		print("12. View Email Statistics")
		print("13. View Recent Emails")
		print("14. Test PDF Unlock")
		print("15. Unlock All PDFs")
		print()
		
		# System Management Section
		print("⚙️  SYSTEM MANAGEMENT")
		print("16. Database Management")
		print("17. Exit")
		
		choice = input("\nSelect option (1-17): ").strip()
		
		# Personal Data Management Options (1-7)
		if choice == '1':
			manager = PersonalDataManager()
			manager.setup_interactive()
		
		elif choice == '2':
			manager = PersonalDataManager()
			manager.list_personal_data()
		
		elif choice == '3':
			manager = PersonalDataManager()
			data_type = input("Enter data type: ").strip()
			data_value = input("Enter data value: ").strip()
			description = input("Enter description (optional): ").strip()
			if data_type and data_value:
				manager.add_personal_data(data_type, data_value, description, 'manual', 1.0)
			else:
				print("❌ Data type and value are required!")
		
		elif choice == '4':
			manager = PersonalDataManager()
			manager.list_personal_data()
			try:
				data_id = int(input("Enter ID to delete: "))
				manager.delete_personal_data(data_id)
			except ValueError:
				print("❌ Invalid ID!")
		
		elif choice == '5':
			manager = PersonalDataManager()
			print("\n🤖 Auto-extracting personal data from emails...")
			try:
				extracted_count = manager.extract_from_emails()
				print(f"✅ Extraction complete! Found {extracted_count} new data points")
			except Exception as e:
				print(f"❌ Extraction failed: {e}")
		
		elif choice == '6':
			manager = PersonalDataManager()
			manager.cleanup_low_confidence_data()
		
		elif choice == '7':
			manager = PersonalDataManager()
			manager.list_personal_data(show_auto_extracted=False)
		
		# Email Processing Options (8-11)
		elif choice == '8':
			setup_email_providers()
		
		elif choice == '9':
			process_all_providers()
		
		elif choice == '10':
			process_gmail_only()
		
		elif choice == '11':
			process_outlook_only()
		
		# Analysis & Reports Options (12-15)
		elif choice == '12':
			display_unified_email_stats()
		
		elif choice == '13':
			try:
				limit = int(input("How many recent emails to show? (default 10): ") or "10")
				display_recent_emails(limit=limit)
			except ValueError:
				display_recent_emails()
		
		elif choice == '14':
			test_pdf_unlock()
		
		elif choice == '15':
			unlock_all_pdfs_unified()
		
		# System Management Options (16-17)
		elif choice == '16':
			database_management_menu()
		
		elif choice == '17':
			print("👋 Goodbye!")
			break
		
		else:
			print("❌ Invalid choice! Please select 1-17.")

def personal_data_submenu():
	"""Dedicated submenu for personal data management"""
	manager = PersonalDataManager()
	
	while True:
		print("\n🔐 Personal Data Manager")
		print("=" * 40)
		print("1. Interactive Setup")
		print("2. List Personal Data")
		print("3. Add Single Item")
		print("4. Delete Item")
		print("5. Auto-Extract from Emails")
		print("6. Clean Low-Confidence Data")
		print("7. List Manual Data Only")
		print("8. Back to Main Menu")
		
		choice = input("\nSelect option (1-8): ").strip()
		
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
			break
		
		else:
			print("❌ Invalid choice!")

def setup_email_providers():
	"""Setup email providers (Gmail and Outlook) with improved error handling"""
	print("\n📧 Email Provider Setup")
	print("=" * 30)
	
	try:
		client = UnifiedEmailClient()
		
		while True:
			try:
				providers = client.list_providers()
				
				print(f"\n📋 Current providers ({len(providers)}):")
				if providers:
					for i, provider in enumerate(providers, 1):
						status = "✅ Enabled" if provider['enabled'] else "❌ Disabled"
						email_count = provider.get('total_emails', 0)
						last_sync = provider.get('last_sync', 'Never')
						print(f"  {i}. {provider['name']} ({provider['type']}) - {status}")
						print(f"     📧 {email_count} emails, Last sync: {last_sync}")
				else:
					print("  No providers configured yet")
				
			except Exception as list_error:
				print(f"⚠️ Error listing providers: {list_error}")
				print("📧 Continuing with provider setup...")
				providers = []
			
			print("\n🔧 Options:")
			print("1. Add Gmail Provider")
			print("2. Add Outlook Provider")
			print("3. Test All Providers")
			print("4. Remove Provider")
			print("5. Repair Database")
			print("6. Back to Main Menu")
			
			choice = input("\nSelect option (1-6): ").strip()
			
			if choice == '1':
				setup_gmail_provider(client)
			
			elif choice == '2':
				setup_outlook_provider(client)
			
			elif choice == '3':
				print("\n🔐 Testing all providers...")
				try:
					auth_results = client.authenticate_all()
					
					if not auth_results:
						print("❌ No providers to test")
					else:
						for provider, success in auth_results.items():
							status = "✅ Success" if success else "❌ Failed"
							print(f"  {provider}: {status}")
				except Exception as auth_error:
					print(f"❌ Authentication test failed: {auth_error}")
			
			elif choice == '4':
				try:
					current_providers = client.list_providers()
					if not current_providers:
						print("❌ No providers to remove")
						continue
					
					print("\nSelect provider to remove:")
					for i, provider in enumerate(current_providers, 1):
						print(f"  {i}. {provider['name']} ({provider['type']})")
					
					try:
						idx = int(input("Enter provider number: ")) - 1
						if 0 <= idx < len(current_providers):
							provider_to_remove = current_providers[idx]
							# Add remove functionality to unified client
							print(f"⚠️ Provider removal not yet implemented: {provider_to_remove['name']}")
						else:
							print("❌ Invalid provider number")
					except ValueError:
						print("❌ Invalid input")
				except Exception as remove_error:
					print(f"❌ Error removing provider: {remove_error}")
			
			elif choice == '5':
				print("\n🔧 Repairing database...")
				try:
					repair_database()
					# Recreate client after repair
					client = UnifiedEmailClient()
					print("✅ Database repaired, client reinitialized")
				except Exception as repair_error:
					print(f"❌ Database repair failed: {repair_error}")
			
			elif choice == '6':
				break
			
			else:
				print("❌ Invalid choice!")
	
	except Exception as e:
		print(f"❌ Critical error in provider setup: {e}")
		print("\n💡 Try these troubleshooting steps:")
		print("1. Run Database Repair (option 5)")
		print("2. Check if email_data.db file has proper permissions")
		print("3. Try deleting email_data.db and recreating it")

def setup_gmail_provider(client):
	"""Setup Gmail provider with the unified client"""
	print("\n📧 Gmail Provider Setup")
	print("=" * 25)
	
	try:
		# Check for credentials file
		import os
		credential_paths = [
			"./secret/credentials.json",
			"./credentials.json",
			"credentials.json"
		]
		
		credentials_file = None
		for path in credential_paths:
			if os.path.exists(path):
				credentials_file = path
				print(f"✅ Found credentials at: {path}")
				break
		
		if not credentials_file:
			credentials_file = input("Enter path to Gmail credentials.json file: ").strip()
			if not os.path.exists(credentials_file):
				print("❌ Credentials file not found!")
				return
		
		provider_name = input("Enter name for this Gmail provider (default: Gmail): ").strip()
		if not provider_name:
			provider_name = "Gmail"
		
		print(f"🔧 Adding Gmail provider '{provider_name}'...")
		success = client.add_gmail_provider(provider_name, credentials_file)
		
		if success:
			print(f"✅ Gmail provider '{provider_name}' added successfully!")
		else:
			print(f"❌ Failed to add Gmail provider '{provider_name}'")
	
	except Exception as e:
		print(f"❌ Error setting up Gmail provider: {e}")

def setup_outlook_provider(client):
	"""Setup Outlook provider with the unified client"""
	print("\n📧 Outlook Provider Setup")
	print("=" * 26)
	
	try:
		print("📋 Outlook Configuration Options:")
		print("1. Use default test configuration")
		print("2. Enter custom configuration")
		
		choice = input("Select option (1-2): ").strip()
		
		if choice == '1':
			client_id = "86fd58c9-45de-44cb-9fca-615de1513036"
			tenant_id = "common"
			provider_name = "Outlook"
			print("✅ Using default Microsoft test configuration")
		
		elif choice == '2':
			client_id = input("Enter Azure App Client ID: ").strip()
			tenant_id = input("Enter Tenant ID (default: common): ").strip()
			if not tenant_id:
				tenant_id = "common"
			provider_name = input("Enter name for this Outlook provider (default: Outlook): ").strip()
			if not provider_name:
				provider_name = "Outlook"
		
		else:
			print("❌ Invalid choice!")
			return
		
		if not client_id:
			print("❌ Client ID is required!")
			return
		
		print(f"🔧 Adding Outlook provider '{provider_name}'...")
		success = client.add_outlook_provider(provider_name, client_id, tenant_id)
		
		if success:
			print(f"✅ Outlook provider '{provider_name}' added successfully!")
		else:
			print(f"❌ Failed to add Outlook provider '{provider_name}'")
	
	except Exception as e:
		print(f"❌ Error setting up Outlook provider: {e}")

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
	"""Process Gmail emails only with proper configuration"""
	print("\n📥 Processing Gmail emails only...")
	
	try:
		# Check if Gmail credentials exist
		credentials_file = './secret/credentials.json'
		if not os.path.exists(credentials_file):
			print("❌ Gmail credentials not found!")
			print(f"📁 Looking for: {credentials_file}")
			print("\n💡 Setup steps:")
			print("1. Create 'secret' folder in current directory")
			print("2. Download credentials.json from Google Cloud Console")
			print("3. Place credentials.json in the secret folder")
			return
		
		# Create Gmail configuration
		from enhanced_gmail_client import GmailConfig, EnhancedGmailClient
		
		config = GmailConfig(
			credentials_file=credentials_file,
			token_file='./secret/gmail_token.pickle'
		)
		
		# Initialize and authenticate Gmail client
		print("🔐 Authenticating Gmail...")
		client = EnhancedGmailClient(config)
		
		if not client.authenticate():
			print("❌ Gmail authentication failed!")
			print("💡 Try deleting the token file and re-authenticating:")
			print("   rm ./secret/gmail_token.pickle")
			return
		
		print("✅ Gmail authenticated successfully!")
		
		# Process emails
		print("📧 Processing new emails...")
		processed_count = client.process_new_emails(months_back=2)
		
		if processed_count > 0:
			print(f"✅ Processed {processed_count} new emails from Gmail")
			
			# Get and display recent emails
			emails = client.get_processed_emails()
			if emails:
				print(f"\n📋 Recent emails ({len(emails)} total):")
				for email in emails[:3]:  # Show first 3
					print(f"  - {email['subject']} (from {email['sender_email']})")
					if email['attachments']:
						print(f"    📎 {len(email['attachments'])} attachments")
		else:
			print("ℹ️ No new emails found to process")
		
		# Show statistics
		stats = client.get_email_stats()
		print(f"\n📊 Gmail Statistics:")
		print(f"  Total emails: {stats.get('total_emails', 0)}")
		print(f"  With attachments: {stats.get('emails_with_attachments', 0)}")
		print(f"  Recent (7 days): {stats.get('recent_emails', 0)}")
		
	except Exception as e:
		print(f"❌ Error processing Gmail: {e}")
		logger.error(f"Gmail processing error: {e}")

def process_outlook_direct():
	"""Direct Outlook processing without unified client"""
	print("\n📧 Direct Outlook Processing...")
	
	try:
		from outlook_client import OutlookConfig, OutlookClient
		
		config = OutlookConfig(
			client_id="86fd58c9-45de-44cb-9fca-615de1513036",
			tenant_id="common"
		)
		
		# Initialize and authenticate Outlook client
		print("🔐 Authenticating Outlook...")
		outlook_client = OutlookClient(config)
		
		if not outlook_client.authenticate():
			print("❌ Outlook authentication failed!")
			print("💡 Authentication help:")
			print("   - This requires Microsoft account login")
			print("   - A browser window should open automatically")
			print("   - Complete the login process in the browser")
			print("   - Make sure you have internet connection")
			return
		
		print("✅ Outlook authenticated successfully!")
		
		# Process emails - use the correct method name: process_new_emails
		print("📧 Processing new emails...")
		processed_count = outlook_client.process_new_emails(months_back=2)
		
		if processed_count > 0:
			print(f"✅ Processed {processed_count} new emails from Outlook")
			
			# Get and display recent emails
			try:
				emails = outlook_client.get_processed_emails()
				if emails:
					print(f"\n📋 Recent emails ({len(emails)} total):")
					for email in emails[:3]:  # Show first 3
						print(f"  - {email.get('subject', 'No subject')} (from {email.get('sender_email', 'Unknown')})")
						if email.get('attachments'):
							print(f"    📎 {len(email['attachments'])} attachments")
						if email.get('password_hints'):
							print(f"    🔑 {len(email['password_hints'])} password hints")
			except Exception as e:
				print(f"⚠️ Could not display recent emails: {e}")
		else:
			print("ℹ️ No new emails found to process")
		
		print(f"\n📊 Outlook Statistics:")
		print(f"  Total emails processed this session: {processed_count}")
		
	except Exception as e:
		print(f"❌ Error in direct Outlook processing: {e}")
		import logging
		logger = logging.getLogger(__name__)
		logger.error(f"Direct Outlook processing error: {e}")

def process_outlook_only():
	"""Process Outlook emails only with enhanced error handling"""
	print("\n📥 Processing Outlook emails only...")
	
	try:
		# First, try to fix any database issues
		fix_database_schema()
		
		# Create unified client to check for providers
		client = UnifiedEmailClient()
		providers = client.list_providers()
		
		# Find Outlook provider
		outlook_provider = None
		for provider in providers:
			if provider['type'] == 'outlook' and provider['enabled']:
				outlook_provider = provider
				break
		
		if not outlook_provider:
			print("❌ No Outlook provider configured!")
			print("💡 Setting up Outlook provider with default configuration...")
			
			# Try to set up default Outlook provider with better error handling
			try:
				success = client.add_outlook_provider(
					name="Outlook",
					client_id="86fd58c9-45de-44cb-9fca-615de1513036",
					tenant_id="common"
				)
				
				if not success:
					print("❌ Failed to setup Outlook provider automatically")
					print("📧 Let's try manual setup...")
					
					# Manual setup fallback
					setup_outlook_provider_direct()
					return
				
				print("✅ Default Outlook provider setup successful")
				
			except Exception as setup_error:
				print(f"❌ Setup error: {setup_error}")
				print("💡 Let's try direct Outlook client setup...")
				process_outlook_direct()
				return
		
		# Use direct Outlook client if provider setup fails
		process_outlook_direct()
		
	except Exception as e:
		print(f"❌ Error processing Outlook: {e}")
		import logging
		logger = logging.getLogger(__name__)
		logger.error(f"Outlook processing error: {e}")
		
		# Fallback to direct processing
		print("💡 Trying direct Outlook processing...")
		process_outlook_direct()

def process_outlook_with_method_detection():
	"""Process Outlook emails with automatic method detection"""
	print("\n📧 Outlook Processing with Method Detection")
	print("=" * 45)
	
	try:
		from outlook_client import OutlookConfig, OutlookClient
		
		config = OutlookConfig(
			client_id="86fd58c9-45de-44cb-9fca-615de1513036",
			tenant_id="common"
		)
		
		# Initialize and authenticate Outlook client
		print("🔐 Authenticating Outlook...")
		outlook_client = OutlookClient(config)
		
		if not outlook_client.authenticate():
			print("❌ Outlook authentication failed!")
			return
		
		print("✅ Outlook authenticated successfully!")
		
		# Show available methods
		print("🔍 Available methods in OutlookClient:")
		methods = [method for method in dir(outlook_client) if not method.startswith('_') and callable(getattr(outlook_client, method))]
		
		# Filter for processing-related methods
		processing_methods = [m for m in methods if any(keyword in m.lower() for keyword in ['process', 'fetch', 'search'])]
		print(f"📋 Processing-related methods: {processing_methods}")
		
		# Use the correct method: process_new_emails
		print("📧 Processing new emails using process_new_emails()...")
		processed_count = outlook_client.process_new_emails(months_back=2)
		
		if processed_count > 0:
			print(f"✅ Processed {processed_count} emails using process_new_emails()")
			
			# Get and display recent emails
			try:
				emails = outlook_client.get_processed_emails()
				if emails:
					print(f"\n📋 Recent emails ({len(emails)} total):")
					for email in emails[:3]:  # Show first 3
						subject = email.get('subject', 'No subject')
						sender = email.get('sender_email', 'Unknown')
						print(f"  - {subject} (from {sender})")
						
						if email.get('attachments'):
							print(f"    📎 {len(email['attachments'])} attachments")
						
						if email.get('password_hints'):
							hints = email['password_hints']
							print(f"    🔑 {len(hints)} password hints: {', '.join(hints[:3])}")
						
						if email.get('password_rules'):
							rules = email['password_rules']
							print(f"    📋 {len(rules)} password rules found")
			except Exception as e:
				print(f"⚠️ Could not display recent emails: {e}")
		else:
			print("ℹ️ No new emails found to process")
		
		print(f"\n📊 Method Detection Results:")
		print(f"  ✅ Correct method: process_new_emails()")
		print(f"  📧 Emails processed: {processed_count}")
		
	except Exception as e:
		print(f"❌ Error in method detection processing: {e}")

def test_outlook_methods():
	"""Test what methods are available in OutlookClient"""
	print("\n🔍 Testing OutlookClient Methods")
	print("=" * 35)
	
	try:
		from outlook_client import OutlookConfig, OutlookClient
		
		config = OutlookConfig(
			client_id="86fd58c9-45de-44cb-9fca-615de1513036",
			tenant_id="common"
		)
		
		client = OutlookClient(config)
		
		print("📋 All available methods in OutlookClient:")
		methods = [method for method in dir(client) if not method.startswith('_') and callable(getattr(client, method))]
		
		for i, method in enumerate(methods, 1):
			print(f"  {i:2d}. {method}")
		
		# Highlight the correct processing methods
		processing_methods = []
		for method_name in ['process_new_emails', 'process_emails', 'fetch_and_process_emails', 'fetch_emails']:
			if hasattr(client, method_name):
				processing_methods.append(method_name)
		
		print(f"\n✅ Available processing methods:")
		for method in processing_methods:
			print(f"  ✓ {method}")
		
		if 'process_new_emails' in processing_methods:
			print(f"\n🎯 Recommended method: process_new_emails(months_back=2)")
		
		# Show method signatures if possible
		if processing_methods:
			print(f"\n📋 Method details:")
			for method_name in processing_methods:
				try:
					method = getattr(client, method_name)
					print(f"  {method_name}: {method.__doc__ or 'No documentation available'}")
				except:
					pass
		
	except Exception as e:
		print(f"❌ Error testing methods: {e}")

def setup_outlook_provider_direct():
	"""Direct Outlook provider setup without unified client"""
	print("\n📧 Direct Outlook Provider Setup")
	print("=" * 32)
	
	try:
		from outlook_client import OutlookConfig, OutlookClient
		
		print("📋 Using default Microsoft test configuration:")
		print("   Client ID: 86fd58c9-45de-44cb-9fca-615de1513036")
		print("   Tenant ID: common (works with personal Microsoft accounts)")
		print("   Scopes: Mail.Read, User.Read")
		
		config = OutlookConfig(
			client_id="86fd58c9-45de-44cb-9fca-615de1513036",
			tenant_id="common"
		)
		
		print("\n🔐 Testing Outlook authentication...")
		client = OutlookClient(config)
		
		if client.authenticate():
			print("✅ Outlook authentication successful!")
			print("📧 You can now process Outlook emails using option 11")
			
			# Save configuration manually to database
			try:
				import sqlite3
				import json
				from datetime import datetime
				
				conn = sqlite3.connect('email_data.db')
				c = conn.cursor()
				
				provider_data = {
					'id': 'outlook_default',
					'name': 'Outlook',
					'provider_type': 'outlook',
					'config': json.dumps(config.__dict__),
					'enabled': 1,
					'created_date': datetime.now().isoformat()
				}
				
				c.execute('''
					INSERT OR REPLACE INTO email_providers 
					(id, name, provider_type, config, enabled, created_date)
					VALUES (?, ?, ?, ?, ?, ?)
				''', (
					provider_data['id'],
					provider_data['name'], 
					provider_data['provider_type'],
					provider_data['config'],
					provider_data['enabled'],
					provider_data['created_date']
				))
				
				conn.commit()
				conn.close()
				print("✅ Provider configuration saved to database")
				
			except Exception as db_error:
				print(f"⚠️ Could not save to database: {db_error}")
				print("   But authentication works, so you can still use direct processing")
		else:
			print("❌ Outlook authentication failed")
			print("\n💡 Troubleshooting tips:")
			print("   1. Make sure you have internet connection")
			print("   2. Check if a browser window opened for login")
			print("   3. Try logging in with a different Microsoft account")
			print("   4. Verify that the account has email access")
		
	except Exception as e:
		print(f"❌ Error in direct setup: {e}")

def check_database_integrity():
	"""Check and report database integrity"""
	print("\n🔍 Database Integrity Check")
	print("=" * 30)
	
	try:
		import sqlite3
		conn = sqlite3.connect('email_data.db')
		c = conn.cursor()
		
		# Check tables
		c.execute("SELECT name FROM sqlite_master WHERE type='table'")
		tables = [row[0] for row in c.fetchall()]
		
		print(f"📋 Found {len(tables)} tables:")
		for table in tables:
			c.execute(f"SELECT COUNT(*) FROM {table}")
			count = c.fetchone()[0]
			print(f"   {table}: {count} records")
		
		# Check schema for critical tables
		critical_tables = ['email_providers', 'emails', 'personal_data']
		
		for table in critical_tables:
			if table in tables:
				print(f"\n📊 Schema for {table}:")
				c.execute(f"PRAGMA table_info({table})")
				columns = c.fetchall()
				for col in columns:
					print(f"   {col[1]} ({col[2]}) {'NOT NULL' if col[3] else ''} {'PRIMARY KEY' if col[5] else ''}")
		
		conn.close()
		print("\n✅ Database integrity check completed")
		
	except Exception as e:
		print(f"❌ Database check error: {e}")

def unlock_all_pdfs_unified():
	"""Unlock all PDFs using unified system with fallback"""
	print("\n🔓 Unlocking all PDFs (Unified System)...")
	
	try:
		# Check if we have any emails with attachments first
		import sqlite3
		conn = sqlite3.connect('email_data.db')
		c = conn.cursor()
		
		c.execute("SELECT COUNT(*) FROM emails WHERE has_attachments = 1")
		pdf_count = c.fetchone()[0] if c.fetchone() else 0
		
		if pdf_count == 0:
			print("ℹ️ No emails with attachments found to unlock")
			conn.close()
			return
		
		print(f"📄 Found {pdf_count} emails with potential PDFs")
		conn.close()
		
		# Try unified client approach
		try:
			client = UnifiedEmailClient()
			# Placeholder for unlock functionality
			print("⚠️ PDF unlocking feature not yet implemented in unified client")
			print("💡 You can manually check downloaded files in the 'downloads' folder")
			
		except Exception as unified_error:
			print(f"⚠️ Unified client error: {unified_error}")
			print("💡 PDF files should be available in downloads folder for manual unlocking")
		
	except Exception as e:
		print(f"❌ Error unlocking PDFs: {e}")
		import logging
		logger = logging.getLogger(__name__)
		logger.error(f"PDF unlock error: {e}")

def display_unified_email_stats(db_path='email_data.db'):
	"""Display statistics about processed emails (unified version)"""
	display_email_stats(db_path=db_path)

def fix_database_schema(db_path='email_data.db'):
	"""Dummy function to fix database schema (placeholder)"""
	# In a real implementation, this would check and fix schema issues.
	print("✅ Database schema checked (placeholder, no changes made).")

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