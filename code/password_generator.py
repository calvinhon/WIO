import sqlite3
import re
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import requests
import subprocess
import os
from dataclasses import dataclass
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PasswordCandidate:
    password: str
    confidence: float
    source: str
    reasoning: str

class LocalLLMManager:
    """Manages different local LLM backends"""
    
    def __init__(self, backend="ollama", model="llama3.1"):
        self.backend = backend
        self.model = model
        self.base_url = "http://localhost:11434"  # Default Ollama URL
        
    def is_available(self) -> bool:
        """Check if the LLM service is available"""
        try:
            if self.backend == "ollama":
                response = requests.get(f"{self.base_url}/api/tags", timeout=5)
                return response.status_code == 200
            elif self.backend == "lmstudio":
                response = requests.get("http://localhost:1234/v1/models", timeout=5)
                return response.status_code == 200
            elif self.backend == "llamacpp":
                response = requests.get("http://localhost:8080/health", timeout=5)
                return response.status_code == 200
        except:
            return False
        return False
    
    def generate_response(self, prompt: str, max_tokens: int = 500) -> str:
        """Generate response using the configured LLM backend"""
        try:
            if self.backend == "ollama":
                return self._ollama_generate(prompt, max_tokens)
            elif self.backend == "lmstudio":
                return self._lmstudio_generate(prompt, max_tokens)
            elif self.backend == "llamacpp":
                return self._llamacpp_generate(prompt, max_tokens)
            else:
                raise ValueError(f"Unsupported backend: {self.backend}")
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return ""
    
    def _ollama_generate(self, prompt: str, max_tokens: int) -> str:
        """Generate using Ollama API"""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": 0.1
            }
        }
        
        response = requests.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json().get("response", "")
        else:
            raise Exception(f"Ollama API error: {response.status_code}")
    
    def _lmstudio_generate(self, prompt: str, max_tokens: int) -> str:
        """Generate using LM Studio API"""
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.1
        }
        
        response = requests.post(
            "http://localhost:1234/v1/chat/completions",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            raise Exception(f"LM Studio API error: {response.status_code}")
    
    def _llamacpp_generate(self, prompt: str, max_tokens: int) -> str:
        """Generate using llama.cpp server"""
        payload = {
            "prompt": prompt,
            "n_predict": max_tokens,
            "temperature": 0.1,
            "stop": ["</s>", "\n\n"]
        }
        
        response = requests.post(
            "http://localhost:8080/completion",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json().get("content", "")
        else:
            raise Exception(f"llama.cpp server error: {response.status_code}")

class PasswordGeneratorLLM:
    """Enhanced password generator using local LLMs"""
    
    def __init__(self, db_path: str = 'email_data.db'):
        self.db_path = db_path
        self.llm_manager = None
        self._setup_llm()
        
    def _setup_llm(self):
        """Setup the best available local LLM"""
        backends = [
            ("ollama", "llama3.1"),
            ("lmstudio", "llama-3.1-8b-instruct"),
            ("llamacpp", "llama-3.1-8b-instruct")
        ]
        
        for backend, model in backends:
            try:
                llm = LocalLLMManager(backend, model)
                if llm.is_available():
                    self.llm_manager = llm
                    logger.info(f"Using {backend} with model {model}")
                    return
            except Exception as e:
                logger.warning(f"Failed to setup {backend}: {e}")
        
        logger.warning("No local LLM available, falling back to rule-based generation")
        self.llm_manager = None
    
    def get_personal_data(self) -> Dict[str, List[str]]:
        """Retrieve personal data organized by type"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT data_type, data_value, description FROM personal_data')
        rows = c.fetchall()
        conn.close()
        
        data = {}
        for data_type, data_value, description in rows:
            if data_type not in data:
                data[data_type] = []
            data[data_type].append(data_value)
        
        return data
    
    def extract_bank_context(self, email_body: str, sender: str) -> Dict[str, str]:
        """Extract bank-specific context from email"""
        bank_patterns = {
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
            'sc': r'standard chartered'
        }
        
        context = {
            'bank': 'unknown',
            'account_numbers': [],
            'card_numbers': [],
            'dates': [],
            'amounts': []
        }
        
        # Identify bank
        sender_lower = sender.lower()
        email_lower = email_body.lower()
        
        for bank, pattern in bank_patterns.items():
            if re.search(pattern, sender_lower) or re.search(pattern, email_lower):
                context['bank'] = bank
                break
        
        # Extract account numbers (masked)
        account_patterns = [
            r'account.*?(\d{4,6})',
            r'a/c.*?(\d{4,6})',
            r'account ending.*?(\d{4,6})'
        ]
        
        for pattern in account_patterns:
            matches = re.finditer(pattern, email_body, re.IGNORECASE)
            context['account_numbers'].extend([m.group(1) for m in matches])
        
        # Extract card numbers (last 4 digits)
        card_patterns = [
            r'card.*?(\d{4})',
            r'credit card.*?(\d{4})',
            r'ending.*?(\d{4})'
        ]
        
        for pattern in card_patterns:
            matches = re.finditer(pattern, email_body, re.IGNORECASE)
            context['card_numbers'].extend([m.group(1) for m in matches])
        
        # Extract dates
        date_patterns = [
            r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b',
            r'\b(\d{2,4}[/-]\d{1,2}[/-]\d{1,2})\b'
        ]
        
        for pattern in date_patterns:
            matches = re.finditer(pattern, email_body)
            context['dates'].extend([m.group(1) for m in matches])
        
        return context
    
    def generate_llm_prompt(self, email_body: str, password_rules: List[str], 
                          password_hints: List[str], personal_data: Dict[str, List[str]], 
                          bank_context: Dict[str, str]) -> str:
        """Generate a comprehensive prompt for the LLM"""
        
        prompt = f"""You are an expert password analyst. Your task is to analyze bank statement emails and generate the most likely PDF password based on the provided information.

EMAIL CONTENT:
{email_body[:1000]}...

PASSWORD RULES FOUND:
{chr(10).join(password_rules) if password_rules else 'None specified'}

PASSWORD HINTS FOUND:
{', '.join(password_hints) if password_hints else 'None found'}

PERSONAL DATA AVAILABLE:
"""
        
        for data_type, values in personal_data.items():
            prompt += f"- {data_type}: {', '.join(values[:3])}\n"
        
        prompt += f"""
BANK CONTEXT:
- Bank: {bank_context['bank']}
- Account Numbers: {', '.join(bank_context['account_numbers'])}
- Card Numbers: {', '.join(bank_context['card_numbers'])}
- Dates Found: {', '.join(bank_context['dates'][:5])}

COMMON BANK PASSWORD PATTERNS:
1. Last 4 digits of card/account number
2. Date of birth (DDMMYYYY, MMDDYYYY)
3. Mobile number last 4 digits
4. First name + last 4 digits of card
5. DDMMYYYY format dates
6. Account number variations

TASK: Generate the 5 most likely passwords based on this analysis. For each password, provide:
1. The password itself
2. Confidence level (1-10)
3. Reasoning for this choice

Format your response as JSON:
{{
  "passwords": [
    {{
      "password": "12345678",
      "confidence": 8,
      "reasoning": "Based on rule mentioning last 4 digits of card number (5678) combined with birth date (1234)"
    }}
  ]
}}

RESPOND ONLY WITH THE JSON, NO OTHER TEXT.
"""
        
        return prompt
    
    def parse_llm_response(self, response: str) -> List[PasswordCandidate]:
        """Parse LLM response into password candidates"""
        candidates = []
        
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                data = json.loads(json_str)
                
                for pwd_data in data.get('passwords', []):
                    candidate = PasswordCandidate(
                        password=pwd_data.get('password', ''),
                        confidence=float(pwd_data.get('confidence', 0)),
                        source='llm',
                        reasoning=pwd_data.get('reasoning', '')
                    )
                    candidates.append(candidate)
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
        
        return candidates
    
    def generate_rule_based_passwords(self, email_body: str, password_rules: List[str], 
                                    password_hints: List[str], personal_data: Dict[str, List[str]], 
                                    bank_context: Dict[str, str]) -> List[PasswordCandidate]:
        """Generate password candidates using rule-based approach"""
        candidates = []
        
        # Direct hints
        for hint in password_hints:
            if len(hint) >= 4:
                candidates.append(PasswordCandidate(
                    password=hint,
                    confidence=9.0,
                    source='direct_hint',
                    reasoning=f'Found direct password hint: {hint}'
                ))
        
        # Personal data combinations
        if 'birth_date' in personal_data:
            for date in personal_data['birth_date']:
                # Different date formats
                date_clean = re.sub(r'[/-]', '', date)
                candidates.append(PasswordCandidate(
                    password=date_clean,
                    confidence=7.0,
                    source='birth_date',
                    reasoning=f'Birth date format: {date_clean}'
                ))
        
        # Card/Account number combinations
        for card_num in bank_context['card_numbers']:
            candidates.append(PasswordCandidate(
                password=card_num,
                confidence=8.0,
                source='card_number',
                reasoning=f'Last 4 digits of card: {card_num}'
            ))
        
        for acc_num in bank_context['account_numbers']:
            candidates.append(PasswordCandidate(
                password=acc_num,
                confidence=7.0,
                source='account_number',
                reasoning=f'Account number digits: {acc_num}'
            ))
        
        # Date combinations from email
        for date in bank_context['dates']:
            date_clean = re.sub(r'[/-]', '', date)
            if len(date_clean) >= 6:
                candidates.append(PasswordCandidate(
                    password=date_clean,
                    confidence=6.0,
                    source='email_date',
                    reasoning=f'Date from email: {date_clean}'
                ))
        
        # Mobile number combinations
        if 'mobile_number' in personal_data:
            for mobile in personal_data['mobile_number']:
                last_4 = mobile[-4:] if len(mobile) >= 4 else mobile
                candidates.append(PasswordCandidate(
                    password=last_4,
                    confidence=6.0,
                    source='mobile_number',
                    reasoning=f'Last 4 digits of mobile: {last_4}'
                ))
        
        # Name combinations
        if 'first_name' in personal_data and bank_context['card_numbers']:
            for name in personal_data['first_name']:
                for card in bank_context['card_numbers']:
                    combo = name.lower() + card
                    candidates.append(PasswordCandidate(
                        password=combo,
                        confidence=5.0,
                        source='name_card_combo',
                        reasoning=f'First name + card digits: {combo}'
                    ))
        
        return candidates
    
    def generate_passwords_for_email(self, email_id: str) -> List[PasswordCandidate]:
        """Generate password candidates for a specific email"""
        # Get email data
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            SELECT email_body, password_hints, password_rules, sender, subject 
            FROM emails WHERE id = ?
        ''', (email_id,))
        
        row = c.fetchone()
        conn.close()
        
        if not row:
            return []
        
        email_body, password_hints_str, password_rules_str, sender, subject = row
        
        # Parse stored data
        password_hints = json.loads(password_hints_str) if password_hints_str else []
        password_rules = json.loads(password_rules_str) if password_rules_str else []
        
        # Get personal data and bank context
        personal_data = self.get_personal_data()
        bank_context = self.extract_bank_context(email_body, sender)
        
        candidates = []
        
        # Try LLM generation first
        if self.llm_manager:
            try:
                prompt = self.generate_llm_prompt(
                    email_body, password_rules, password_hints, 
                    personal_data, bank_context
                )
                
                response = self.llm_manager.generate_response(prompt)
                llm_candidates = self.parse_llm_response(response)
                candidates.extend(llm_candidates)
                
                logger.info(f"Generated {len(llm_candidates)} candidates from LLM")
                
            except Exception as e:
                logger.error(f"LLM generation failed: {e}")
        
        # Always generate rule-based candidates as backup
        rule_candidates = self.generate_rule_based_passwords(
            email_body, password_rules, password_hints, 
            personal_data, bank_context
        )
        candidates.extend(rule_candidates)
        
        # Sort by confidence and remove duplicates
        seen = set()
        unique_candidates = []
        for candidate in sorted(candidates, key=lambda x: x.confidence, reverse=True):
            if candidate.password not in seen:
                seen.add(candidate.password)
                unique_candidates.append(candidate)
        
        return unique_candidates[:20]  # Return top 20 candidates
    
    def save_password_candidates(self, email_id: str, candidates: List[PasswordCandidate]):
        """Save password candidates to database"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Create table if not exists
        c.execute('''
            CREATE TABLE IF NOT EXISTS password_candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_id TEXT,
                password TEXT,
                confidence REAL,
                source TEXT,
                reasoning TEXT,
                tested BOOLEAN DEFAULT 0,
                works BOOLEAN DEFAULT 0,
                created_date TEXT,
                FOREIGN KEY (email_id) REFERENCES emails (id)
            )
        ''')
        
        # Clear existing candidates for this email
        c.execute('DELETE FROM password_candidates WHERE email_id = ?', (email_id,))
        
        # Insert new candidates
        for candidate in candidates:
            c.execute('''
                INSERT INTO password_candidates 
                (email_id, password, confidence, source, reasoning, created_date)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                email_id, candidate.password, candidate.confidence, 
                candidate.source, candidate.reasoning, datetime.now().isoformat()
            ))
        
        conn.commit()
        conn.close()
    
    def test_password_on_pdf(self, pdf_path: str, password: str) -> bool:
        """Test if password works on PDF (requires PyPDF2 or similar)"""
        try:
            import PyPDF2
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                if reader.is_encrypted:
                    return reader.decrypt(password)
                return True  # PDF is not encrypted
        except Exception as e:
            logger.error(f"PDF test failed: {e}")
            return False
    
    def mark_password_result(self, email_id: str, password: str, works: bool):
        """Mark password test result in database"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            UPDATE password_candidates 
            SET tested = 1, works = ? 
            WHERE email_id = ? AND password = ?
        ''', (works, email_id, password))
        conn.commit()
        conn.close()
    
    def process_all_emails(self):
        """Process all emails in database for password generation"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT id, subject, sender FROM emails')
        emails = c.fetchall()
        conn.close()
        
        for email_id, subject, sender in emails:
            logger.info(f"Processing email: {subject[:50]}...")
            
            candidates = self.generate_passwords_for_email(email_id)
            if candidates:
                self.save_password_candidates(email_id, candidates)
                logger.info(f"Generated {len(candidates)} password candidates")
            else:
                logger.warning(f"No candidates generated for email {email_id}")

# Usage example and setup functions
def setup_personal_data(db_path: str = 'email_data.db'):
    """Setup personal data for password generation"""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Example personal data - replace with actual data
    personal_data = [
        ('first_name', 'John', 'First name'),
        ('last_name', 'Doe', 'Last name'),
        ('birth_date', '15/03/1990', 'Date of birth DD/MM/YYYY'),
        ('birth_date', '15031990', 'Date of birth DDMMYYYY'),
        ('mobile_number', '971501234567', 'Mobile number'),
        ('card_last_4', '1234', 'Credit card last 4 digits'),
        ('account_number', '987654', 'Account number last 6 digits'),
    ]
    
    for data_type, value, description in personal_data:
        c.execute('''
            INSERT OR REPLACE INTO personal_data (data_type, data_value, description, created_date)
            VALUES (?, ?, ?, ?)
        ''', (data_type, value, description, datetime.now().isoformat()))
    
    conn.commit()
    conn.close()
    print("Personal data setup complete")

def main():
    """Main function to demonstrate usage"""
    # Setup personal data first
    setup_personal_data()
    
    # Initialize password generator
    generator = PasswordGeneratorLLM()
    
    # Process all emails
    generator.process_all_emails()
    
    # Example: Get candidates for a specific email
    # candidates = generator.generate_passwords_for_email('some_email_id')
    # for candidate in candidates:
    #     print(f"Password: {candidate.password}, Confidence: {candidate.confidence}")
    #     print(f"Source: {candidate.source}, Reasoning: {candidate.reasoning}")
    #     print("---")

if __name__ == "__main__":
    main()