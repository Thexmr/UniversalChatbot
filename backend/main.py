#!/usr/bin/env python3
"""
UniversalChatbot - Python Native Messaging Host
Main entry point for the backend service
"""
import sys
import json
import os
import threading
from pathlib import Path

from chatbot.native_host import NativeHost
from chatbot.logger import get_logger
from chatbot.chat_manager import ChatManager
from chatbot.llm_client import LLMClient

def main():
    """Main entry point"""
    logger = get_logger()
    logger.info("UniversalChatbot starting...")
    
    # Initialize components
    chat_manager = ChatManager()
    llm_client = LLMClient()
    
    # Check if running in native messaging mode
    if len(sys.argv) > 1:
        # Registry key passed (Windows)
        registry_key = sys.argv[1]
        logger.info(f"Native host registered with key: {registry_key}")
    
    # Start native messaging host
    host = NativeHost()
    host.run()


if __name__ == "__main__":
    try:
        # Import dashboard
        from dashboard.app import start_dashboard_thread
        
        # Initialize components for dashboard
        from chatbot.chat_manager import ChatManager
        from chatbot.llm_client import LLMClient
        
        chat_manager = ChatManager()
        llm_client = LLMClient()
        
        # Start dashboard in separate thread
        dashboard_thread = threading.Thread(
            target=start_dashboard_thread,
            args=(chat_manager, llm_client, 5000),
            daemon=True
        )
        dashboard_thread.start()
        
        logger = get_logger()
        logger.info("Dashboard started on http://localhost:5000")
        
        # Continue with native host
        main()
    except KeyboardInterrupt:
        print("Shutting down...", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)
