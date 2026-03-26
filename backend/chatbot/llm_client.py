"""
UniversalChatbot - LLM Client
OpenAI API integration for chat response generation
"""
import os
from typing import List, Dict, Any, Optional

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from chatbot.logger import get_logger


class LLMClient:
    """Client for OpenAI LLM API"""
    
    DEFAULT_MODEL = "gpt-3.5-turbo"
    DEFAULT_SYSTEM_PROMPT = """You are a helpful chat assistant. 
Keep responses concise and natural. 
Respond in the same language as the user's message.
Be helpful and friendly."""
    
    def __init__(self):
        self.logger = get_logger()
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.model = os.getenv('LLM_MODEL', self.DEFAULT_MODEL)
        
        if self.api_key and OpenAI:
            self.client = OpenAI(api_key=self.api_key)
            self.logger.info(f"LLM client initialized with model: {self.model}")
        else:
            self.client = None
            self.logger.warning("LLM client not initialized - missing API key or openai package")
    
    def generate_response(self, context: List[Dict[str, str]], 
                         system_prompt: Optional[str] = None) -> str:
        """Generate response based on conversation context"""
        
        if not self.client:
            return "[LLM not configured - check OPENAI_API_KEY]"
        
        try:
            messages = [{"role": "system", "content": system_prompt or self.DEFAULT_SYSTEM_PROMPT}]
            messages.extend(context)
            
            self.logger.debug(f"Sending {len(messages)} messages to LLM")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=500,
                temperature=0.7
            )
            
            text = response.choices[0].message.content.strip()
            
            self.logger.info(f"Generated response: {len(text)} chars")
            return text
            
        except Exception as e:
            self.logger.error(f"LLM API error: {e}")
            return "[Error generating response - check logs]"
    
    def is_configured(self) -> bool:
        """Check if LLM client is properly configured"""
        return self.client is not None
