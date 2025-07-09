#!/usr/bin/env python3
"""
Test script to verify imports work correctly
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test each import individually"""
    print("Testing imports...")
    
    try:
        import json
        print("✅ json import successful")
    except Exception as e:
        print(f"❌ json import failed: {e}")
    
    try:
        import sqlite3
        print("✅ sqlite3 import successful")
    except Exception as e:
        print(f"❌ sqlite3 import failed: {e}")
    
    try:
        from datetime import datetime
        print("✅ datetime import successful")
    except Exception as e:
        print(f"❌ datetime import failed: {e}")
    
    try:
        from enhanced_gmail_client import EnhancedGmailClient
        print("✅ EnhancedGmailClient import successful")
    except Exception as e:
        print(f"❌ EnhancedGmailClient import failed: {e}")
    
    try:
        from personal_data_manager import PersonalDataManager
        print("✅ PersonalDataManager import successful")
    except Exception as e:
        print(f"❌ PersonalDataManager import failed: {e}")
    
    try:
        from unified_email_client import UnifiedEmailClient
        print("✅ UnifiedEmailClient import successful")
    except Exception as e:
        print(f"❌ UnifiedEmailClient import failed: {e}")
    
    try:
        from outlook_client import OutlookClient, OutlookConfig
        print("✅ OutlookClient import successful")
    except Exception as e:
        print(f"❌ OutlookClient import failed: {e}")

if __name__ == "__main__":
    test_imports()
