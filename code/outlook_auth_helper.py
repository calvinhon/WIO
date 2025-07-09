#!/usr/bin/env python3
"""
Outlook Authentication Helper
This script helps you authenticate with Outlook using the improved flow
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from outlook_client import OutlookClient, OutlookConfig

def main():
    """Main authentication helper"""
    print("🔐 Outlook Authentication Helper")
    print("=" * 40)
    
    # Configuration
    config = OutlookConfig(
        client_id="86fd58c9-45de-44cb-9fca-615de1513036",
        tenant_id="common",
    )
    
    # Initialize client
    client = OutlookClient(config)
    
    print("🚀 Starting authentication process...")
    print("📌 RECOMMENDATION: Use device flow authentication (option 1) - it's much easier!")
    print("📌 Device flow: You get a simple code to enter on a Microsoft page")
    print("📌 Browser flow: You need to copy a complex URL with code parameter")
    print()
    
    try:
        # Authenticate
        if client.authenticate():
            print("\n✅ Authentication successful!")
            print("🎉 You can now use the Outlook client to process emails")
            
            # Quick test
            print("\n🧪 Testing basic functionality...")
            folders = client.get_folders()
            print(f"📁 Found {len(folders)} folders")
            
            return True
            
        else:
            print("\n❌ Authentication failed")
            print("💡 Tips for troubleshooting:")
            print("   - Try device flow authentication (option 1)")
            print("   - Make sure you have internet connection")
            print("   - Check if your Microsoft account is accessible")
            return False
            
    except Exception as e:
        print(f"\n❌ Authentication error: {e}")
        print("💡 Try running the script again and select device flow authentication")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎊 Great! Authentication is working.")
        print("🔄 You can now run the main email processing script.")
    else:
        print("\n🔄 Please try again or check the troubleshooting tips above.")
