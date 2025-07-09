"""
Data models for the Enhanced Gmail PDF Unlocker
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime

@dataclass
class PasswordCandidate:
    """Represents a password candidate with metadata"""
    password: str
    confidence: float
    source: str
    reasoning: str
    tested: bool = False
    works: bool = False
    created_date: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_date is None:
            self.created_date = datetime.now()

@dataclass
class EmailData:
    """Represents processed email data"""
    id: str
    subject: str
    sender: str
    date: str
    snippet: str
    password_hints: List[str]
    password_rules: List[str]
    attachments: List[str]
    email_body: str
    timestamp: int
    processed_date: Optional[datetime] = None
    
    def __post_init__(self):
        if self.processed_date is None:
            self.processed_date = datetime.now()

@dataclass
class PersonalData:
    """Represents personal data for password generation"""
    data_type: str
    data_value: str
    description: str
    created_date: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_date is None:
            self.created_date = datetime.now()

@dataclass
class BankContext:
    """Represents bank-specific context extracted from email"""
    bank: str
    account_numbers: List[str]
    card_numbers: List[str]
    dates: List[str]
    amounts: List[str]
    
    def __post_init__(self):
        # Remove duplicates
        self.account_numbers = list(set(self.account_numbers))
        self.card_numbers = list(set(self.card_numbers))
        self.dates = list(set(self.dates))
        self.amounts = list(set(self.amounts))

@dataclass
class UnlockResult:
    """Represents the result of a PDF unlock attempt"""
    pdf_path: str
    success: bool
    password_used: Optional[str] = None
    unlocked_path: Optional[str] = None
    error_message: Optional[str] = None
    attempts_count: int = 0
    
    def __str__(self):
        if self.success:
            return f"✅ Successfully unlocked {self.pdf_path} with password '{self.password_used}'"
        else:
            return f"❌ Failed to unlock {self.pdf_path}: {self.error_message}"

@dataclass
class ProcessingStats:
    """Represents statistics for processing results"""
    total_emails: int = 0
    new_emails: int = 0
    total_pdfs: int = 0
    unlocked_pdfs: int = 0
    failed_pdfs: int = 0
    password_candidates_generated: int = 0
    
    @property
    def success_rate(self) -> float:
        if self.total_pdfs == 0:
            return 0.0
        return (self.unlocked_pdfs / self.total_pdfs) * 100
    
    def __str__(self):
        return f"""
📊 Processing Statistics:
- Total emails processed: {self.total_emails}
- New emails found: {self.new_emails}
- Total PDFs: {self.total_pdfs}
- Successfully unlocked: {self.unlocked_pdfs}
- Failed to unlock: {self.failed_pdfs}
- Success rate: {self.success_rate:.1f}%
- Password candidates generated: {self.password_candidates_generated}
"""
