"""
Database management for the Enhanced Gmail PDF Unlocker
"""

import sqlite3
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from contextlib import contextmanager

from models import EmailData, PersonalData, PasswordCandidate
from config import DATABASE_PATH

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages database operations for the application"""
    
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database tables"""
        with self.get_connection() as conn:
            c = conn.cursor()
            
            # Emails table
            c.execute('''
                CREATE TABLE IF NOT EXISTS emails (
                    id TEXT PRIMARY KEY,
                    subject TEXT,
                    sender TEXT,
                    date TEXT,
                    snippet TEXT,
                    password_hints TEXT,
                    password_rules TEXT,
                    attachments TEXT,
                    timestamp INTEGER,
                    email_body TEXT,
                    processed_date TEXT
                )
            ''')
            
            # Personal data table
            c.execute('''
                CREATE TABLE IF NOT EXISTS personal_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data_type TEXT,
                    data_value TEXT,
                    description TEXT,
                    created_date TEXT,
                    UNIQUE(data_type, data_value)
                )
            ''')
            
            # Password candidates table
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
            
            # Unlock results table
            c.execute('''
                CREATE TABLE IF NOT EXISTS unlock_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pdf_path TEXT,
                    email_id TEXT,
                    success BOOLEAN,
                    password_used TEXT,
                    unlocked_path TEXT,
                    error_message TEXT,
                    attempts_count INTEGER,
                    unlock_date TEXT,
                    FOREIGN KEY (email_id) REFERENCES emails (id)
                )
            ''')
            
            conn.commit()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()
    
    def add_personal_data(self, data_type: str, data_value: str, description: str = ""):
        """Add personal data that might be used in passwords"""
        with self.get_connection() as conn:
            c = conn.cursor()
            try:
                c.execute('''
                    INSERT OR REPLACE INTO personal_data (data_type, data_value, description, created_date)
                    VALUES (?, ?, ?, ?)
                ''', (data_type, data_value, description, datetime.now().isoformat()))
                conn.commit()
                logger.info(f"Added personal data: {data_type} = {data_value}")
            except Exception as e:
                logger.error(f"Error adding personal data: {e}")
                conn.rollback()
    
    def get_personal_data(self) -> List[Tuple[str, str, str]]:
        """Retrieve all personal data for password generation"""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT data_type, data_value, description FROM personal_data')
            return c.fetchall()
    
    def get_personal_data_organized(self) -> Dict[str, List[str]]:
        """Retrieve personal data organized by type"""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT data_type, data_value, description FROM personal_data')
            rows = c.fetchall()
        
        data = {}
        for data_type, data_value, description in rows:
            if data_type not in data:
                data[data_type] = []
            data[data_type].append(data_value)
        
        return data
    
    def get_latest_email_timestamp(self) -> Optional[int]:
        """Get the timestamp of the latest processed email"""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT MAX(timestamp) FROM emails')
            result = c.fetchone()
            return result[0] if result and result[0] else None
    
    def is_email_processed(self, msg_id: str) -> bool:
        """Check if an email has already been processed"""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT id FROM emails WHERE id = ?', (msg_id,))
            return c.fetchone() is not None
    
    def store_email_data(self, email_data: EmailData):
        """Store email metadata in the database"""
        with self.get_connection() as conn:
            c = conn.cursor()
            try:
                c.execute('''
                    INSERT OR REPLACE INTO emails 
                    (id, subject, sender, date, snippet, password_hints, password_rules, 
                     attachments, timestamp, email_body, processed_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    email_data.id,
                    email_data.subject,
                    email_data.sender,
                    email_data.date,
                    email_data.snippet,
                    json.dumps(email_data.password_hints),
                    json.dumps(email_data.password_rules),
                    json.dumps(email_data.attachments),
                    email_data.timestamp,
                    email_data.email_body,
                    email_data.processed_date.isoformat()
                ))
                conn.commit()
                logger.info(f"Stored email data: {email_data.subject}")
            except Exception as e:
                logger.error(f"Error storing email data: {e}")
                conn.rollback()
    
    def get_email_data(self, email_id: str) -> Optional[EmailData]:
        """Retrieve email data by ID"""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('''
                SELECT id, subject, sender, date, snippet, password_hints, password_rules, 
                       attachments, email_body, timestamp, processed_date
                FROM emails WHERE id = ?
            ''', (email_id,))
            
            row = c.fetchone()
            if not row:
                return None
            
            return EmailData(
                id=row[0],
                subject=row[1],
                sender=row[2],
                date=row[3],
                snippet=row[4],
                password_hints=json.loads(row[5]) if row[5] else [],
                password_rules=json.loads(row[6]) if row[6] else [],
                attachments=json.loads(row[7]) if row[7] else [],
                email_body=row[8],
                timestamp=row[9],
                processed_date=datetime.fromisoformat(row[10]) if row[10] else None
            )
    
    def get_emails_with_attachments(self) -> List[EmailData]:
        """Get all emails that have PDF attachments"""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('''
                SELECT id, subject, sender, date, snippet, password_hints, password_rules, 
                       attachments, email_body, timestamp, processed_date
                FROM emails 
                WHERE attachments IS NOT NULL AND attachments != "[]"
            ''')
            
            emails = []
            for row in c.fetchall():
                emails.append(EmailData(
                    id=row[0],
                    subject=row[1],
                    sender=row[2],
                    date=row[3],
                    snippet=row[4],
                    password_hints=json.loads(row[5]) if row[5] else [],
                    password_rules=json.loads(row[6]) if row[6] else [],
                    attachments=json.loads(row[7]) if row[7] else [],
                    email_body=row[8],
                    timestamp=row[9],
                    processed_date=datetime.fromisoformat(row[10]) if row[10] else None
                ))
            
            return emails
    
    def save_password_candidates(self, email_id: str, candidates: List[PasswordCandidate]):
        """Save password candidates to database"""
        with self.get_connection() as conn:
            c = conn.cursor()
            
            # Clear existing candidates for this email
            c.execute('DELETE FROM password_candidates WHERE email_id = ?', (email_id,))
            
            # Insert new candidates
            for candidate in candidates:
                c.execute('''
                    INSERT INTO password_candidates 
                    (email_id, password, confidence, source, reasoning, tested, works, created_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    email_id,
                    candidate.password,
                    candidate.confidence,
                    candidate.source,
                    candidate.reasoning,
                    candidate.tested,
                    candidate.works,
                    candidate.created_date.isoformat()
                ))
            
            conn.commit()
    
    def get_password_candidates(self, email_id: str) -> List[PasswordCandidate]:
        """Get password candidates for an email"""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('''
                SELECT password, confidence, source, reasoning, tested, works, created_date
                FROM password_candidates 
                WHERE email_id = ?
                ORDER BY confidence DESC, created_date DESC
            ''', (email_id,))
            
            candidates = []
            for row in c.fetchall():
                candidates.append(PasswordCandidate(
                    password=row[0],
                    confidence=row[1],
                    source=row[2],
                    reasoning=row[3],
                    tested=bool(row[4]),
                    works=bool(row[5]),
                    created_date=datetime.fromisoformat(row[6]) if row[6] else None
                ))
            
            return candidates
    
    def mark_password_result(self, email_id: str, password: str, works: bool):
        """Mark password test result in database"""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('''
                UPDATE password_candidates 
                SET tested = 1, works = ? 
                WHERE email_id = ? AND password = ?
            ''', (works, email_id, password))
            conn.commit()
    
    def save_unlock_result(self, email_id: str, pdf_path: str, success: bool, 
                          password_used: str = None, unlocked_path: str = None,
                          error_message: str = None, attempts_count: int = 0):
        """Save PDF unlock result"""
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute('''
                INSERT INTO unlock_results 
                (pdf_path, email_id, success, password_used, unlocked_path, 
                 error_message, attempts_count, unlock_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                pdf_path, email_id, success, password_used, unlocked_path,
                error_message, attempts_count, datetime.now().isoformat()
            ))
            conn.commit()
    
    def get_unlock_statistics(self) -> Dict[str, int]:
        """Get statistics about unlock attempts"""
        with self.get_connection() as conn:
            c = conn.cursor()
            
            # Total attempts
            c.execute('SELECT COUNT(*) FROM unlock_results')
            total_attempts = c.fetchone()[0]
            
            # Successful unlocks
            c.execute('SELECT COUNT(*) FROM unlock_results WHERE success = 1')
            successful_unlocks = c.fetchone()[0]
            
            # Failed attempts
            c.execute('SELECT COUNT(*) FROM unlock_results WHERE success = 0')
            failed_attempts = c.fetchone()[0]
            
            return {
                'total_attempts': total_attempts,
                'successful_unlocks': successful_unlocks,
                'failed_attempts': failed_attempts,
                'success_rate': (successful_unlocks / total_attempts * 100) if total_attempts > 0 else 0
            }
    
    def cleanup_old_data(self, days_old: int = 30):
        """Clean up old data from the database"""
        cutoff_date = datetime.now().replace(days=days_old)
        
        with self.get_connection() as conn:
            c = conn.cursor()
            
            # Clean up old password candidates
            c.execute('''
                DELETE FROM password_candidates 
                WHERE created_date < ? AND tested = 0
            ''', (cutoff_date.isoformat(),))
            
            # Clean up old unlock results
            c.execute('''
                DELETE FROM unlock_results 
                WHERE unlock_date < ?
            ''', (cutoff_date.isoformat(),))
            
            conn.commit()
            logger.info(f"Cleaned up data older than {days_old} days")
