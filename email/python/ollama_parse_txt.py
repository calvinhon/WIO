import os
import json
import sqlite3
import subprocess
import logging
import sys
import re
from typing import Optional, Dict, Any

DB_PATH = 'bills.db'

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def init_database():
    """Initialize the database with proper schema."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Drop existing table if it exists (for fresh start)
    c.execute('DROP TABLE IF EXISTS bills')
    
    # Create table with correct schema
    c.execute('''
    CREATE TABLE IF NOT EXISTS bills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT,
        card_id TEXT,
        due_date TEXT,
        minimum_due REAL,
        balance_outstanding REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("Database initialized successfully")

def query_ollama(text: str, model: str = 'nuextract', retry_with_smaller_models: bool = True) -> Optional[str]:
    """Query Ollama model with improved error handling and timeout."""
    # Truncate text if it's too long to avoid timeouts
    if len(text) > 3000:
        text = text[:3000] + "..."
        logger.warning("Text truncated to 3000 characters to avoid timeout")
    
    # List of models to try in order of preference
    models_to_try = [model]
    if retry_with_smaller_models and model not in ['llama2:7b', 'tinyllama', 'phi3:mini', 'qwen2.5:0.5b']:
        models_to_try.extend(['phi3:mini', 'qwen2.5:0.5b', 'tinyllama'])
    
    # Simple, short prompt for all models
    prompt = (
        "Extract from this credit card bill as JSON:\n"
        "- card_id: last 4 digits of card number\n"
        "- latest_due_date: due date (DD.MM.YY format)\n"
        "- latest_min_amount: minimum payment (number)\n"
        "- latest_total_amount: total balance (number)\n\n"
        "Return only: {\"card_id\": \"1234\", \"latest_due_date\": \"15.08.25\", \"latest_min_amount\": 150.0, \"latest_total_amount\": 2500.0}\n\n"
        "Text:\n" + text
    )
    
    for current_model in models_to_try:
        try:
            logger.info(f"Trying model: {current_model}")
            
            # Check if model is available
            check_result = subprocess.run(
                ['ollama', 'list'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if current_model not in check_result.stdout:
                logger.warning(f"Model {current_model} not available, skipping")
                continue

            # Run the model with shorter timeout
            result = subprocess.run(
                ['ollama', 'run', current_model],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=30  # Very short timeout
            )
            
            if result.returncode != 0:
                logger.warning(f"Model {current_model} failed with return code {result.returncode}")
                continue
                
            output = result.stdout.strip()
            if output:
                logger.info(f"Successfully got response from {current_model}")
                return output
            else:
                logger.warning(f"Empty response from {current_model}")
                continue
                
        except subprocess.TimeoutExpired:
            logger.warning(f"Model {current_model} timed out, trying next model")
            continue
        except Exception as e:
            logger.warning(f"Error with model {current_model}: {e}")
            continue
    
    logger.error(f"All models failed for text extraction")
    return None

def clean_json_response(response: str) -> str:
    """Clean and extract JSON from model response."""
    if not response:
        return ""
    
    # Remove any text before the first {
    start_idx = response.find('{')
    if start_idx == -1:
        return ""
    
    # Find the matching closing brace
    brace_count = 0
    end_idx = -1
    for i in range(start_idx, len(response)):
        if response[i] == '{':
            brace_count += 1
        elif response[i] == '}':
            brace_count -= 1
            if brace_count == 0:
                end_idx = i
                break
    
    if end_idx == -1:
        return ""
    
    json_str = response[start_idx:end_idx + 1]
    
    # Fix common JSON issues with simpler regex patterns
    # Remove any trailing commas before closing braces
    json_str = re.sub(r',\s*}', '}', json_str)
    json_str = re.sub(r',\s*]', ']', json_str)
    
    # Fix unescaped quotes in values - use a simpler pattern
    json_str = re.sub(r':\s*"([^"]*)"([^,}]*)', r': "\1\2"', json_str)
    
    return json_str

def extract_with_regex(text: str) -> Dict[str, Any]:
    """Fallback extraction using regex patterns."""
    data = {
        'card_id': 'unknown',
        'latest_due_date': 'unknown',
        'latest_min_amount': 0.0,
        'latest_total_amount': 0.0
    }
    
    # Try to extract card number (last 4 digits)
    card_patterns = [
        r'\b(\d{4})\s*(?:xxxx|XXXX|\*{4}|\*{12})',
        r'ending in (\d{4})',
        r'ending (\d{4})',
        r'xxxx\s*(\d{4})',
        r'\*{4,}\s*(\d{4})',
        r'card.*?(\d{4})',
    ]
    
    for pattern in card_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            data['card_id'] = match.group(1)
            break
    
    # Try to extract amounts
    amount_patterns = [
        r'(?:minimum due|minimum payment|min due|minimum).*?(\d+\.?\d*)',
        r'(\d+\.?\d*)\s*(?:minimum|min\s*due)',
        r'due.*?(\d+\.?\d*)',
        r'balance.*?(\d+\.?\d*)',
        r'total.*?(\d+\.?\d*)',
        r'outstanding.*?(\d+\.?\d*)',
    ]
    
    amounts = []
    for pattern in amount_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        amounts.extend([float(match) for match in matches if match])
    
    if amounts:
        amounts = sorted(amounts)
        if len(amounts) >= 2:
            data['latest_min_amount'] = amounts[0]
            data['latest_total_amount'] = amounts[-1]
        else:
            data['latest_total_amount'] = amounts[0]
    
    # Try to extract date
    date_patterns = [
        r'due date.*?(\d{1,2}[./]\d{1,2}[./]\d{2,4})',
        r'(\d{1,2}[./]\d{1,2}[./]\d{2,4}).*?due',
        r'payment due.*?(\d{1,2}[./]\d{1,2}[./]\d{2,4})',
        r'(\d{1,2}[./]\d{1,2}[./]\d{2,4})',
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            date_str = match.group(1)
            # Try to normalize date format
            date_match = re.search(r'(\d{1,2})[./](\d{1,2})[./](\d{2,4})', date_str)
            if date_match:
                day, month, year = date_match.groups()
                if len(year) == 4:
                    year = year[-2:]
                data['latest_due_date'] = f"{day.zfill(2)}.{month.zfill(2)}.{year}"
                break
    
    return data

def validate_extracted_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and clean extracted data."""
    required_keys = ["card_id", "latest_due_date", "latest_min_amount", "latest_total_amount"]
    
    # Ensure all required keys exist
    for key in required_keys:
        if key not in data:
            if 'amount' in key:
                data[key] = 0.0
            else:
                data[key] = 'unknown'
    
    # Clean and validate data
    try:
        # Ensure amounts are numbers
        data['latest_min_amount'] = float(data['latest_min_amount']) if data['latest_min_amount'] != 'unknown' else 0.0
        data['latest_total_amount'] = float(data['latest_total_amount']) if data['latest_total_amount'] != 'unknown' else 0.0
        
        # Clean card_id (remove any non-alphanumeric characters except the last 4 digits)
        card_id = str(data['card_id'])
        if card_id != 'unknown':
            # Extract last 4 digits if it's a full card number
            digits = re.findall(r'\d', card_id)
            if len(digits) >= 4:
                data['card_id'] = ''.join(digits[-4:])
        
        # Validate date format (try to fix common issues)
        date_str = str(data['latest_due_date'])
        if date_str != 'unknown':
            # Try to extract date pattern
            date_match = re.search(r'(\d{1,2})[./](\d{1,2})[./](\d{2,4})', date_str)
            if date_match:
                day, month, year = date_match.groups()
                if len(year) == 4:
                    year = year[-2:]  # Convert to 2-digit year
                data['latest_due_date'] = f"{day.zfill(2)}.{month.zfill(2)}.{year}"
        
    except (ValueError, TypeError) as e:
        logger.warning(f"Data validation/cleaning error: {e}")
        # Set default values for invalid data
        if 'latest_min_amount' not in data or not isinstance(data['latest_min_amount'], (int, float)):
            data['latest_min_amount'] = 0.0
        if 'latest_total_amount' not in data or not isinstance(data['latest_total_amount'], (int, float)):
            data['latest_total_amount'] = 0.0
    
    return data

def parse_and_store_bills(text_dir: str, model: str = 'nuextract'):
    """Parse bills from text directory and store in database."""
    if not os.path.exists(text_dir):
        logger.error(f"Directory {text_dir} does not exist")
        return
    
    # Initialize database
    init_database()
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Get list of text files
    text_files = [f for f in os.listdir(text_dir) if f.endswith('.txt')]
    if not text_files:
        logger.warning(f"No .txt files found in {text_dir}")
        return
    
    logger.info(f"Found {len(text_files)} text files to process")
    
    successful_inserts = 0
    failed_inserts = 0
    
    for filename in text_files:
        logger.info(f"Processing {filename}...")
        
        file_path = os.path.join(text_dir, filename)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                bill_text = f.read()
        except Exception as e:
            logger.error(f"Error reading file {filename}: {e}")
            failed_inserts += 1
            continue
        
        if not bill_text.strip():
            logger.warning(f"Empty file: {filename}")
            failed_inserts += 1
            continue
        
        # Try LLM extraction first
        response = query_ollama(bill_text, model=model)
        
        if response:
            # Clean and parse JSON
            cleaned_response = clean_json_response(response)
            if cleaned_response:
                try:
                    data = json.loads(cleaned_response)
                    logger.info(f"Successfully extracted with LLM for {filename}")
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON parsing error for {filename}, trying regex fallback: {e}")
                    data = extract_with_regex(bill_text)
                    logger.info(f"Used regex fallback for {filename}")
            else:
                logger.warning(f"Could not extract JSON from LLM response for {filename}, trying regex fallback")
                data = extract_with_regex(bill_text)
                logger.info(f"Used regex fallback for {filename}")
        else:
            logger.warning(f"No response from LLM for {filename}, trying regex fallback")
            data = extract_with_regex(bill_text)
            logger.info(f"Used regex fallback for {filename}")
        
        # Validate and clean data
        data = validate_extracted_data(data)
        
        # Insert into database
        try:
            c.execute('''
                INSERT INTO bills (filename, card_id, due_date, minimum_due, balance_outstanding)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                filename,
                data['card_id'],
                data['latest_due_date'],
                data['latest_min_amount'],
                data['latest_total_amount']
            ))
            conn.commit()
            successful_inserts += 1
            logger.info(f"Successfully processed {filename}")
            
        except Exception as e:
            logger.error(f"Database error for {filename}: {e}")
            failed_inserts += 1
    
    # Print summary
    print(f"\n=== Processing Summary ===")
    print(f"Successfully processed: {successful_inserts}")
    print(f"Failed to process: {failed_inserts}")
    print(f"Total files: {len(text_files)}")
    
    # Show all entries in the database
    print("\n=== All entries in the bills database ===")
    c.execute("SELECT id, filename, card_id, due_date, minimum_due, balance_outstanding FROM bills ORDER BY id")
    rows = c.fetchall()
    
    if rows:
        print(f"{'ID':<3} {'Filename':<30} {'Card ID':<8} {'Due Date':<10} {'Min Due':<10} {'Balance':<10}")
        print("-" * 80)
        for row in rows:
            print(f"{row[0]:<3} {row[1]:<30} {row[2]:<8} {row[3]:<10} {row[4]:<10.2f} {row[5]:<10.2f}")
    else:
        print("No entries found in the database.")
    
    conn.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        model = sys.argv[2] if len(sys.argv) > 2 else 'nuextract'
        parse_and_store_bills(sys.argv[1], model)
    else:
        print("Usage: python3 ollama_parse_txt.py <text_dir> [model_name]")
        print("Recommended models for speed:")
        print("- nuextract (optimized for extraction)")
        print("- phi3:mini (small, fast)")
        print("- qwen2.5:0.5b (very fast)")
        print("- tinyllama (fastest, basic)")
        print("Example: python3 ollama_parse_txt.py assets/output nuextrace")
        print("Note: Script will try smaller models if the primary one fails/timeouts")
        print("Includes regex fallback if all LLM models fail")