#!/usr/bin/env python3
"""
Test Outlook Authentication
This script tests the improved Outlook authentication flow
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from outlook_client import OutlookClient, OutlookConfig

def test_outlook_authentication():
    """Test Outlook authentication with improved flow"""
    print("🧪 Testing Outlook Authentication")
    print("=" * 40)
    
    # Configuration
    config = OutlookConfig(
        client_id="86fd58c9-45de-44cb-9fca-615de1513036",
        tenant_id="common",
    )
    
    # Initialize client
    client = OutlookClient(config)
    
    try:
        # Authenticate
        if client.authenticate():
            print("✅ Authentication successful!")
            
            # Test basic functionality
            print("\n📁 Testing folder access...")
            folders = client.get_folders()
            print(f"✅ Found {len(folders)} folders")
            
            if folders:
                for folder in folders[:5]:  # Show first 5 folders
                    print(f"  📂 {folder['displayName']} ({folder['totalItemCount']} items)")
            
            print("\n📧 Testing email search...")
            emails = client.search_bank_emails(months_back=1)
            print(f"✅ Found {len(emails)} potential statement emails")
            
            if emails:
                print("📊 Recent emails:")
                for email in emails[:3]:  # Show first 3 emails
                    print(f"  📧 {email['subject'][:50]}...")
            
            return True
            
        else:
            print("❌ Authentication failed")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_outlook_authentication()
