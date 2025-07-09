"""
Local LLM integration for the Enhanced Gmail PDF Unlocker
"""

import requests
import json
import logging
from typing import List, Dict, Optional
from models import PasswordCandidate, BankContext
from config import LLM_BACKENDS, LLM_URLS

logger = logging.getLogger(__name__)

class LocalLLMManager:
    """Manages different local LLM backends for password generation"""
    
    def __init__(self, backend: str = "ollama", model: str = "llama3.1"):
        self.backend = backend
        self.model = model
        self.base_url = LLM_URLS.get(backend, "http://localhost:11434")
        self.is_initialized = False
        
    def initialize(self) -> bool:
        """Initialize the LLM connection"""
        if self.is_available():
            self.is_initialized = True
            logger.info(f"Successfully initialized {self.backend} with model {self.model}")
            return True
        else:
            logger.warning(f"Failed to initialize {self.backend}")
            return False
    
    def is_available(self) -> bool:
        """Check if the LLM service is available"""
        try:
            if self.backend == "ollama":
                response = requests.get(f"{self.base_url}/api/tags", timeout=5)
                return response.status_code == 200
            elif self.backend == "lmstudio":
                response = requests.get(f"{self.base_url}/v1/models", timeout=5)
                return response.status_code == 200
            elif self.backend == "llamacpp":
                response = requests.get(f"{self.base_url}/health", timeout=5)
                return response.status_code == 200
        except Exception as e:
            logger.debug(f"LLM availability check failed: {e}")
            return False
        return False
    
    def generate_response(self, prompt: str, max_tokens: int = 500) -> str:
        """Generate response using the configured LLM backend"""
        if not self.is_initialized:
            raise RuntimeError("LLM not initialized")
        
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
            raise
    
    def _ollama_generate(self, prompt: str, max_tokens: int) -> str:
        """Generate using Ollama API"""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": 0.1,
                "top_k": 40,
                "top_p": 0.9
            }
        }
        
        response = requests.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            return response.json().get("response", "")
        else:
            raise Exception(f"Ollama API error: {response.status_code} - {response.text}")
    
    def _lmstudio_generate(self, prompt: str, max_tokens: int) -> str:
        """Generate using LM Studio API"""
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.1,
            "top_p": 0.9
        }
        
        response = requests.post(
            f"{self.base_url}/v1/chat/completions",
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            raise Exception(f"LM Studio API error: {response.status_code} - {response.text}")
    
    def _llamacpp_generate(self, prompt: str, max_tokens: int) -> str:
        """Generate using llama.cpp server"""
        payload = {
            "prompt": prompt,
            "n_predict": max_tokens,
            "temperature": 0.1,
            "top_k": 40,
            "top_p": 0.9,
            "stop": ["</s>", "\n\n", "USER:", "ASSISTANT:"]
        }
        
        response = requests.post(
            f"{self.base_url}/completion",
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            return response.json().get("content", "")
        else:
            raise Exception(f"llama.cpp server error: {response.status_code} - {response.text}")

class LLMPasswordGenerator:
    """Generates password candidates using LLM"""
    
    def __init__(self, llm_manager: LocalLLMManager):
        self.llm_manager = llm_manager
    
    def generate_prompt(self, email_body: str, password_rules: List[str], 
                       password_hints: List[str], personal_data: Dict[str, List[str]], 
                       bank_context: BankContext) -> str:
        """Generate a comprehensive prompt for the LLM"""
        
        # Truncate email body for context
        email_excerpt = email_body[:1500] + "..." if len(email_body) > 1500 else email_body
        
        prompt = f"""You are an expert password analyst specializing in bank statement PDF passwords. Your task is to analyze the provided information and generate the most likely passwords.

EMAIL CONTENT EXCERPT:
{email_excerpt}

PASSWORD RULES FOUND:
{chr(10).join(password_rules) if password_rules else 'None specified'}

PASSWORD HINTS FOUND:
{', '.join(password_hints) if password_hints else 'None found'}

PERSONAL DATA AVAILABLE:
"""
        
        for data_type, values in personal_data.items():
            if values:
                prompt += f"- {data_type}: {', '.join(values[:3])}\n"
        
        prompt += f"""
BANK CONTEXT:
- Bank: {