#!/usr/bin/env python3
"""
Test script to display email statistics
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from unified_email_client import UnifiedEmailClient
from enhanced_gmail_client import EnhancedGmailClient
import sqlite3

def display_email_stats(db_path='email_data.db'):
    """Display statistics about processed emails"""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Check if tables exist
    c.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = c.fetchall()
    print("📊 Available tables:", [table[0] for table in tables])
    
    # Get total emails from original table
    try:
        c.execute('SELECT COUNT(*) FROM emails')
        total_emails = c.fetchone()[0]
        print(f"Total emails (original table): {total_emails}")
    except:
        print("Original emails table not found")
    
    # Get total emails from unified table
    try:
        c.execute('SELECT COUNT(*) FROM unified_emails')
        total_unified = c.fetchone()[0]
        print(f"Total emails (unified table): {total_unified}")
    except:
        print("Unified emails table not found")
    
    # Get emails with attachments
    try:
        c.execute('SELECT COUNT(*) FROM emails WHERE attachments IS NOT NULL AND attachments != "[]"')
        emails_with_attachments = c.fetchone()[0]
        print(f"Emails with attachments: {emails_with_attachments}")
    except:
        print("Could not get attachment stats")
    
    conn.close()

def test_gmail_client():
    """Test Gmail client initialization"""
    print("\n🧪 Testing Gmail Client...")
    
    try:
        client = EnhancedGmailClient()
        print("✅ Gmail client initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Gmail client initialization failed: {e}")
        return False

def test_unified_client():
    """Test unified client"""
    print("\n🧪 Testing Unified Client...")
    
    try:
        client = UnifiedEmailClient()
        stats = client.get_statistics()
        print("✅ Unified client initialized successfully")
        print(f"📊 Statistics: {stats}")
        return True
    except Exception as e:
        print(f"❌ Unified client failed: {e}")
        return False

if __name__ == "__main__":
    print("📊 Email Statistics Display")
    print("=" * 50)
    
    display_email_stats()
    
    gmail_works = test_gmail_client()
    unified_works = test_unified_client()
    
    if gmail_works:
        print("\n✅ Gmail client is working - the process_new_statements fix should work!")
    else:
        print("\n❌ Gmail client has issues")
