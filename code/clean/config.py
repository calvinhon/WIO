"""
Configuration settings for the Enhanced Gmail PDF Unlocker
"""

import os
from pathlib import Path

# Gmail API settings
GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.json'

# Database settings
DATABASE_PATH = 'email_data.db'

# File paths
DOWNLOADS_DIR = 'downloads'
LOGS_DIR = 'logs'

# Create directories if they don't exist
for dir_path in [DOWNLOADS_DIR, LOGS_DIR]:
    Path(dir_path).mkdir(exist_ok=True)

# Logging configuration
LOG_LEVEL = 'INFO'
LOG_FILE = os.path.join(LOGS_DIR, 'app.log')

# LLM configuration
LLM_BACKENDS = [
    ("ollama", "llama3.1"),
    ("lmstudio", "llama-3.1-8b-instruct"),
    ("llamacpp", "llama-3.1-8b-instruct")
]

LLM_URLS = {
    "ollama": "http://localhost:11434",
    "lmstudio": "http://localhost:1234",
    "llamacpp": "http://localhost:8080"
}

# Search configuration
SEARCH_MONTHS_BACK = 6
MAX_SEARCH_RESULTS = 100

# Password generation settings
MAX_PASSWORD_CANDIDATES = 20
MIN_PASSWORD_LENGTH = 4
MAX_PASSWORD_LENGTH = 20

# Common bank patterns for UAE
BANK_PATTERNS = {
    'fab': r'(fab|first abu dhabi bank)',
    'adcb': r'(adcb|abu dhabi commercial bank)',
    'enbd': r'(enbd|emirates nbd)',
    'adib': r'(adib|abu dhabi islamic bank)',
    'dib': r'(dib|dubai islamic bank)',
    'mashreq': r'mashreq',
    'rakbank': r'(rak|rakbank)',
    'nbf': r'(nbf|national bank of fujairah)',
    'hsbc': r'hsbc',
    'citibank': r'citi',
    'sc': r'standard chartered',
    'emirates_islamic': r'(emiratesislamic|emirates islamic)',
    'cbd': r'(cbd|commercial bank of dubai)',
    'uab': r'(uab|united arab bank)',
    'barclays': r'barclays',
    'bnp_paribas': r'(bnp|paribas)',
    'bank_of_baroda': r'(bank of baroda|bob)',
    'habib_bank': r'(hbl|habib bank)',
    'arab_bank': r'arab bank',
    'al_hilal': r'(alnilal|al hilal)',
    'ajman_bank': r'ajman bank',
    'sib': r'(sib|sharjah islamic bank)',
    'emirates_investment': r'(eibank|emirates investment)'
}

# Email search query
SEARCH_QUERY_TEMPLATE = """
has:attachment filename:pdf 
subject:(statement OR "credit card" OR bank OR "account statement" OR "e-statement" OR "monthly statement") 
after:{date}
"""

# Password rule patterns
PASSWORD_RULE_PATTERNS = [
    r'password (is|will be|format|structure|contains)[\s:]*([^\n.]{1,100})',
    r'pdf password[\s:]*([^\n.]{1,100})',
    r'to open.*password[\s:]*([^\n.]{1,100})',
    r'statement password[\s:]*([^\n.]{1,100})',
    r'password.*last (\d+) digits',
    r'password.*birth date',
    r'password.*mobile number',
    r'password.*card number',
    r'password.*account number',
    r'password.*first name',
    r'password.*last name',
    r'password.*date of birth',
    r'password.*phone number',
    r'password.*DDMMYYYY',
    r'password.*DD/MM/YYYY',
    r'password.*YYYYMMDD',
    r'combination of.*password',
    r'password.*combination.*of'
]

# Password hint patterns
PASSWORD_HINT_PATTERNS = [
    r'password[\s:=]*([A-Za-z0-9@#$%^&*()_+\-=\[\]{}|;:,.<>?]{4,20})',
    r'pdf password[\s:=]*([A-Za-z0-9@#$%^&*()_+\-=\[\]{}|;:,.<>?]{4,20})',
    r'to open.*password[\s:=]*([A-Za-z0-9@#$%^&*()_+\-=\[\]{}|;:,.<>?]{4,20})',
]

# Date patterns
DATE_PATTERNS = [
    r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b',
    r'\b(\d{2,4}[/-]\d{1,2}[/-]\d{1,2})\b',
    r'\b(\d{2}\.\d{2}\.\d{4})\b',
    r'\b(\d{4}\.\d{2}\.\d{2})\b'
]

# Account/Card patterns
ACCOUNT_PATTERNS = [
    r'account.*?(\d{4,6})',
    r'a/c.*?(\d{4,6})',
    r'account ending.*?(\d{4,6})',
    r'account.*?ending.*?(\d{4,6})'
]

CARD_PATTERNS = [
    r'card.*?(\d{4})',
    r'credit card.*?(\d{4})',
    r'ending.*?(\d{4})',
    r'card.*?ending.*?(\d{4})'
]
