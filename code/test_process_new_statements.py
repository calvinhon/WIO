#!/usr/bin/env python3
"""
Test script to verify the process_new_statements method works
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_gmail_client import EnhancedGmailClient

def test_process_new_statements():
    """Test the process_new_statements method"""
    print("🧪 Testing process_new_statements method...")
    
    try:
        # Initialize the client
        client = EnhancedGmailClient()
        
        # Add some sample personal data
        client.add_personal_data('date_of_birth', '10031984', 'Date of birth in DDMMYYYY format')
        client.add_personal_data('mobile_number', '971525562885', 'Mobile number')
        client.add_personal_data('name', 'John', 'First name')
        client.add_personal_data('card_number', '1234567890123456', 'Credit card number')
        
        # Test the method
        result = client.process_new_statements()
        print(f"✅ process_new_statements completed successfully! Processed {result} emails.")
        
    except Exception as e:
        print(f"❌ Error testing process_new_statements: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_process_new_statements()
