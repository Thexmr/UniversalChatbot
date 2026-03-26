"""
UniversalChatbot - Test Suite
Tests for all backend modules
"""
import unittest
import json
import io
import sys
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from chatbot.chat_manager import ChatManager
from chatbot.native_host import NativeHost


class TestChatManager(unittest.TestCase):
    """Test cases for ChatManager"""
    
    def setUp(self):
        self.manager = ChatManager(max_history=5)
    
    def test_create_session(self):
        """Test session creation"""
        session = self.manager.get_or_create_session("test-uuid")
        self.assertIsNotNone(session)
        self.assertEqual(session['id'], "test-uuid")
        self.assertEqual(len(session['messages']), 0)
    
    def test_add_messages(self):
        """Test adding messages"""
        messages = [
            {"role": "user", "text": "Hello", "timestamp": "2025-01-01T10:00:00"},
            {"role": "assistant", "text": "Hi there!", "timestamp": "2025-01-01T10:01:00"}
        ]
        
        self.manager.add_messages("test-uuid", messages)
        context = self.manager.get_context("test-uuid")
        
        self.assertEqual(len(context), 2)
        self.assertEqual(context[0]["content"], "Hello")
        self.assertEqual(context[1]["content"], "Hi there!")
    
    def test_max_history(self):
        """Test that old messages are dropped"""
        for i in range(10):
            msg = [{"role": "user", "text": f"Message {i}", "timestamp": f"2025-01-0{i}"}]
            self.manager.add_messages("test-uuid", msg)
        
        context = self.manager.get_context("test-uuid")
        self.assertEqual(len(context), 5)  # Max history


class TestNativeHost(unittest.TestCase):
    """Test cases for NativeHost"""
    
    def setUp(self):
        self.host = NativeHost()
    
    def test_message_routing(self):
        """Test message routing"""
        # Mock handlers
        self.host.handle_chat_update = Mock()
        
        # Test chat_update routing
        message = {
            "type": "chat_update",
            "session_id": "123",
            "messages": []
        }
        self.host.process_message(message)
        self.host.handle_chat_update.assert_called_once()
    
    def test_unknown_message_type(self):
        """Test handling of unknown message types"""
        message = {"type": "unknown_type"}
        self.host.send_message = Mock()
        self.host.process_message(message)
        # Should not crash
        self.assertTrue(True)


class TestLLMClient(unittest.TestCase):
    """Test cases for LLMClient"""
    
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'})
    def test_initialization_without_key(self):
        """Test client handles missing API key"""
        with patch.dict('os.environ', {}, clear=True):
            from chatbot.llm_client import LLMClient
            client = LLMClient()
            self.assertIsNotNone(client)
    
    def test_is_configured_false_without_key(self):
        """Test is_configured returns False without key"""
        with patch.dict('os.environ', {}, clear=True):
            from chatbot.llm_client import LLMClient
            client = LLMClient()
            self.assertFalse(client.is_configured())
    
    def test_generate_response_mock(self):
        """Test response generation with mock"""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test'}, clear=True):
            with patch('chatbot.llm_client.OpenAI'):
                from chatbot.llm_client import LLMClient
                client = LLMClient()
                
                # Mock the client
                mock_response = MagicMock()
                mock_response.choices[0].message.content = "Test response"
                client.client = MagicMock()
                client.client.chat.completions.create.return_value = mock_response
                
                context = [{"role": "user", "content": "Hello"}]
                response = client.generate_response(context)
                
                self.assertEqual(response, "Test response")


class TestIntegration(unittest.TestCase):
    """Integration tests"""
    
    def test_full_flow(self):
        """Test complete message flow"""
        manager = ChatManager()
        
        # Simulate incoming messages
        messages = [
            {"role": "user", "text": "Hi bot!", "timestamp": "2025-01-01"}
        ]
        manager.add_messages("session-1", messages)
        
        context = manager.get_context("session-1")
        self.assertEqual(len(context), 1)
        self.assertEqual(context[0]["content"], "Hi bot!")


def run_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestChatManager))
    suite.addTests(loader.loadTestsFromTestCase(TestNativeHost))
    suite.addTests(loader.loadTestsFromTestCase(TestLLMClient))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    runner = unittest.TextTestRunner(verbosity=2)
    return runner.run(suite)


if __name__ == '__main__':
    result = run_tests()
    exit(0 if result.wasSuccessful() else 1)
