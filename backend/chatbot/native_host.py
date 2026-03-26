"""
UniversalChatbot - Native Messaging Host
Handles stdin/stdout JSON communication with Chrome Extension
Includes retry logic with exponential backoff and manual reconnect support
"""
import sys
import json
import struct
import threading
import time
from typing import Dict, Any, Callable, Optional

from chatbot.logger import get_logger
from chatbot.chat_manager import ChatManager
from chatbot.llm_client import LLMClient
from chatbot.error_handler import ErrorHandler


class NativeHost:
    """
    Native Messaging Host for Chrome Extension communication.
    
    Features:
    - Native messaging protocol
    - Retry with exponential backoff on disconnect
    - Manual reconnect support
    - Comprehensive error handling
    """
    
    # Retry configuration
    MAX_RECONNECT_ATTEMPTS = 5
    INITIAL_BACKOFF_MS = 1000
    MAX_BACKOFF_MS = 30000
    BACKOFF_MULTIPLIER = 2
    
    def __init__(self):
        self.logger = get_logger()
        self.chat_manager = ChatManager()
        self.llm_client = LLMClient()
        self.running = True
        self._connected = False
        self._reconnect_attempts = 0
        self._error_handler: Optional[ErrorHandler] = None
        self._manual_reconnect_requested = False
        self._last_message_time = 0
        self._connection_stats = {
            "connects": 0,
            "disconnects": 0,
            "messages_received": 0,
            "messages_sent": 0,
            "reconnects": 0
        }
        
        # Register error recovery strategies
        self._register_recovery_strategies()
    
    def set_error_handler(self, handler: ErrorHandler):
        """Set the error handler for recovery"""
        self._error_handler = handler
    
    def _register_recovery_strategies(self):
        """Register built-in error recovery strategies"""
        # Will be populated when error handler is set
        pass
    
    def _get_backoff_delay_ms(self) -> int:
        """
        Calculate exponential backoff delay.
        
        Returns:
            Delay in milliseconds
        """
        if self._reconnect_attempts == 0:
            return 0
        
        delay = self.INITIAL_BACKOFF_MS * (self.BACKOFF_MULTIPLIER ** (self._reconnect_attempts - 1))
        return min(delay, self.MAX_BACKOFF_MS)
    
    def _wait_backoff(self):
        """Wait for backoff delay with interrupt check"""
        delay_ms = self._get_backoff_delay_ms()
        if delay_ms > 0:
            self.logger.info(f"Waiting {delay_ms}ms before reconnect attempt...")
            # Wait in small increments to allow interruption
            waited = 0
            while waited < delay_ms and self.running and not self._manual_reconnect_requested:
                time.sleep(0.1)  # 100ms chunks
                waited += 100
    
    def read_message(self) -> Optional[Dict[str, Any]]:
        """
        Read JSON message from Chrome Extension via stdin.
        
        Returns:
            Parsed message dict or None if disconnected
        """
        try:
            # Read message length (4 bytes, little-endian)
            raw_length = sys.stdin.buffer.read(4)
            if len(raw_length) == 0:
                return None
            
            message_length = struct.unpack('@I', raw_length)[0]
            
            # Sanity check for message length
            if message_length > 10 * 1024 * 1024:  # Max 10MB
                self.logger.error(f"Message too large: {message_length} bytes")
                return None
            
            # Read actual message
            message = sys.stdin.buffer.read(message_length).decode('utf-8')
            data = json.loads(message)
            
            self._last_message_time = time.time()
            self._connection_stats["messages_received"] += 1
            
            self.logger.debug(f"Received: {data.get('type', 'unknown')}")
            return data
            
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error: {e}")
            if self._error_handler:
                self._error_handler.handle(e, "read_message")
            return None
            
        except UnicodeDecodeError as e:
            self.logger.error(f"Unicode decode error: {e}")
            if self._error_handler:
                self._error_handler.handle(e, "read_message")
            return None
            
        except Exception as e:
            self.logger.error(f"Error reading message: {e}")
            if self._error_handler:
                self._error_handler.handle(e, "read_message")
            return None
    
    def send_message(self, data: Dict[str, Any]) -> bool:
        """
        Send JSON message to Chrome Extension via stdout.
        
        Args:
            data: Message data to send
            
        Returns:
            True if sent successfully
        """
        try:
            message = json.dumps(data)
            encoded = message.encode('utf-8')
            
            # Validate message size
            if len(encoded) > 1024 * 1024:  # Max 1MB
                self.logger.error(f"Message too large to send: {len(encoded)} bytes")
                return False
            
            # Send length (4 bytes) + message
            length = struct.pack('@I', len(encoded))
            sys.stdout.buffer.write(length)
            sys.stdout.buffer.write(encoded)
            sys.stdout.buffer.flush()
            
            self._connection_stats["messages_sent"] += 1
            self.logger.debug(f"Sent: {data.get('type', 'unknown')}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending message: {e}")
            if self._error_handler:
                self._error_handler.handle(e, "send_message")
            return False
    
    def _on_connect(self):
        """Called when connection is established/re-established"""
        self._connected = True
        self._reconnect_attempts = 0
        self._connection_stats["connects"] += 1
        self.logger.info("Connection established")
        
        # Send connection acknowledgment
        self.send_message({
            "type": "connected",
            "reconnect": self._connection_stats["reconnects"] > 0
        })
    
    def _on_disconnect(self) -> bool:
        """
        Called when connection is lost.
        
        Returns:
            True to retry, False to give up
        """
        self._connected = False
        self._connection_stats["disconnects"] += 1
        self.logger.warning("Connection lost")
        
        # Try reconnection with backoff
        if self._reconnect_attempts < self.MAX_RECONNECT_ATTEMPTS:
            self._reconnect_attempts += 1
            self._connection_stats["reconnects"] += 1
            self.logger.info(f"Reconnection attempt {self._reconnect_attempts}/{self.MAX_RECONNECT_ATTEMPTS}")
            
            # Wait with backoff
            self._wait_backoff()
            
            # Check if manual reconnect was requested
            if self._manual_reconnect_requested:
                self.logger.info("Manual reconnect requested")
                self._manual_reconnect_requested = False
            
            return True
        else:
            self.logger.error(f"Max reconnection attempts ({self.MAX_RECONNECT_ATTEMPTS}) reached")
            return False
    
    def request_manual_reconnect(self):
        """
        Request a manual reconnect (for UI reconnect button).
        This resets the reconnect counter and attempts immediate reconnection.
        """
        self.logger.info("Manual reconnect requested via button")
        self._reconnect_attempts = 0
        self._manual_reconnect_requested = True
    
    def get_reconnect_status(self) -> Dict[str, Any]:
        """
        Get current reconnection status.
        
        Returns:
            Status dictionary for UI display
        """
        return {
            "connected": self._connected,
            "attempt": self._reconnect_attempts,
            "max_attempts": self.MAX_RECONNECT_ATTEMPTS,
            "backoff_delay_ms": self._get_backoff_delay_ms(),
            "can_reconnect": self._reconnect_attempts < self.MAX_RECONNECT_ATTEMPTS or self._manual_reconnect_requested
        }
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        stats = self._connection_stats.copy()
        stats["connected"] = self._connected
        stats["reconnect_attempts"] = self._reconnect_attempts
        stats["last_message_time"] = self._last_message_time
        return stats
    
    def handle_chat_update(self, data: Dict[str, Any]):
        """Process chat update from extension"""
        session_id = data.get('session_id')
        platform = data.get('platform')
        messages = data.get('messages', [])
        
        try:
            # Update chat history
            self.chat_manager.add_messages(session_id, messages)
            
            # Generate response if needed
            if data.get('requires_response', False):
                context = self.chat_manager.get_context(session_id)
                response_text = self.llm_client.generate_response(context)
                
                # Send back to extension
                self.send_message({
                    "type": "insert_text",
                    "session_id": session_id,
                    "text": response_text,
                    "auto_send": False
                })
                
        except Exception as e:
            self.logger.error(f"Error handling chat update: {e}")
            if self._error_handler:
                recovered = self._error_handler.handle(e, "handle_chat_update")
                if not recovered:
                    # Notify extension of error
                    self.send_message({
                        "type": "error",
                        "session_id": session_id,
                        "message": f"Error processing message: {str(e)}"
                    })
    
    def process_message(self, data: Dict[str, Any]):
        """Route message to appropriate handler"""
        msg_type = data.get('type')
        
        handlers: Dict[str, Callable] = {
            'chat_update': self.handle_chat_update,
            'ping': lambda d: self.send_message({'type': 'pong'}),
            'reconnect_status': lambda d: self.send_message({
                'type': 'reconnect_status',
                'data': self.get_reconnect_status()
            }),
            'request_reconnect': lambda d: self.request_manual_reconnect(),
        }
        
        handler = handlers.get(msg_type, self.handle_unknown)
        handler(data)
    
    def handle_unknown(self, data: Dict[str, Any]):
        """Handle unknown message types"""
        self.logger.warning(f"Unknown message type: {data.get('type')}")
        self.send_message({
            "type": "error",
            "message": f"Unknown message type: {data.get('type')}"
        })
    
    def _read_loop(self) -> bool:
        """
        Single iteration of read loop.
        
        Returns:
            True to continue, False to stop
        """
        try:
            message = self.read_message()
            
            if message is None:
                # Chrome disconnected
                self.logger.info("Chrome disconnected")
                return False
            
            self.process_message(message)
            return True
            
        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt")
            return False
        except Exception as e:
            self.logger.error(f"Error in main loop: {e}")
            if self._error_handler:
                self._error_handler.handle(e, "main_loop")
            # Continue on error
            return True
    
    def run(self):
        """
        Main loop - read and process messages with reconnection support.
        """
        self.logger.info("Native messaging host running")
        self._on_connect()
        
        while self.running:
            # Run read loop
            should_continue = self._read_loop()
            
            if not should_continue:
                # Check if we should reconnect
                if self._on_disconnect():
                    continue
                else:
                    break
        
        self.logger.info("Native messaging host stopped")
    
    def shutdown(self):
        """Graceful shutdown"""
        self.logger.info("Shutdown requested")
        self.running = False


if __name__ == '__main__':
    host = NativeHost()
    host.run()
