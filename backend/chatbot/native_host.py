"""
UniversalChatbot - Native Messaging Host
Handles stdin/stdout JSON communication with Chrome Extension
"""
import sys
import json
import struct
import threading
from typing import Dict, Any, Callable

from chatbot.logger import get_logger
from chatbot.chat_manager import ChatManager
from chatbot.llm_client import LLMClient


class NativeHost:
    """Native Messaging Host for Chrome Extension communication"""
    
    def __init__(self):
        self.logger = get_logger()
        self.chat_manager = ChatManager()
        self.llm_client = LLMClient()
        self.running = True
    
    def read_message(self) -> Dict[str, Any]:
        """Read JSON message from Chrome Extension via stdin"""
        try:
            # Read message length (4 bytes, little-endian)
            raw_length = sys.stdin.buffer.read(4)
            if len(raw_length) == 0:
                return None
            
            message_length = struct.unpack('@I', raw_length)[0]
            
            # Read actual message
            message = sys.stdin.buffer.read(message_length).decode('utf-8')
            data = json.loads(message)
            
            self.logger.debug(f"Received: {data.get('type', 'unknown')}")
            return data
            
        except Exception as e:
            self.logger.error(f"Error reading message: {e}")
            return None
    
    def send_message(self, data: Dict[str, Any]):
        """Send JSON message to Chrome Extension via stdout"""
        try:
            message = json.dumps(data)
            encoded = message.encode('utf-8')
            
            # Send length (4 bytes) + message
            length = struct.pack('@I', len(encoded))
            sys.stdout.buffer.write(length)
            sys.stdout.buffer.write(encoded)
            sys.stdout.buffer.flush()
            
            self.logger.debug(f"Sent: {data.get('type', 'unknown')}")
            
        except Exception as e:
            self.logger.error(f"Error sending message: {e}")
    
    def handle_chat_update(self, data: Dict[str, Any]):
        """Process chat update from extension"""
        session_id = data.get('session_id')
        platform = data.get('platform')
        messages = data.get('messages', [])
        
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
    
    def process_message(self, data: Dict[str, Any]):
        """Route message to appropriate handler"""
        msg_type = data.get('type')
        
        handlers = {
            'chat_update': self.handle_chat_update,
            'ping': lambda d: self.send_message({'type': 'pong'}),
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
    
    def run(self):
        """Main loop - read and process messages"""
        self.logger.info("Native messaging host running")
        
        while self.running:
            try:
                message = self.read_message()
                
                if message is None:
                    # Chrome disconnected
                    self.logger.info("Chrome disconnected")
                    break
                
                self.process_message(message)
                
            except KeyboardInterrupt:
                self.logger.info("Received keyboard interrupt")
                break
            except Exception as e:
                self.logger.error(f"Error in main loop: {e}")
                continue
        
        self.logger.info("Native messaging host stopped")


if __name__ == '__main__':
    host = NativeHost()
    host.run()
