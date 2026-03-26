#!/usr/bin/env python3
"""
UniversalChatbot - Python Native Messaging Host
Main entry point for the backend service
"""
import sys
import json
import os
from pathlib import Path

from chatbot.native_host import NativeHost
from chatbot.logger import get_logger

def main():
    """Main entry point"""
    logger = get_logger()
    logger.info("UniversalChatbot starting...")
    
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
        main()
    except KeyboardInterrupt:
        print("Shutting down...", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)
