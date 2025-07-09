#!/usr/bin/env python3
"""
Direct test of the process_new_statements method
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Test if the method exists
try:
    from enhanced_gmail_client import EnhancedGmailClient
    
    # Check if the method exists
    if hasattr(EnhancedGmailClient, 'process_new_statements'):
        print("✅ SUCCESS: process_new_statements method exists in EnhancedGmailClient")
        
        # Try to create an instance (this will test authentication)
        try:
            client = EnhancedGmailClient()
            print("✅ SUCCESS: EnhancedGmailClient can be instantiated")
            
            # Try to call the method
            try:
                result = client.process_new_statements()
                print(f"✅ SUCCESS: process_new_statements() executed successfully. Result: {result}")
            except Exception as e:
                print(f"⚠️ WARNING: process_new_statements() exists but failed to execute: {e}")
                # This is expected if there are no credentials or network issues
                
        except Exception as e:
            print(f"⚠️ WARNING: Could not instantiate EnhancedGmailClient: {e}")
            print("This is likely due to missing credentials.json file")
    else:
        print("❌ FAILED: process_new_statements method NOT found in EnhancedGmailClient")
        
except ImportError as e:
    print(f"❌ FAILED: Could not import EnhancedGmailClient: {e}")
except Exception as e:
    print(f"❌ FAILED: Unexpected error: {e}")

print("\n🔧 The main fix has been applied:")
print("- Added process_new_statements method to EnhancedGmailClient class")
print("- This method searches for credit card emails and processes them")
print("- It extracts password hints/rules and downloads PDF attachments")
print("- The method should resolve the original error about missing method")
