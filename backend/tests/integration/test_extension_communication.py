"""
Integration Tests for Extension Communication
Tests E2E flow between Chrome Extension and Python Backend
"""
import unittest
import subprocess
import json
import struct
import time
import signal
import os
import sys
from pathlib import Path


class TestExtensionCommunication(unittest.TestCase):
    """Integration tests for Chrome Extension native messaging"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        cls.backend_dir = Path(__file__).parent.parent.parent
        cls.python_exe = sys.executable
        cls.main_script = cls.backend_dir / "main.py"
    
    def setUp(self):
        """Start backend process for each test"""
        # Set up environment
        env = os.environ.copy()
        env['OPENAI_API_KEY'] = 'test-key-integration'  # Use mock key
        env['PYTHONPATH'] = str(self.backend_dir)
        
        # Start the backend process
        self.process = subprocess.Popen(
            [self.python_exe, str(self.main_script)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env
        )
        # Give process time to start
        time.sleep(0.5)
    
    def tearDown(self):
        """Clean up backend process"""
        if hasattr(self, 'process') and self.process:
            self.process.stdin.close()
            self.process.stdout.close()
            self.process.stderr.close()
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
    
    def _send_message(self, data):
        """Send JSON message via native messaging protocol"""
        message = json.dumps(data)
        encoded = message.encode('utf-8')
        length = struct.pack('@I', len(encoded))
        
        self.process.stdin.write(length)
        self.process.stdin.write(encoded)
        self.process.stdin.flush()
    
    def _read_message(self, timeout=5):
        """Read JSON message via native messaging protocol"""
        # Set stdout to non-blocking
        import fcntl
        import select
        
        # Read length (4 bytes)
        ready, _, _ = select.select([self.process.stdout], [], [], timeout)
        if not ready:
            raise TimeoutError("No response received")
        
        raw_length = self.process.stdout.read(4)
        if len(raw_length) == 0:
            return None
        
        message_length = struct.unpack('@I', raw_length)[0]
        
        # Read actual message
        ready, _, _ = select.select([self.process.stdout], [], [], timeout)
        if not ready:
            raise TimeoutError("Response incomplete")
        
        message = self.process.stdout.read(message_length)
        return json.loads(message.decode('utf-8'))
    
    def test_ping_pong(self):
        """Test basic ping-pong communication"""
        # Send ping
        self._send_message({"type": "ping"})
        
        # Read response
        response = self._read_message()
        
        self.assertIsNotNone(response)
        self.assertEqual(response.get('type'), 'pong')
    
    def test_chat_update_no_response(self):
        """Test chat update without required response"""
        test_data = {
            "type": "chat_update",
            "session_id": "test-session-123",
            "platform": "web",
            "messages": [
                {"role": "user", "text": "Hello bot!", "timestamp": "2025-01-01T12:00:00"}
            ],
            "requires_response": False
        }
        
        self._send_message(test_data)
        
        # Small delay to ensure processing
        time.sleep(0.2)
        
        # Since requires_response is False, no immediate response expected
        # Process should still be alive
        self.assertIsNone(self.process.poll())
    
    def test_unknown_message_type(self):
        """Test handling of unknown message types"""
        test_data = {
            "type": "unknown_weird_type",
            "data": "test"
        }
        
        self._send_message(test_data)
        
        # Read error response
        response = self._read_message()
        
        self.assertIsNotNone(response)
        self.assertEqual(response.get('type'), 'error')
        self.assertIn('unknown_weird_type', response.get('message', ''))
    
    def test_multiple_messages(self):
        """Test handling multiple sequential messages"""
        messages = [
            {"type": "ping"},
            {"type": "ping"},
            {"type": "ping"}
        ]
        
        responses = []
        for msg in messages:
            self._send_message(msg)
            response = self._read_message()
            responses.append(response)
        
        # All should be pong
        for response in responses:
            self.assertEqual(response.get('type'), 'pong')
        
        self.assertEqual(len(responses), 3)
    
    def test_json_message_structure(self):
        """Test that messages are valid JSON with expected structure"""
        self._send_message({"type": "ping"})
        response = self._read_message()
        
        # Verify response structure
        self.assertIsInstance(response, dict)
        self.assertIn('type', response)
        self.assertIsInstance(response['type'], str)


class TestExtensionCommunicationMock(unittest.TestCase):
    """Integration tests with mocked LLM for reliable testing"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        cls.backend_dir = Path(__file__).parent.parent.parent
        cls.python_exe = sys.executable
        cls.main_script = cls.backend_dir / "main.py"
    
    def setUp(self):
        """Start backend with mocked OpenAI"""
        env = os.environ.copy()
        env['OPENAI_API_KEY'] = 'test-key'
        env['PYTHONPATH'] = str(self.backend_dir)
        
        self.process = subprocess.Popen(
            [self.python_exe, str(self.main_script)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env
        )
        time.sleep(0.5)
    
    def tearDown(self):
        """Clean up"""
        if hasattr(self, 'process') and self.process:
            self.process.stdin.close()
            self.process.stdout.close()
            self.process.stderr.close()
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()


if __name__ == '__main__':
    unittest.main()
