"""
Unit tests for ChatManager
Manages chat sessions and conversation history
"""
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime
from collections import deque

from chatbot.chat_manager import ChatManager


class TestChatManager(unittest.TestCase):
    """Test cases for ChatManager class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.manager = ChatManager(max_history=5)
    
    def test_initialization(self):
        """Test ChatManager initializes correctly"""
        manager = ChatManager(max_history=10)
        self.assertEqual(manager.max_history, 10)
        self.assertEqual(manager.sessions, {})
    
    def test_create_session(self):
        """Test creating a new session"""
        session = self.manager.get_or_create_session("test-uuid")
        
        self.assertIsNotNone(session)
        self.assertEqual(session['id'], "test-uuid")
        self.assertIn('created_at', session)
        self.assertIn('messages', session)
        self.assertIn('platform', session)
        self.assertIsInstance(session['messages'], deque)
    
    def test_get_existing_session(self):
        """Test retrieving an existing session"""
        # Create session
        session1 = self.manager.get_or_create_session("existing-uuid")
        session1['platform'] = 'web'
        
        # Get same session
        session2 = self.manager.get_or_create_session("existing-uuid")
        
        self.assertEqual(session1, session2)
        self.assertEqual(session2['platform'], 'web')
    
    def test_add_single_message(self):
        """Test adding a single message"""
        messages = [{"role": "user", "text": "Hello", "timestamp": "2025-01-01"}]
        self.manager.add_messages("test-uuid", messages)
        
        context = self.manager.get_context("test-uuid")
        self.assertEqual(len(context), 1)
        self.assertEqual(context[0]["role"], "user")
        self.assertEqual(context[0]["content"], "Hello")
    
    def test_add_multiple_messages(self):
        """Test adding multiple messages"""
        messages = [
            {"role": "user", "text": "Hello", "timestamp": "2025-01-01T10:00:00"},
            {"role": "assistant", "text": "Hi there!", "timestamp": "2025-01-01T10:01:00"},
            {"role": "user", "text": "How are you?", "timestamp": "2025-01-01T10:02:00"}
        ]
        self.manager.add_messages("test-uuid", messages)
        
        context = self.manager.get_context("test-uuid")
        self.assertEqual(len(context), 3)
        self.assertEqual(context[0]["content"], "Hello")
        self.assertEqual(context[1]["content"], "Hi there!")
        self.assertEqual(context[2]["content"], "How are you?")
    
    def test_add_messages_default_values(self):
        """Test adding messages with default values"""
        messages = [{"role": "user"}]  # Missing text and timestamp
        self.manager.add_messages("test-uuid", messages)
        
        context = self.manager.get_context("test-uuid")
        self.assertEqual(len(context), 1)
        self.assertEqual(context[0]["role"], "user")
        self.assertEqual(context[0]["content"], "")  # Default empty string
        self.assertIn('timestamp', self.manager.sessions["test-uuid"]['messages'][0])
    
    def test_max_history_limit(self):
        """Test that old messages are dropped when max_history is exceeded"""
        manager = ChatManager(max_history=3)
        
        # Add 5 messages
        for i in range(5):
            messages = [{"role": "user", "text": f"Message {i}"}]
            manager.add_messages("test-uuid", messages)
        
        context = manager.get_context("test-uuid")
        
        # Should only have the last 3 messages
        self.assertEqual(len(context), 3)
        self.assertEqual(context[0]["content"], "Message 2")
        self.assertEqual(context[1]["content"], "Message 3")
        self.assertEqual(context[2]["content"], "Message 4")
    
    def test_max_history_exact_limit(self):
        """Test behavior at exact max_history limit"""
        manager = ChatManager(max_history=3)
        
        # Add exactly 3 messages
        for i in range(3):
            messages = [{"role": "user", "text": f"Message {i}"}]
            manager.add_messages("test-uuid", messages)
        
        context = manager.get_context("test-uuid")
        
        # Should have all 3 messages
        self.assertEqual(len(context), 3)
        self.assertEqual(context[0]["content"], "Message 0")
        self.assertEqual(context[1]["content"], "Message 1")
        self.assertEqual(context[2]["content"], "Message 2")
    
    def test_get_context_empty_session(self):
        """Test getting context for empty session"""
        context = self.manager.get_context("non-existent-uuid")
        self.assertEqual(context, [])
    
    def test_get_context_format(self):
        """Test that context returns proper LLM format"""
        messages = [
            {"role": "user", "text": "Hello"},
            {"role": "assistant", "text": "Hi!"}
        ]
        self.manager.add_messages("test-uuid", messages)
        
        context = self.manager.get_context("test-uuid")
        
        # Should have role and content only (no timestamp)
        for msg in context:
            self.assertIn("role", msg)
            self.assertIn("content", msg)
            self.assertNotIn("timestamp", msg)
    
    def test_close_session(self):
        """Test closing and cleaning up a session"""
        # Create session
        self.manager.get_or_create_session("to-close-uuid")
        self.manager.add_messages("to-close-uuid", [{"role": "user", "text": "test"}])
        
        # Verify session exists
        self.assertIn("to-close-uuid", self.manager.sessions)
        
        # Close session
        self.manager.close_session("to-close-uuid")
        
        # Verify session is gone
        self.assertNotIn("to-close-uuid", self.manager.sessions)
    
    def test_close_nonexistent_session(self):
        """Test closing a session that doesn't exist"""
        # Should not raise an error
        self.manager.close_session("non-existent-uuid")
    
    def test_multiple_sessions(self):
        """Test managing multiple concurrent sessions"""
        session1_messages = [{"role": "user", "text": "Session 1 message"}]
        session2_messages = [{"role": "user", "text": "Session 2 message"}]
        
        self.manager.add_messages("uuid-1", session1_messages)
        self.manager.add_messages("uuid-2", session2_messages)
        
        context1 = self.manager.get_context("uuid-1")
        context2 = self.manager.get_context("uuid-2")
        
        self.assertEqual(len(context1), 1)
        self.assertEqual(len(context2), 1)
        self.assertEqual(context1[0]["content"], "Session 1 message")
        self.assertEqual(context2[0]["content"], "Session 2 message")
    
    def test_session_platform_default(self):
        """Test that sessions have default platform"""
        session = self.manager.get_or_create_session("test-uuid")
        self.assertEqual(session['platform'], 'unknown')
    
    def test_message_deque_len(self):
        """Test that messages is a deque with maxlen"""
        manager = ChatManager(max_history=5)
        session = manager.get_or_create_session("test")
        
        # Verify it's a deque with maxlen
        self.assertIsInstance(session['messages'], deque)
        self.assertEqual(session['messages'].maxlen, 5)
    
    def test_add_messages_multiple_calls(self):
        """Test adding messages through multiple calls"""
        # First batch
        self.manager.add_messages("test-uuid", [
            {"role": "user", "text": "First"}
        ])
        
        # Second batch
        self.manager.add_messages("test-uuid", [
            {"role": "assistant", "text": "Second"},
            {"role": "user", "text": "Third"}
        ])
        
        context = self.manager.get_context("test-uuid")
        self.assertEqual(len(context), 3)
        self.assertEqual(context[0]["content"], "First")
        self.assertEqual(context[1]["content"], "Second")
        self.assertEqual(context[2]["content"], "Third")


if __name__ == '__main__':
    unittest.main()
