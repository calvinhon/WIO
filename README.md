For the email component, run ./startFlutter.sh which will build a Docker container with the Dockerfile. Make sure to run ollama serve, ollama pull mistral:instruct, and ollama pull nuextract before running functions related to LLM calls. 

For sms component, use command `adb devices` to get device_id. After that run `flutter run -d device_id` (from sms_reader_app).


### Email Component Setup

1. **Gmail Setup**
   - Create Google Cloud Project and enable Gmail API
   - Download `credentials.json` and place in `email/python/secret/` folder

2. **Outlook Setup** (Optional)
   - Create Azure App Registration
   - Note the Client ID for configuration

3. **Run Email Processor**
   ```bash
   cd email/python
   python3 main_email_fetch.py
   ```

## 📁 Email Parser ##

```
WIO/
├── email/python/           # Email processing scripts
│   ├── main_email_fetch.py # Main application
│   ├── enhanced_gmail_client.py
│   ├── outlook_client.py
│   ├── personal_data_manager.py
│   └── requirements.txt
├── sms_reader_app/         # Flutter SMS app
├── docs/                   # Documentation
└── Dockerfile             # Container setup
```

## 🔧 Configuration

### Gmail Setup
1. Visit [Google Cloud Console](https://console.cloud.google.com/)
2. Create project and enable Gmail API
3. Create OAuth 2.0 credentials
4. Download as `credentials.json`
5. Place in `email/python/secret/` folder

### Outlook Setup
Uses default test configuration or custom Azure app:
- Client ID: default in code
- Tenant: `common`

## 📊 Data Storage

- **SQLite Database** - Local storage for processed emails and personal data
- **Assets Folder** - Downloaded attachments and extracted text
- **Privacy-First** - All processing happens locally

## 🛡️ Security

- **Local Processing** - No data sent to external services (except email APIs)
- **OAuth2 Authentication** - Secure email access
- **Personal Data Encryption** - Sensitive data is protected
- **On-Device SMS** - SMS processing stays on device
