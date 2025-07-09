# Enhanced Gmail PDF Statement Processor

## Overview
This enhanced system processes Gmail emails to extract bank statement PDFs and automatically unlock them using intelligent password detection and personal data combinations.

## Features
- ✅ **Smart Email Filtering**: Fetches only bank statement emails from last 2 months
- ✅ **Incremental Processing**: Only processes new emails (avoids duplicates)
- ✅ **Password Rules Detection**: Extracts password patterns and rules from email content
- ✅ **Personal Data Integration**: Uses your personal information to generate password candidates
- ✅ **Intelligent Password Generation**: Creates variations based on common banking patterns
- ✅ **Database Storage**: Stores all metadata for efficient processing
- ✅ **PDF Unlocking**: Automatically unlocks password-protected PDFs

## Prerequisites

### 1. Python Dependencies
```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client pikepdf
```

### 2. Gmail API Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Gmail API
4. Create OAuth 2.0 credentials (Desktop application)
5. Download the credentials as `credentials.json`
6. Place `credentials.json` in the same directory as the scripts

## Installation

1. **Save the Scripts**: Save all the Python scripts in the same directory:
   - `enhanced_gmail_client.py` - Main client with enhanced features
   - `personal_data_manager.py` - Personal data management utility
   - `main_email_processor.py` - Main script with interactive menu

2. **Directory Structure**:
   ```
   your_project/
   ├── credentials.json          # Google API credentials
   ├── enhanced_gmail_client.py  # Main client
   ├── personal_data_manager.py  # Personal data manager
   ├── main_email_processor.py   # Main script
   ├── downloads/               # PDF downloads (auto-created)
   └── email_data.db            # SQLite database (auto-created)
   ```

## Usage

### 1. First Time Setup

Run the main script:
```bash
python main_email_processor.py
```

Choose **Option 1: Setup Personal Data** and enter your information:
- **Date of Birth**: Format as DDMMYYYY (e.g., 01011990)
- **Mobile Number**: Your complete mobile number (e.g., 971501234567)
- **Names**: First name, last name, or any name variations
- **Card Numbers**: Last 4 digits of your credit cards
- **Account Numbers**: Last 4 digits of your bank accounts
- **Custom Hints**: Any specific passwords or patterns you know

### 2. Process New Emails

Choose **Option 2: Process New Emails** to:
- Search for bank statement emails from the last 2 months
- Extract password rules and hints from email content
- Download PDF attachments
- Store everything in the database

### 3. Unlock PDFs

Choose **Option 6: Unlock All PDFs** to:
- Generate password candidates based on your personal data
- Try different combinations and variations
- Unlock PDFs and save unlocked versions

## How Password Generation Works

The system generates password candidates using:

### 1. Direct Hints from Emails
- Passwords explicitly mentioned in emails
- Date formats found in email content
- Number sequences that might be passwords

### 2. Personal Data Variations
- **Date of Birth**: DDMMYYYY, DDMMYY, YYYYMMDD, MMYY
- **Mobile Number**: Last 4, 6, 8 digits
- **Names**: Lowercase, uppercase, title case
- **Card Numbers**: Last 4 digits

### 3. Intelligent Combinations
- Personal data + hints
- Date variations from recent months
- Common banking password patterns

### 4. Pattern Recognition
The system looks for password rules in emails like:
- "Password is your date of birth in DDMMYYYY format"
- "PDF password is the last 4 digits of your mobile number"
- "Use your first name + last 4 digits of card number"

## Database Structure

### Emails Table
- `id`: Unique email ID
- `subject`: Email subject
- `sender`: Sender email address
- `password_hints`: JSON array of extracted hints
- `password_rules`: JSON array of password rules/patterns
- `attachments`: JSON array of downloaded PDF paths
- `email_body`: Full email content for analysis
- `timestamp`: Email timestamp
- `processed_date`: When the email was processed

### Personal Data Table
- `data_type`: Type of personal data (date_of_birth, mobile_number, etc.)
- `data_value`: The actual value
- `description`: Description of the data
- `created_date`: When the data was added

## Bank Support

The system is configured to work with major UAE banks:
- Emirates NBD
- First Abu Dhabi Bank (FAB)
- Abu Dhabi Commercial Bank (ADCB)
- Dubai Islamic Bank (DIB)
- Emirates Islamic Bank
- Mashreq Bank
- RAK Bank
- And many more...

## Menu Options

1. **Setup Personal Data**: Add/manage your personal information
2. **Process New Emails**: Fetch and process new bank statement emails
3. **View Email Statistics**: See processing statistics
4. **View Recent Emails**: Display recently processed emails
5. **Test PDF Unlock**: Test unlocking with current data
6. **Unlock All PDFs**: Attempt to unlock all stored PDFs
7. **Database Management**: Manage stored data
8. **Exit**: Close the application

## Tips for Success

### 1. Complete Personal Data
- Add all variations of your personal information
- Include different date formats
- Add custom password hints you remember

### 2. Regular Processing
- Run the processor regularly to catch new emails
- The system only processes new emails to avoid duplicates

### 3. Password Rules
- Pay attention to the password rules extracted from emails
- Banks often provide specific password formats in their emails

### 4. Security
- Keep your `credentials.json` secure
- The database contains sensitive information
- Consider encrypting the database for production use

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Ensure `credentials.json` is in the correct directory
   - Check Gmail API is enabled in Google Cloud Console
   - Re-authenticate if tokens expire

2. **No Emails Found**
   - Check your Gmail search filters
   - Verify bank email addresses in the search query
   - Ensure emails are within the 2-month window

3. **PDF Unlock Failures**
   - Verify personal data is correctly entered
   - Check if password rules were properly extracted
   - Try adding more personal data variations

4. **Database Issues**
   - Delete `email_data.db` to start fresh
   - Check file permissions in the directory

### Performance Tips

- The system processes emails incrementally
- Large mailboxes may take time on first run
- Subsequent runs are much faster (only new emails)
- Consider running regularly to maintain efficiency

## Security Considerations

### Data Protection
- Personal data is stored locally in SQLite database
- No data is sent to external servers except Google APIs
- Consider database encryption for sensitive environments

### Access Control
- OAuth tokens are stored locally in `token.json`
- Ensure proper file permissions on sensitive files
- Regularly review and rotate access tokens

### PDF Security
- Unlocked PDFs are saved with `_unlocked` suffix
- Original password-protected PDFs are preserved
- Consider secure deletion of unlocked files after use

## Advanced Usage

### Custom Password Patterns
Add custom patterns by modifying the `generate_password_candidates` method:

```python
# Example: Add company-specific patterns
candidates.add(f"COMPANY{personal_data}")
candidates.add(f"{personal_data}BANK")
```

### Bank-Specific Rules
Extend the system for specific banks by modifying the email search query or adding bank-specific password generation logic.

### Batch Processing
For large numbers of emails, consider running in batch mode:

```python
# Process specific date ranges
client.search_credit_card_emails(months_back=6)
```

## Support and Maintenance

### Regular Updates
- Update bank email addresses as they change
- Modify search queries for new statement formats
- Add new password patterns as discovered

### Monitoring
- Check processing statistics regularly
- Monitor unlock success rates
- Review failed unlock attempts for pattern improvements

### Backup
- Regular database backups recommended
- Export functionality available in database management menu
- Consider automated backup scheduling

## Legal and Compliance

### Terms of Use
- This tool is for personal use with your own email account
- Ensure compliance with your bank's terms of service
- Respect Gmail API usage limits and quotas

### Data Privacy
- All processing is done locally on your machine
- No personal data is transmitted to third parties
- You maintain full control over your data

## Version History

### Current Version Features
- Enhanced password rule extraction
- Intelligent password generation
- Incremental email processing
- Comprehensive database management
- Interactive menu system
- Export/import functionality

### Future Enhancements
- Machine learning for password pattern detection
- Multi-language support for international banks
- Enhanced security with database encryption
- Cloud storage integration options
- Mobile app version

## Getting Help

If you encounter issues:
1. Check the troubleshooting section
2. Review the error messages carefully
3. Ensure all dependencies are installed
4. Verify Gmail API setup is complete
5. Check file permissions and directory structure

For optimal results, ensure your personal data is comprehensive and accurate. The system's success depends on the quality of the personal information provided and the password rules extracted from your emails.