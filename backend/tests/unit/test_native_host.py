"""
Unit tests for NativeHost - Native Messaging Host
Tests stdin/stdout JSON communication with Chrome Extension
"""
import unittest
import json
import struct
import sys
import io
from unittest.mock import Mock, patch, MagicMock, call

from chatbot.native_host import NativeHost
from chatbot.chat_manager import ChatManager
from chatbot.llm_client import LLMClient


class MockBufferWrapper:
    """Wrapper to provide .buffer attribute for io.BytesIO"""
    def __init__(self, data=b''):
        self._buffer = io.BytesIO(data)
    
    def read(self, size=-1):
        return self._buffer.read(size)
    
    def write(self, data):
        return self._buffer.write(data)
    
    def flush(self):
        return self._buffer.flush()
    
    def seek(self, pos):
        return self._buffer.seek(pos)
    
    @property
    def buffer(self):
        return self._buffer


class TestNativeHost(unittest.TestCase):
    """Test cases for NativeHost class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.host = NativeHost()
        self.host.running = False  # Prevent actual running
    
    def test_initialization(self):
        """Test NativeHost initializes correctly"""
        host = NativeHost()
        self.assertIsNotNone(host.logger)
        self.assertIsNotNone(host.chat_manager)
        self.assertIsNotNone(host.llm_client)
        self.assertTrue(host.running)
    
    def test_read_message_length_success(self):
        """Test reading message length from stdin"""
        # Create a test message
        test_message = json.dumps({"type": "ping"})
        encoded = test_message.encode('utf-8')
        message_length = len(encoded)
        
        # Create mock stdin with length prefix
        mock_stdin = MockBufferWrapper(
            struct.pack('@I', message_length) + encoded
        )
        
        # Replace sys.stdin temporarily
        original_stdin = sys.stdin
        sys.stdin = mock_stdin
        
        try:
            result = self.host.read_message()
            self.assertIsNotNone(result)
            self.assertEqual(result.get('type'), 'ping')
        finally:
            sys.stdin = original_stdin
    
    def test_read_message_eof(self):
        """Test reading when EOF (empty bytes)"""
        # Create empty stdin
        mock_stdin = MockBufferWrapper(b'')
        
        original_stdin = sys.stdin
        sys.stdin = mock_stdin
        
        try:
            result = self.host.read_message()
            self.assertIsNone(result)
        finally:
            sys.stdin = original_stdin
    
    def test_read_message_invalid_json(self):
        """Test handling invalid JSON"""
        invalid_message = b"not valid json"
        mock_stdin = MockBufferWrapper(
            struct.pack('@I', len(invalid_message)) + invalid_message
        )
        
        original_stdin = sys.stdin
        sys.stdin = mock_stdin
        
        try:
            result = self.host.read_message()
            self.assertIsNone(result)  # Should return None on error
        finally:
            sys.stdin = original_stdin
    
    def test_send_message_success(self):
        """Test sending message to stdout"""
        test_data = {"type": "pong", "session_id": "test-123"}
        
        # Create mock stdout
        mock_stdout = MockBufferWrapper()
        original_stdout = sys.stdout
        sys.stdout = mock_stdout
        
        try:
            self.host.send_message(test_data)
            
            # Get the internal buffer content
            buffer = mock_stdout.buffer
            buffer.seek(0)
            output = buffer.read()
            
            # Verify length prefix (4 bytes)
            length = struct.unpack('@I', output[:4])[0]
            
            # Verify message content
            message = json.loads(output[4:4+length].decode('utf-8'))
            self.assertEqual(message['type'], 'pong')
            self.assertEqual(message['session_id'], 'test-123')
        finally:
            sys.stdout = original_stdout
    
    def test_send_message_complex(self):
        """Test sending complex message with nested data"""
        test_data = {
            "type": "insert_text",
            "session_id": "uuid-123",
            "text": "Hello, World!",
            "auto_send": False,
            "metadata": {"timestamp": "2025-01-01"}
        }
        
        mock_stdout = MockBufferWrapper()
        original_stdout = sys.stdout
        sys.stdout = mock_stdout
        
        try:
            self.host.send_message(test_data)
            
            buffer = mock_stdout.buffer
            buffer.seek(0)
            output = buffer.read()
            
            length = struct.unpack('@I', output[:4])[0]
            message = json.loads(output[4:4+length].decode('utf-8'))
            
            self.assertEqual(message['type'], 'insert_text')
            self.assertEqual(message['text'], 'Hello, World!')
            self.assertEqual(message['metadata']['timestamp'], '2025-01-01')
        finally:
            sys.stdout = original_stdout
    
    def test_handle_chat_update_with_response(self):
        """Test handling chat update that requires a response"""
        with patch.object(self.host.chat_manager, 'add_messages') as mock_add, \
             patch.object(self.host.chat_manager, 'get_context') as mock_context, \
             patch.object(self.host.llm_client, 'generate_response') as mock_gen, \
             patch.object(self.host, 'send_message') as mock_send:
            
            mock_context.return_value = [{"role": "user", "content": "Hello"}]
            mock_gen.return_value = "Generated response"
            
            test_data = {
                "session_id": "session-123",
                "platform": "web",
                "messages": [{"role": "user", "text": "Hello", "timestamp": "2025-01-01"}],
                "requires_response": True
            }
            
            self.host.handle_chat_update(test_data)
            
            # Verify messages were added
            mock_add.assert_called_once_with("session-123", test_data["messages"])
            
            # Verify context was retrieved
            mock_context.assert_called_once_with("session-123")
            
            # Verify LLM was called
            mock_gen.assert_called_once_with([{"role": "user", "content": "Hello"}])
            
            # Verify response was sent
            mock_send.assert_called_once()
            sent_message = mock_send.call_args[0][0]
            self.assertEqual(sent_message["type"], "insert_text")
            self.assertEqual(sent_message["text"], "Generated response")
            self.assertEqual(sent_message["session_id"], "session-123")
            self.assertFalse(sent_message["auto_send"])
    
    def test_handle_chat_update_no_response(self):
        """Test handling chat update that doesn't require a response"""
        with patch.object(self.host.chat_manager, 'add_messages') as mock_add, \
             patch.object(self.host.chat_manager, 'get_context') as mock_context, \
             patch.object(self.host.llm_client, 'generate_response') as mock_gen, \
             patch.object(self.host, 'send_message') as mock_send:
            
            mock_context.return_value = []
            mock_gen.return_value = "Response"
            
            test_data = {
                "session_id": "session-456",
                "platform": "web",
                "messages": [{"role": "user", "text": "Hello"}],
                "requires_response": False
            }
            
            self.host.handle_chat_update(test_data)
            
            # Messages should be added
            mock_add.assert_called_once()
            
            # But no response should be generated
            mock_context.assert_not_called()
            mock_gen.assert_not_called()
            mock_send.assert_not_called()
    
    def test_process_message_chat_update(self):
        """Test routing chat_update messages"""
        with patch.object(self.host, 'handle_chat_update') as mock_handler:
            test_data = {"type": "chat_update", "session_id": "test"}
            self.host.process_message(test_data)
            mock_handler.assert_called_once_with(test_data)
    
    def test_process_message_ping(self):
        """Test routing ping messages"""
        with patch.object(self.host, 'send_message') as mock_send:
            test_data = {"type": "ping"}
            self.host.process_message(test_data)
            mock_send.assert_called_once_with({'type': 'pong'})
    
    def test_process_message_unknown(self):
        """Test handling unknown message types"""
        with patch.object(self.host, 'send_message') as mock_send:
            test_data = {"type": "unknown_type"}
            self.host.process_message(test_data)
            
            mock_send.assert_called_once()
            sent_message = mock_send.call_args[0][0]
            self.assertEqual(sent_message["type"], "error")
            self.assertIn("unknown_type", sent_message["message"])
    
    def test_handle_unknown(self):
        """Test unknown message handler directly"""
        with patch.object(self.host, 'send_message') as mock_send:
            test_data = {"type": "weird_type", "data": "test"}
            self.host.handle_unknown(test_data)
            
            mock_send.assert_called_once()
            sent_message = mock_send.call_args[0][0]
            self.assertEqual(sent_message["type"], "error")
    
    def test_run_main_loop(self):
        """Test main run loop processes messages"""
        # Create test message (ping)
        ping_message = json.dumps({"type": "ping"})
        encoded = ping_message.encode('utf-8')
        
        # Create stdin with length prefix + message
        mock_stdin = MockBufferWrapper(
            struct.pack('@I', len(encoded)) + encoded
        )
        
        mock_stdout = MockBufferWrapper()
        
        original_stdin = sys.stdin
        original_stdout = sys.stdout
        
        sys.stdin = mock_stdin
        sys.stdout = mock_stdout
        
        try:
            self.host.running = True
            self.host.run()
            
            # Read the response from the buffer
            buffer = mock_stdout.buffer
            buffer.seek(0)
            output = buffer.read()
            
            # Verify we got a pong response
            if len(output) >= 4:
                length = struct.unpack('@I', output[:4])[0]
                message = json.loads(output[4:4+length].decode('utf-8'))
                self.assertEqual(message['type'], 'pong')
        finally:
            sys.stdin = original_stdin
            sys.stdout = original_stdout
    
    def test_run_keyboard_interrupt(self):
        """Test graceful shutdown on keyboard interrupt"""
        with patch.object(self.host, 'read_message', side_effect=KeyboardInterrupt):
            self.host.run()
            # Should complete without error
    
    def test_run_general_exception(self):
        """Test handling of general exceptions in main loop"""
        with patch.object(self.host, 'read_message', side_effect=[Exception("Test error"), None]):
            with patch.object(self.host, 'logger') as mock_logger:
                self.host.running = True
                self.host.run()
                # Should continue after exception and stop on None
                # Verify error was logged
                mock_logger.error.assert_called()


if __name__ == '__main__':
    unittest.main()
