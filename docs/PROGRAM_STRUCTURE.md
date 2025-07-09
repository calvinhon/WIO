# Gmail PDF Password Generator - Program Structure & Usage Guide

## 📁 Program Architecture

### Core Components

```
d:\H\42AD\WIO\code/
├── 📋 Main Scripts
│   ├── main_email_fetch.py          # 🚀 Main entry point with interactive menu
│   ├── enhanced_gmail_client.py     # 📧 Enhanced Gmail client with PDF processing
│   ├── personal_data_manager.py     # 👤 Personal data management utility
│   └── password_generator.py        # 🔐 Advanced password generation with LLM support
│
├── 📚 Support Libraries
│   ├── gmail_client.py             # 📮 Basic Gmail client
│   ├── pdf_unlocker.py            # 🔓 PDF unlocking utilities
│   └── email_processor.py         # 📨 Email processing utilities
│
├── 🧪 Testing & Setup
│   ├── test_pdf_unlocker.py       # 🔍 PDF unlocking tests
│   ├── test_gmailclient.py        # 📧 Gmail client tests
│   └── setup.py                   # ⚙️ Installation and setup script
│
├── 📂 Configuration & Data
│   ├── requirements.txt           # 📦 Python dependencies
│   ├── credentials.json          # 🔑 Google API credentials (you need to add this)
│   ├── token.json                # 🎟️ OAuth token (auto-generated)
│   ├── email_data.db             # 💾 SQLite database (auto-created)
│   └── downloads/                # 📄 Downloaded PDF files
│
└── 📖 Documentation
    └── read.md                   # 📚 Detailed documentation
```

## 🏗️ System Architecture

### 1. Data Flow
```
Gmail API → Enhanced Gmail Client → Email Processing → Password Generation → PDF Unlocking
     ↓              ↓                    ↓                  ↓              ↓
  Auth Token    Email Metadata    Password Rules    LLM/Rule-based    Unlocked PDFs
     ↓              ↓                    ↓            Generation           ↓
  token.json    email_data.db      Pattern Matching      ↓           downloads/
                     ↓                    ↓          Password DB
               Personal Data       Rule Extraction        ↓
                     ↓                    ↓         Success/Failure
            personal_data table    password_hints         ↓
                                                    Updated Status
```

### 2. Database Schema
```sql
-- Email metadata and processing results
CREATE TABLE emails (
    id TEXT PRIMARY KEY,              -- Gmail message ID
    subject TEXT,                     -- Email subject
    sender TEXT,                      -- Email sender
    date TEXT,                        -- Email date
    snippet TEXT,                     -- Email snippet
    password_hints TEXT,              -- JSON array of password hints
    password_rules TEXT,              -- JSON array of password rules
    attachments TEXT,                 -- JSON array of attachments
    timestamp INTEGER,                -- Unix timestamp
    email_body TEXT,                  -- Full email body
    processed_date TEXT               -- When processed
);

-- Personal data for password generation
CREATE TABLE personal_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data_type TEXT,                   -- Type of data (birth_date, mobile, etc.)
    data_value TEXT,                  -- The actual value
    description TEXT,                 -- Description
    created_date TEXT                 -- When added
);
```

## 🚀 How to Run the Program

### Prerequisites

1. **Python 3.8+** installed
2. **Google API Credentials** (`credentials.json`)
3. **Dependencies** installed

### Step-by-Step Setup

#### 1. Install Dependencies
```bash
cd d:\H\42AD\WIO\code
pip install -r requirements.txt
```

#### 2. Google API Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create/select project
3. Enable Gmail API
4. Create OAuth 2.0 credentials (Desktop app)
5. Download as `credentials.json`
6. Place in `/code` directory

#### 3. Run the Main Program
```bash
python main_email_fetch.py
```

### 📋 Program Menu Options

When you run `main_email_fetch.py`, you'll see:

```
📬 Enhanced Gmail PDF Statement Processor
==================================================

🔧 Main Menu
1. Setup Personal Data          # 👤 Configure your personal information
2. Process New Emails           # 📧 Fetch and process bank emails
3. View Email Statistics        # 📊 Show processing statistics
4. View Recent Emails           # 📧 Display recent processed emails
5. Test PDF Unlock              # 🔍 Test PDF unlocking functionality
6. Unlock All PDFs              # 🔓 Unlock all downloaded PDFs
7. Database Management          # 🗄️ Manage database and personal data
8. Exit                         # 👋 Exit program
```

### 🏃‍♂️ Quick Start Workflow

#### First Run:
```bash
python main_email_fetch.py
# Select option 1: Setup Personal Data
# Enter your information (birth date, mobile, etc.)
# Select option 2: Process New Emails
# Select option 6: Unlock All PDFs
```

#### Subsequent Runs:
```bash
python main_email_fetch.py
# Select option 2: Process New Emails (gets new emails only)
# Select option 6: Unlock All PDFs
```

## 🔧 Individual Component Usage

### 1. Personal Data Manager
```bash
python personal_data_manager.py
```
- Standalone utility for managing personal data
- Interactive setup for password generation

### 2. Password Generator (Advanced)
```bash
python password_generator.py
```
- Uses local LLM (Ollama/LMStudio) for intelligent password generation
- Requires local LLM setup (optional)

### 3. Enhanced Gmail Client
```bash
python enhanced_gmail_client.py
```
- Can be imported as a module
- Provides Gmail processing capabilities

## 🔑 Authentication Flow

### First Time Authentication:
1. Program opens browser for Google OAuth
2. Sign in with your Gmail account
3. Grant permissions
4. Token saved to `token.json`

### Subsequent Runs:
- Uses saved token
- Auto-refreshes if expired

## 📊 Data Storage

### Email Data (`email_data.db`)
- SQLite database
- Stores email metadata, password hints, rules
- Prevents reprocessing same emails

### Personal Data
- Birth date, mobile number, names
- Card/account number last 4 digits
- Custom password hints

### Downloaded Files
- PDFs saved in `downloads/` directory
- Original names preserved
- Unlocked versions created

## 🔍 Troubleshooting

### Common Issues:

1. **Missing credentials.json**
   - Download from Google Cloud Console
   - Place in `/code` directory

2. **Authentication Error**
   - Delete `token.json`
   - Re-run program for fresh authentication

3. **No emails found**
   - Check Gmail has bank statement emails
   - Verify email filters in code

4. **PDF unlock failures**
   - Add more personal data
   - Check password hints in emails
   - Verify PDF is password-protected

### Debug Mode:
```bash
python main_email_fetch.py
# Select option 7: Database Management
# Select option 1: View Personal Data
# Check if personal data is properly stored
```

## 🔒 Security Notes

- `credentials.json` and `token.json` contain sensitive data
- Database may contain personal information
- PDFs may contain financial data
- Keep all files secure and backed up

## 📈 Performance

- Incremental processing (only new emails)
- Efficient database queries
- Parallel password attempts
- LLM integration for smart password generation

## 🎯 Success Metrics

The program tracks:
- Emails processed
- PDFs downloaded
- PDFs successfully unlocked
- Password success rates
- Processing time

Run option 3 (View Email Statistics) to see current metrics.
