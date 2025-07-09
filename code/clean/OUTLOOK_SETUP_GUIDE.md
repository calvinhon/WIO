# Outlook Integration Setup Guide

## 📧 Adding Outlook Support to Your Email PDF Password Generator

Your system has been enhanced to support both Gmail and Outlook email providers. Here's how to set up Outlook integration:

## 🔧 Prerequisites

### 1. Install Additional Dependencies

```bash
cd d:\H\42AD\WIO\code
pip install msal requests microsoft-graph-core
```

### 2. Azure App Registration (Required for Outlook)

To use Outlook, you need to register your application with Microsoft Azure:

#### Step-by-Step Azure Setup:

1. **Go to Azure Portal**
   - Visit: https://portal.azure.com/
   - Sign in with your Microsoft account

2. **Navigate to App Registrations**
   - Search for "App registrations" in the search bar
   - Click on "App registrations"

3. **Create New Registration**
   - Click "New registration"
   - Enter application name: `Email PDF Password Generator`
   - Select account types: `Accounts in any organizational directory and personal Microsoft accounts`
   - Redirect URI: Select "Web" and enter: `http://localhost:8080/callback`
   - Click "Register"

4. **Get Client ID**
   - After registration, you'll see the "Application (client) ID"
   - **Copy this ID** - you'll need it for setup

5. **Configure API Permissions**
   - Go to "API permissions" in the left menu
   - Click "Add a permission"
   - Select "Microsoft Graph"
   - Choose "Delegated permissions"
   - Add these permissions:
     - `Mail.Read`
     - `Mail.ReadBasic`
     - `User.Read`
   - Click "Add permissions"
   - **Optional**: Click "Grant admin consent" if you're an admin

6. **Authentication Settings**
   - Go to "Authentication" in the left menu
   - Under "Platform configurations", ensure you have:
     - Redirect URI: `http://localhost:8080/callback`
   - Under "Advanced settings":
     - Check "Allow public client flows": Yes

## 🚀 How to Run with Outlook Support

### 1. Start the Program

```bash
cd d:\H\42AD\WIO\code
python main_email_fetch.py
```

### 2. Setup Email Providers

1. Choose option `2. Setup Email Providers`
2. Choose option `2. Add Outlook Provider`
3. Enter your **Client ID** from Azure App Registration
4. Enter **Tenant ID** (use `common` for personal accounts)
5. The system will save your configuration

### 3. Authenticate with Outlook

When you first try to process Outlook emails:

1. The system will open your browser
2. Sign in with your Microsoft account
3. Grant permissions to the application
4. Copy the redirect URL and paste it back in the terminal
5. Authentication token will be saved for future use

### 4. Process Emails

You can now:
- **Option 3**: Process emails from all providers (Gmail + Outlook)
- **Option 4**: Process Gmail only
- **Option 5**: Process Outlook only

## 📋 New Menu Options

Your updated program now includes:

```
📬 Enhanced Gmail PDF Statement Processor
==================================================

🔧 Main Menu
1. Setup Personal Data
2. Setup Email Providers          # NEW: Configure Gmail/Outlook
3. Process New Emails (All)       # NEW: Process both providers
4. Process Gmail Only             # NEW: Gmail-specific processing
5. Process Outlook Only           # NEW: Outlook-specific processing
6. View Email Statistics          # Enhanced with provider stats
7. View Recent Emails
8. Test PDF Unlock
9. Unlock All PDFs                # Enhanced with unified system
10. Database Management
11. Exit
```

## 🔍 Features of Outlook Integration

### Email Processing
- **Smart Filtering**: Searches for bank statement emails
- **Attachment Download**: Automatically downloads PDF attachments
- **Password Extraction**: Extracts password hints and rules from email body
- **Incremental Processing**: Only processes new emails

### Password Generation
- **Enhanced Integration**: Uses the same advanced password generation as Gmail
- **LLM Support**: Leverages local LLM for intelligent password generation
- **Rule-Based Fallback**: Uses pattern matching when LLM is unavailable

### Database Integration
- **Unified Storage**: All emails stored in unified database
- **Provider Tracking**: Track which provider each email came from
- **Statistics**: Comprehensive stats across all providers

## 🛠️ Troubleshooting

### Common Issues:

1. **Authentication Failed**
   - Check your Client ID is correct
   - Ensure redirect URI is exactly: `http://localhost:8080/callback`
   - Make sure you granted the required permissions

2. **No Emails Found**
   - Check that your Outlook account has bank statement emails
   - Verify the search filters are appropriate for your emails
   - Try adjusting the date range (currently set to 2 months back)

3. **Permission Errors**
   - Ensure you have the required API permissions in Azure
   - Try granting admin consent if you're an admin
   - Check if your organization has restrictions on app registrations

4. **Token Expired**
   - Delete `outlook_token_cache.json` file
   - Re-run the program to re-authenticate

### Debug Steps:

1. **Check Provider Status**
   ```bash
   python main_email_fetch.py
   # Choose option 2 (Setup Email Providers)
   # Choose option 3 (Test All Providers)
   ```

2. **View Logs**
   - The program includes detailed logging
   - Check console output for specific error messages

3. **Manual Testing**
   ```bash
   # Test Outlook client directly
   python outlook_client.py
   ```

## 📊 Database Schema

The system now includes these tables:

- `emails` - Gmail-specific emails
- `outlook_emails` - Outlook-specific emails  
- `unified_emails` - Combined view of all emails
- `email_providers` - Provider configurations
- `personal_data` - Your personal data for password generation
- `password_candidates` - Generated password candidates

## 🔒 Security Notes

- **Token Storage**: Authentication tokens are stored locally in `outlook_token_cache.json`
- **Credentials**: Never share your Client ID or authentication tokens
- **Permissions**: The app only requests read permissions for your mail
- **Local Processing**: All password generation and PDF unlocking happens locally

## 🎯 Success Workflow

1. **First Time Setup**:
   ```bash
   python main_email_fetch.py
   # Option 1: Setup Personal Data
   # Option 2: Setup Email Providers (add both Gmail and Outlook)
   # Option 3: Process New Emails (All Providers)
   # Option 9: Unlock All PDFs
   ```

2. **Regular Use**:
   ```bash
   python main_email_fetch.py
   # Option 3: Process New Emails (incremental)
   # Option 9: Unlock All PDFs
   ```

3. **Monitor Progress**:
   ```bash
   # Option 6: View Email Statistics
   # Shows stats for both Gmail and Outlook
   ```

## 📈 Performance Benefits

- **Unified Processing**: Process multiple email providers in one go
- **Intelligent Caching**: Avoid reprocessing same emails
- **Enhanced Password Generation**: Better success rates with LLM integration
- **Comprehensive Logging**: Track success rates and performance

## 🔄 Migration from Gmail-Only

If you were using the Gmail-only version:

1. Your existing Gmail data remains intact
2. Personal data is preserved
3. New unified system works alongside existing Gmail functionality
4. You can continue using Gmail-only options if preferred

Your enhanced system now supports both Gmail and Outlook for comprehensive email processing and PDF unlocking!
