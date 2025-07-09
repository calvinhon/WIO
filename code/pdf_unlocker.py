import sqlite3
import requests
import json
import re
import os
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict
import PyPDF2

@dataclass
class PasswordCandidate:
    password: str
    confidence: float
    reasoning: str

class OllamaLLM:
    def __init__(self, model="llama3.1:8b", host="http://localhost:11434"):
        self.model = model
        self.base_url = host

    def is_available(self) -> bool:
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return r.status_code == 200
        except:
            return False

    def generate_passwords(self, prompt: str) -> List[PasswordCandidate]:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 400
            }
        }
        r = requests.post(f"{self.base_url}/api/generate", json=payload)
        if r.status_code != 200:
            raise Exception("Ollama failed: " + str(r.text))
        
        try:
            text = r.json().get("response", "")
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if not match:
                return []
            parsed = json.loads(match.group(0))
            return [
                PasswordCandidate(p['password'], float(p['confidence']), p['reasoning'])
                for p in parsed.get("passwords", [])
            ]
        except Exception as e:
            print(f"Parsing failed: {e}")
            return []

class PasswordUnlocker:
    def __init__(self, db_path='email_data.db'):
        self.db_path = db_path
        self.llm = OllamaLLM()

    def get_email(self, email_id: str) -> Dict:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            SELECT subject, sender, email_body, password_hints, password_rules
            FROM emails WHERE id = ?
        ''', (email_id,))
        row = c.fetchone()
        conn.close()
        if not row:
            raise Exception("Email not found")
        return {
            "subject": row[0],
            "sender": row[1],
            "body": row[2],
            "hints": json.loads(row[3]) if row[3] else [],
            "rules": json.loads(row[4]) if row[4] else []
        }

    def get_personal_data(self) -> Dict[str, List[str]]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT data_type, data_value FROM personal_data')
        data = {}
        for data_type, value in c.fetchall():
            data.setdefault(data_type, []).append(value)
        conn.close()
        return data

    def create_prompt(self, email: Dict, personal_data: Dict) -> str:
        prompt = f"""You are an expert in understanding password rules in bank emails.
Your task is to predict likely PDF passwords using the email content, password hints, rules, and user data.

EMAIL SUBJECT: {email['subject']}
EMAIL BODY: {email['body'][:800]}...
SENDER: {email['sender']}
PASSWORD HINTS: {', '.join(email['hints']) if email['hints'] else 'None'}
PASSWORD RULES: {', '.join(email['rules']) if email['rules'] else 'None'}

PERSONAL DATA:
"""
        for k, v in personal_data.items():
            prompt += f"- {k}: {', '.join(v[:3])}\n"

        prompt += """
Give the top 5 most likely passwords in JSON format:
{
  "passwords": [
    {
      "password": "123456",
      "confidence": 9,
      "reasoning": "It's the last 4 digits of the card + birth year"
    }
  ]
}
Respond ONLY with JSON.
"""
        return prompt

    def test_pdf(self, pdf_path: str, password: str) -> bool:
        try:
            with open(pdf_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                if reader.is_encrypted:
                    return reader.decrypt(password)
                return True
        except Exception as e:
            print(f"Error testing PDF: {e}")
            return False
def unlock_pdf(self, email_id: str, pdf_path: str):
    if not os.path.exists(pdf_path):
        raise Exception("PDF not found")

    if not self.llm.is_available():
        raise Exception("Ollama model not available")

    email = self.get_email(email_id)
    personal_data = self.get_personal_data()
    prompt = self.create_prompt(email, personal_data)

    print("\n📨 Prompt sent to LLM:\n")
    print(prompt)

    candidates = self.llm.generate_passwords(prompt)

    print("\n🤖 Passwords returned by LLM:\n")
    for cand in candidates:
        print(f"- Password: {cand.password}")
        print(f"  Confidence: {cand.confidence}")
        print(f"  Reasoning: {cand.reasoning}")
        print("-----")

    for cand in candidates:
        print(f"🔐 Trying password: {cand.password} — Reason: {cand.reasoning}")
        if self.test_pdf(pdf_path, cand.password):
            print(f"✅ SUCCESS! Password: {cand.password}")
            return cand.password

    print("❌ Failed to unlock the PDF with LLM-generated passwords.")
    return None

    #def unlock_pdf(self, email_id: str, pdf_path: str):
    #    if not os.path.exists(pdf_path):
    #        raise Exception("PDF not found")

    #    if not self.llm.is_available():
    #        raise Exception("Ollama model not available")

    #    email = self.get_email(email_id)
    #    personal_data = self.get_personal_data()
    #    prompt = self.create_prompt(email, personal_data)
    #    candidates = self.llm.generate_passwords(prompt)

    #    for cand in candidates:
    #        print(f"Trying: {cand.password} — Reason: {cand.reasoning}")
    #        if self.test_pdf(pdf_path, cand.password):
    #            print(f"✅ SUCCESS! Password: {cand.password}")
    #            return cand.password
    #    print("❌ Failed to unlock the PDF with LLM-generated passwords.")
    #    return None
if __name__ == "__main__":
    email_id = "197ea038354ad840"  # Replace with a real ID from your database
    pdf_path = "downloads/EStatement_20250709_084140.pdf"  # Replace with your actual PDF path

    unlocker = PasswordUnlocker()
    unlocker.unlock_pdf(email_id, pdf_path)
