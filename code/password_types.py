"""
Password-related type definitions for backward compatibility
"""
from dataclasses import dataclass
from typing import List

@dataclass
class PasswordCandidate:
    """Password candidate for PDF unlocking"""
    password: str
    confidence: float
    source: str
    reasoning: str

@dataclass
class PasswordRule:
    """Password generation rule"""
    name: str
    pattern: str
    description: str
    enabled: bool = True