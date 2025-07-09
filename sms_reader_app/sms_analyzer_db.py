#!/usr/bin/env python3
"""
SMS Credit Card Last 4 Digits Extractor using FinBERT - Database Version
This program extracts unique last 4 digits of credit cards from SMS messages stored in SQLite database
and saves financial summaries back to the database
"""

import json
import re
import sys
import sqlite3
import subprocess
import os
import shutil
from typing import Set, List, Dict, Tuple, Any, Union, Optional
from collections import defaultdict
import torch
from transformers import AutoTokenizer, AutoModelForTokenClassification
from transformers.pipelines import pipeline
import warnings
from datetime import datetime
import dateutil.parser

# Suppress warnings
warnings.filterwarnings('ignore')
import logging
logging.getLogger('transformers').setLevel(logging.ERROR)
import os
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

class CreditCardExtractorDB:
    # Android sync functionality
    def __init__(self, db_path: str, device_id: Optional[str] = None, app_package: str = "com.example.sms_reader_app", auto_sync: bool = True):
        self.db_path = db_path
        self.device_id = device_id
        self.app_package = app_package
        self.device_db_path = f"/data/data/{app_package}/databases/sms_reader.db"
        self.auto_sync = auto_sync
        
        if auto_sync:
            self._sync_from_device()
        
        self._init_ml_models()
    
    def _sync_from_device(self):
        """Sync database from Android device"""
        try:
            print("🔄 Syncing database from Android device...", file=sys.stderr)
            
            # Check if device is connected
            cmd = ["adb"] + (["-s", self.device_id] if self.device_id else []) + ["devices"]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            if "device" not in result.stdout:
                print("❌ No Android device connected - using local database only", file=sys.stderr)
                return False
            
            # Create backup of current local database
            if os.path.exists(self.db_path):
                backup_path = f"{self.db_path}.backup"
                shutil.copy2(self.db_path, backup_path)
                print(f"📋 Created backup: {backup_path}", file=sys.stderr)
            
            # Use cat to get database content
            temp_file = "/tmp/sms_reader_sync.db"
            
            copy_cmd = ["adb"] + (["-s", self.device_id] if self.device_id else []) + [
                "shell", "run-as", self.app_package,
                "cat", self.device_db_path
            ]
            
            # Get database content
            with open(temp_file, 'wb') as f:
                result = subprocess.run(copy_cmd, stdout=f, stderr=subprocess.PIPE, check=True)
            
            # Copy to our local database file
            shutil.copy2(temp_file, self.db_path)
            os.remove(temp_file)
            
            # Get database size
            size = os.path.getsize(self.db_path)
            print(f"✅ Database synced successfully from device ({size} bytes)", file=sys.stderr)
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to sync from device: {e.stderr}", file=sys.stderr)
            return False
        except Exception as e:
            print(f"❌ Error syncing from device: {e}", file=sys.stderr)
            return False
    
    def _push_to_device(self):
        """Push updated database back to Android device"""
        try:
            if not self.auto_sync:
                print("Auto-sync disabled - skipping push to device", file=sys.stderr)
                return False
                
            if not os.path.exists(self.db_path):
                print("❌ No local database file to push", file=sys.stderr)
                return False
            
            print("🔄 Pushing updated database to Android device...", file=sys.stderr)
            
            # Read local database
            with open(self.db_path, 'rb') as f:
                db_content = f.read()
            
            # Create temp file
            temp_file = "/tmp/sms_reader_upload.db"
            
            # Write database content to temp file
            with open(temp_file, 'wb') as f:
                f.write(db_content)
            
            # Push to device using dd
            push_cmd = ["adb"] + (["-s", self.device_id] if self.device_id else []) + [
                "shell", "run-as", self.app_package,
                "dd", f"of={self.device_db_path}"
            ]
            
            with open(temp_file, 'rb') as f:
                subprocess.run(push_cmd, stdin=f, check=True)
            
            # Clean up temp file
            os.remove(temp_file)
            
            print("✅ Database pushed back to Android device successfully", file=sys.stderr)
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to push to device: {e.stderr}", file=sys.stderr)
            return False
        except Exception as e:
            print(f"❌ Error pushing to device: {e}", file=sys.stderr)
            return False

    # Convert date to DD.MM.YY format
    def convert_date_format(self, date_str: str) -> Optional[str]:
        if not date_str:
            return None
            
        try:
            # Handle various date formats
            # Try parsing ISO format first (from dateTime_readable)
            if 'T' in date_str:
                dt = dateutil.parser.parse(date_str)
                return dt.strftime('%d.%m.%y')
            
            # Handle other formats like "26/08/25", "06Jun25", etc.
            # Try common patterns
            patterns = [
                r'(\d{1,2})/(\d{1,2})/(\d{2,4})',  # DD/MM/YY or DD/MM/YYYY
                r'(\d{1,2})(\w{3})(\d{2})',        # DDMmmYY (e.g., 06Jun25)
                r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})',  # DD-MM-YY
            ]
            
            for pattern in patterns:
                match = re.match(pattern, date_str)
                if match:
                    day, month, year = match.groups()
                    
                    # Handle month names
                    if month.isalpha():
                        month_names = {
                            'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
                            'may': '05', 'jun': '06', 'jul': '07', 'aug': '08',
                            'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'
                        }
                        month = month_names.get(month.lower(), month)
                    
                    # Ensure 2-digit format
                    day = day.zfill(2)
                    month = month.zfill(2)
                    
                    # Handle year format
                    if len(year) == 4:
                        year = year[-2:]  # Take last 2 digits
                    elif len(year) == 2:
                        # Convert 2-digit year to proper format
                        year_int = int(year)
                        if year_int > 50:  # Assume 1950-1999
                            year = year
                        else:  # Assume 2000-2050
                            year = year
                    
                    return f"{day}.{month}.{year}"
            
            # If no pattern matches, try dateutil as fallback
            dt = dateutil.parser.parse(date_str, fuzzy=True)
            return dt.strftime('%d.%m.%y')
            
        except Exception as e:
            print(f"Error parsing date '{date_str}': {e}", file=sys.stderr)
            return date_str  # Return original if parsing fails

    def _init_ml_models(self):
        """Initialize the FinBERT model and tokenizer"""
        # Load FinBERT model for sequence classification
        # We'll use it to identify financial entities and then extract card numbers
        self.model_name = "ProsusAI/finbert"
        
        try:
            # Load tokenizer and model
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForTokenClassification.from_pretrained(
                self.model_name,
                num_labels=2,  # Binary classification
                ignore_mismatched_sizes=True
            )
            
            # Create a pipeline for easier use
            self.classifier = pipeline(
                "token-classification",
                model=self.model,
                tokenizer=self.tokenizer,
                aggregation_strategy="simple"
            )
            
        except Exception as e:
            self.classifier = None

    # Connect to SQLite database
    def connect_db(self) -> sqlite3.Connection:
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
            return conn
        except sqlite3.Error as e:
            print(f"Error connecting to database: {e}", file=sys.stderr)
            raise

    # Create tables if they don't exist
    def create_tables(self):
        try:
            conn = self.connect_db()
            cursor = conn.cursor()
            
            # Create cards table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cards (
                    card_id TEXT PRIMARY KEY,
                    latest_due_date TEXT,
                    latest_total_amount REAL,
                    latest_min_amount REAL,
                    total_payments_made REAL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create payments table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS payments (
                    payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    card_id TEXT NOT NULL,
                    amount REAL NOT NULL,
                    payment_date TEXT NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (card_id) REFERENCES cards(card_id) ON DELETE CASCADE
                )
            """)
            
            conn.commit()
            conn.close()
            
        except sqlite3.Error as e:
            print(f"Error creating tables: {e}", file=sys.stderr)
            raise

    # Read SMS messages from database
    def read_sms_messages(self, table_name: str = "messages") -> List[Dict]:
        try:
            conn = self.connect_db()
            cursor = conn.cursor()
            
            # First, check if the table exists
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name=?
            """, (table_name,))
            
            if not cursor.fetchone():
                print(f"Table '{table_name}' not found in database", file=sys.stderr)
                return []
            
            # Read all messages
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()
            
            # Convert rows to list of dictionaries
            messages = []
            for row in rows:
                message = dict(row)
                messages.append(message)
            
            conn.close()
            return messages
            
        except sqlite3.Error as e:
            print(f"Error reading SMS messages: {e}", file=sys.stderr)
            return []

    # Save card summary to database
    def save_card_summary(self, card_id: str, financial_summary: Dict[str, Any]):
        try:
            conn = self.connect_db()
            cursor = conn.cursor()
            
            # Insert or replace card summary
            cursor.execute("""
                INSERT OR REPLACE INTO cards (
                    card_id, 
                    latest_due_date, 
                    latest_total_amount, 
                    latest_min_amount, 
                    total_payments_made,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                card_id,
                financial_summary.get('latest_due_date'),
                financial_summary.get('latest_total_amount'),
                financial_summary.get('latest_min_amount'),
                financial_summary.get('total_payments_made', 0)
            ))
            
            # Delete existing payments for this card
            cursor.execute("DELETE FROM payments WHERE card_id = ?", (card_id,))
            
            # Insert payments
            payments = financial_summary.get('payments', [])
            for payment in payments:
                cursor.execute("""
                    INSERT INTO payments (
                        card_id, 
                        amount, 
                        payment_date, 
                        description
                    ) VALUES (?, ?, ?, ?)
                """, (
                    card_id,
                    payment['amount'],
                    payment['date'],
                    payment['description']
                ))
            
            conn.commit()
            conn.close()
            
        except sqlite3.Error as e:
            print(f"Error saving card summary: {e}", file=sys.stderr)
            raise

    # Extract financial information from message text
    def extract_financial_info(self, text: str) -> Dict[str, Any]:
        info: Dict[str, Union[str, float, None]] = {
            'due_date': None,
            'total_amount': None,
            'min_amount': None,
            'payment_made': None
        }
        
        # Extract due date
        due_date_patterns = [
            r'due date[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'due date[:\s]+(\d{1,2}\s+\w+\s+\d{2,4})',
            r'by\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'Due Date\s+(\d{1,2}/\d{1,2}/\d{2})',
            r'due date is\s+(\d{1,2}\w{3}\d{2})'
        ]
        
        for pattern in due_date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                info['due_date'] = match.group(1)
                break
        
        # Extract total amount
        total_patterns = [
            r'total\s+(?:amount\s+)?due[:\s]+AED\s*([\d,]+\.?\d*)',
            r'total\s+amt\s+due[:\s]+AED\s*([\d,]+\.?\d*)',
            r'total\s+due\s+to\s+avoid[^:]+:\s*AED\s*([\d,]+\.?\d*)',
            r'amount\s+due\s+is\s+AED\s*([\d,]+\.?\d*)'
        ]
        
        for pattern in total_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                info['total_amount'] = float(match.group(1).replace(',', ''))
                break
        
        # Extract minimum amount
        min_patterns = [
            r'min(?:imum)?\s+(?:amount\s+)?(?:due|payment)[:\s]+AED\s*([\d,]+\.?\d*)',
            r'min\s+amt\s+due[:\s]+AED\s*([\d,]+\.?\d*)',
            r'pay\s+min\.?\s+AED\s*([\d,]+\.?\d*)',
            r'pay\s+at\s+least\s+AED\s*([\d,]+\.?\d*)',
            r'minimum\s+(?:due\s+)?is\s+AED\s*([\d,]+\.?\d*)'
        ]
        
        for pattern in min_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                info['min_amount'] = float(match.group(1).replace(',', ''))
                break
        
        # Extract payment made (including purchases and actual payments)
        payment_patterns = [
            # Actual payments received
            r'payment\s+of\s+AED\s*([\d,]+\.?\d*)\s+(?:for\s+card|.*?(?:received|processed))',
            r'Your\s+[Pp]ayment\s+of\s+AED\s*([\d,]+\.?\d*)',
            r'receipt\s+of\s+your\s+payment\s+of\s+AED\s*([\d,]+\.?\d*)',
            r'your\s+payment\s+of\s+AED\s*([\d,]+\.?\d*)\s+.*?(?:received|processed)',
            
            # Credit card purchases/transactions
            r'AED\s*([\d,]+\.?\d*)\s+purchase\s+approved',
            r'AED\s*([\d,]+\.?\d*)\s+(?:purchase|transaction)\s+(?:approved|processed)',
            r'(?:purchase|transaction)\s+of\s+AED\s*([\d,]+\.?\d*)',
            r'AED\s*([\d,]+\.?\d*)\s+(?:spent|charged|debited)',
            
            # General transaction patterns
            r'AED\s*([\d,]+\.?\d*)\s+.*?(?:card\s+ending|with\s+card)',
            r'(?:spent|charged|paid)\s+AED\s*([\d,]+\.?\d*)',
            
            # Refunds and credits
            r'refund\s+of\s+AED\s*([\d,]+\.?\d*)',
            r'credit\s+of\s+AED\s*([\d,]+\.?\d*)',
            
            # Transfer patterns
            r'transfer\s+of\s+AED\s*([\d,]+\.?\d*)',
            r'AED\s*([\d,]+\.?\d*)\s+(?:transferred|debited)'
        ]
        
        for pattern in payment_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                info['payment_made'] = float(match.group(1).replace(',', ''))
                break
        
        # Remove None values for cleaner output
        return {k: v for k, v in info.items() if v is not None}
    
    # Generate short description using FinBERT
    def _generate_description(self, message_body: str) -> str:
        try:
            if not self.classifier:
                return self._extract_keywords_fallback(message_body)
            
            # Use FinBERT to analyze the financial context
            # Since FinBERT is primarily for sentiment, we'll extract key financial terms
            financial_terms = []
            
            # Extract key financial indicators
            message_lower = message_body.lower()
            
            # Transaction type keywords
            if 'purchase' in message_lower:
                financial_terms.append('purchase')
            elif 'payment' in message_lower:
                financial_terms.append('payment')
            elif 'refund' in message_lower:
                financial_terms.append('refund')
            elif 'transfer' in message_lower:
                financial_terms.append('transfer')
            
            # Extract merchant/location if available
            merchant_patterns = [
                r'at\s+([A-Za-z\s]+?)(?:\s+on|\s+with|\s*$)',
                r'purchase\s+(?:approved\s+)?at\s+([A-Za-z\s]+?)(?:\s+on|\s+with)',
                r'from\s+([A-Za-z\s]+?)(?:\s+on|\s+with|\s*$)'
            ]
            
            for pattern in merchant_patterns:
                match = re.search(pattern, message_body, re.IGNORECASE)
                if match:
                    merchant = match.group(1).strip()
                    if len(merchant) > 0 and len(merchant) < 15:
                        financial_terms.append(merchant.lower())
                    break
            
            # Extract amount context
            if 'aed' in message_lower:
                financial_terms.append('aed')
            
            # Extract card context
            if 'card' in message_lower:
                financial_terms.append('card')
            
            # Extract status
            if 'approved' in message_lower:
                financial_terms.append('approved')
            elif 'processed' in message_lower:
                financial_terms.append('processed')
            elif 'received' in message_lower:
                financial_terms.append('received')
            
            # Build description (max 5 words)
            description_words = financial_terms[:5]
            
            # Pad with generic terms if needed
            if len(description_words) < 3:
                if 'payment' not in description_words:
                    description_words.append('payment')
                if 'transaction' not in description_words:
                    description_words.append('transaction')
            
            # Ensure we have exactly 5 words or less
            description_words = description_words[:5]
            
            return ' '.join(description_words).title()
            
        except Exception as e:
            print(f"Error generating description: {e}", file=sys.stderr)
            return self._extract_keywords_fallback(message_body)
    
    # Fallback method for description generation
    def _extract_keywords_fallback(self, message_body: str) -> str:
        message_lower = message_body.lower()
        keywords = []
        
        # Transaction type
        if 'purchase' in message_lower:
            keywords.append('Purchase')
        elif 'payment' in message_lower:
            keywords.append('Payment')
        elif 'refund' in message_lower:
            keywords.append('Refund')
        else:
            keywords.append('Transaction')
        
        # Amount
        if 'aed' in message_lower:
            keywords.append('AED')
        
        # Status
        if 'approved' in message_lower:
            keywords.append('Approved')
        elif 'processed' in message_lower:
            keywords.append('Processed')
        elif 'received' in message_lower:
            keywords.append('Received')
        
        # Card context
        if 'card' in message_lower:
            keywords.append('Card')
        
        # Generic fill
        if len(keywords) < 3:
            keywords.append('Complete')
        
        return ' '.join(keywords[:5])
    
    # Extract potential card numbers using regex patterns
    def extract_card_numbers_regex(self, text: str) -> Set[str]:
        card_numbers = set()
        
        # Pattern 1: "card ending XXXX" or "card ending with XXXX"
        pattern1 = r'card\s+ending\s+(?:with\s+)?(\d{4})'
        
        # Pattern 2: "XXX1234" or "XXXXXXXX1234" format
        pattern2 = r'[Xx]{3,}\d{4}'
        
        # Pattern 3: "card 1234" format
        pattern3 = r'card\s+(\d{4})(?:\s|$)'
        
        # Pattern 4: Numbers that look like masked cards (e.g., "4194XXXXXXXX6612")
        pattern4 = r'\d{4}[Xx]{6,}\d{4}'
        
        # Find matches for each pattern
        for pattern in [pattern1, pattern2, pattern3, pattern4]:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if pattern == pattern1 or pattern == pattern3:
                    card_numbers.add(match)
                elif pattern == pattern2:
                    # Extract last 4 digits
                    card_numbers.add(match[-4:])
                elif pattern == pattern4:
                    # Extract last 4 digits
                    card_numbers.add(match[-4:])
        
        return card_numbers
    
    # Use FinBERT to identify financial entities and extract card numbers
    def extract_with_finbert(self, text: str) -> Set[str]:
        if not self.classifier:
            return self.extract_card_numbers_regex(text)
        
        try:
            # Get predictions from FinBERT
            # Since FinBERT is trained for sentiment, we'll use it to identify
            # financial context and then apply regex on relevant parts
            
            # First, check if the text contains financial keywords
            financial_keywords = [
                'card', 'credit', 'payment', 'billing', 'statement',
                'due', 'amount', 'AED', 'processed', 'ending'
            ]
            
            is_financial = any(keyword.lower() in text.lower() for keyword in financial_keywords)
            
            if is_financial:
                # Extract card numbers using regex since FinBERT doesn't directly extract entities
                return self.extract_card_numbers_regex(text)
            else:
                return set()
                
        except Exception as e:
            print(f"Error using FinBERT: {e}", file=sys.stderr)
            return self.extract_card_numbers_regex(text)
    
    # Process all messages and group by card last 4 digits
    def process_messages(self, messages: List[Dict]) -> Dict[str, List[Dict]]:
        card_to_messages = defaultdict(list)
        
        for message in messages:
            body = message.get('body') or ''
            
            # Extract card numbers using FinBERT-enhanced extraction
            card_numbers = self.extract_with_finbert(body)
            
            # Validate extracted numbers (should be 4 digits) and group messages
            for num in card_numbers:
                if re.match(r'^\d{4}$', num):
                    # Create a simplified message object for financial analysis
                    simplified_message = {
                        'body': message.get('body') or '',
                        'dateTime_readable': message.get('dateTime_readable') or ''
                    }
                    
                    # Extract financial information from the message
                    financial_info = self.extract_financial_info(body)
                    if financial_info:
                        simplified_message['financial_info'] = financial_info
                    
                    card_to_messages[num].append(simplified_message)
        
        # Sort messages by date for each card
        for card_num in card_to_messages:
            card_to_messages[card_num].sort(
                key=lambda x: x.get('dateTime_readable') or '',
                reverse=True  # Most recent first
            )
        
        return dict(card_to_messages)
    
    # Analyze financial information across all messages for a card
    def analyze_card_finances(self, messages: List[Dict]) -> Dict[str, Any]:
        summary = {
            'latest_due_date': None,
            'latest_total_amount': None,
            'latest_min_amount': None,
            'total_payments_made': 0.0,
            'payments': []
        }
        
        # Sort messages by date to find the latest information
        sorted_messages = sorted(messages, key=lambda x: x.get('dateTime_readable') or '', reverse=True)
        
        for msg in sorted_messages:
            if 'financial_info' in msg:
                info = msg['financial_info']
                
                # Update latest due date, total, and min amounts (from most recent messages)
                # Convert due date to DD.MM.YY format
                if info.get('due_date') and not summary['latest_due_date']:
                    summary['latest_due_date'] = self.convert_date_format(info['due_date'])
                
                if info.get('total_amount') and not summary['latest_total_amount']:
                    summary['latest_total_amount'] = info['total_amount']
                
                if info.get('min_amount') and not summary['latest_min_amount']:
                    summary['latest_min_amount'] = info['min_amount']
                
                # Track all payments with detailed information
                if info.get('payment_made'):
                    summary['total_payments_made'] += info['payment_made']
                    
                    # Create detailed payment entry with better date parsing
                    payment_date = self.convert_date_format(msg.get('dateTime_readable') or '')
                    
                    # If dateTime_readable parsing fails, try to extract date from message body
                    if not payment_date or payment_date == '01.01.00':
                        # Try to extract date from message body
                        body = msg.get('body', '')
                        date_patterns = [
                            r'on\s+(\d{1,2}/\d{1,2}/\d{2,4})',
                            r'(\d{1,2}/\d{1,2}/\d{2,4})',
                            r'(\d{1,2}\s+\w+\s+\d{2,4})',
                            r'dated\s+(\d{1,2}\s+\w+\s+\d{2,4})'
                        ]
                        
                        for pattern in date_patterns:
                            match = re.search(pattern, body, re.IGNORECASE)
                            if match:
                                extracted_date = self.convert_date_format(match.group(1))
                                if extracted_date and extracted_date != '01.01.00':
                                    payment_date = extracted_date
                                    break
                    
                    # Use current date if still no valid date found
                    if not payment_date or payment_date == '01.01.00':
                        from datetime import datetime
                        payment_date = datetime.now().strftime('%d.%m.%y')
                    
                    payment_entry = {
                        'amount': info['payment_made'],
                        'date': payment_date,
                        'description': self._generate_description(msg.get('body', ''))
                    }
                    
                    summary['payments'].append(payment_entry)
        
        # Remove empty fields
        return {k: v for k, v in summary.items() if v or (isinstance(v, list) and len(v) > 0)}
    
    # Simple payment summary
    def analyze_payments_detailed(self):
        """Provide simple summary of all payments in the database"""
        try:
            conn = self.connect_db()
            cursor = conn.cursor()
            
            # Get overall summary
            cursor.execute("""
                SELECT 
                    COUNT(DISTINCT card_id) as total_cards,
                    SUM(latest_total_amount) as total_due_all,
                    SUM(total_payments_made) as total_paid_all,
                    (SELECT COUNT(*) FROM payments) as total_payment_records
                FROM cards
            """)
            
            summary = cursor.fetchone()
            print(f"Payment Summary: {summary['total_cards']} cards, AED {summary['total_due_all'] or 0} due, AED {summary['total_paid_all'] or 0} paid")
            
            conn.close()
            
        except Exception as e:
            print(f"Error in payment analysis: {e}", file=sys.stderr)

    # Main execution function
    def run(self, sms_table_name: str = "messages"):
        try:
            # Create tables if they don't exist
            self.create_tables()
            
            # Read SMS messages from database
            messages = self.read_sms_messages(sms_table_name)
            
            if not messages:
                print("No messages found in the database", file=sys.stderr)
                return
            
            # Process messages
            card_messages_grouped = self.process_messages(messages)
            
            # Save results to database
            cards_processed = 0
            for card_num in sorted(card_messages_grouped.keys()):
                messages_for_card = card_messages_grouped[card_num]
                
                # Analyze financial information across all messages for this card
                financial_summary = self.analyze_card_finances(messages_for_card)
                
                # Only save cards that have financial information
                if financial_summary:
                    self.save_card_summary(card_num, financial_summary)
                    cards_processed += 1
            
            print(f"Processed {cards_processed} cards from {len(messages)} messages")
            
            # Run payment analysis
            self.analyze_payments_detailed()
            
            # Push updated database back to Android device
            if self.auto_sync:
                self._push_to_device()
                
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            raise


# Main function to run the extractor
def main():
    # Default database path - you can modify this
    db_path = "/Users/aserebry/development/wio/sms_app/sms_app/sms/sms_reader_app/sms_reader_latest.db"
    
    # You can also specify a different SMS table name if needed
    sms_table_name = "bank_sms"
    
    # Android device settings
    device_id = None  # Use None for default device, or specify like "emulator-5554"
    app_package = "com.example.sms_reader_app"
    auto_sync = True  # Set to False to disable Android sync
    
    # Initialize without verbose output
    
    # Create extractor instance with Android sync support
    extractor = CreditCardExtractorDB(
        db_path=db_path,
        device_id=device_id,
        app_package=app_package,
        auto_sync=auto_sync
    )
    
    # Run extraction from database
    extractor.run(sms_table_name)


if __name__ == "__main__":
    main() 