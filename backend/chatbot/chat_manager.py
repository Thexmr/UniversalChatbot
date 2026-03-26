"""
UniversalChatbot - Chat Manager
Manages chat sessions and conversation history
"""
from typing import Dict, List, Any
from collections import deque
import uuid
from datetime import datetime

from chatbot.logger import get_logger


class ChatManager:
    """Manages chat sessions and conversation history"""
    
    def __init__(self, max_history: int = 10):
        self.logger = get_logger()
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.max_history = max_history
    
    def get_or_create_session(self, session_id: str) -> Dict[str, Any]:
        """Get existing session or create new one"""
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                'id': session_id,
                'created_at': datetime.now().isoformat(),
                'messages': deque(maxlen=self.max_history),
                'platform': 'unknown'
            }
            self.logger.info(f"Created new session: {session_id}")
        return self.sessions[session_id]
    
    def add_messages(self, session_id: str, messages: List[Dict[str, Any]]):
        """Add messages to session history"""
        session = self.get_or_create_session(session_id)
        
        for msg in messages:
            session['messages'].append({
                'role': msg.get('role', 'user'),
                'content': msg.get('text', ''),
                'timestamp': msg.get('timestamp', datetime.now().isoformat())
            })
        
        self.logger.debug(f"Added {len(messages)} messages to session {session_id}")
    
    def get_context(self, session_id: str) -> List[Dict[str, str]]:
        """Get conversation context for LLM"""
        session = self.sessions.get(session_id)
        
        if not session:
            return []
        
        # Convert to LLM format
        context = []
        for msg in session['messages']:
            context.append({
                "role": msg['role'],
                "content": msg['content']
            })
        
        return context
    
    def close_session(self, session_id: str):
        """Close and cleanup session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            self.logger.info(f"Closed session: {session_id}")
