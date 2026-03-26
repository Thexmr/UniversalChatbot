#!/usr/bin/env python3
"""
UniversalChatbot - Python Native Messaging Host
Main entry point for the backend service with error handling and health checks
"""
import sys
import json
import os
import signal
import threading
import time
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from chatbot.native_host import NativeHost
from chatbot.logger import get_logger
from chatbot.error_handler import ErrorHandler
from chatbot.chat_manager import ChatManager
from chatbot.llm_client import LLMClient
from chatbot.circuit_breaker import LLMAPICircuitBreaker

# Global instances for health checks and shutdown
chat_manager: ChatManager = None
llm_client: LLMClient = None
error_handler: ErrorHandler = None
circuit_breaker: LLMAPICircuitBreaker = None
health_server: HTTPServer = None
is_shutting_down = False


def get_version() -> str:
    """Get application version"""
    return "0.1.0"


def health_check() -> Dict[str, Any]:
    """
    Health check endpoint.
    Returns overall system health status.
    """
    global chat_manager, llm_client, circuit_breaker, is_shutting_down
    
    status = {
        "status": "healthy",
        "version": get_version(),
        "timestamp": time.time(),
        "shutting_down": is_shutting_down
    }
    
    # LLM connection status
    if llm_client:
        status["llm_connected"] = llm_client.is_configured()
    else:
        status["llm_connected"] = False
    
    # Active sessions
    if chat_manager:
        status["sessions_active"] = len(chat_manager.sessions)
    else:
        status["sessions_active"] = 0
    
    # Circuit breaker status
    if circuit_breaker:
        cb_stats = circuit_breaker.get_stats()
        status["circuit_breaker"] = {
            "state": cb_stats["state"],
            "is_open": cb_stats["is_open"]
        }
        
        if cb_stats["is_open"]:
            status["status"] = "degraded"
            status["wait_time"] = circuit_breaker.get_wait_time()
    
    # Error statistics
    if error_handler:
        status["errors"] = error_handler.get_stats()
    
    return status


class HealthCheckHandler(BaseHTTPRequestHandler):
    """HTTP handler for health check endpoint"""
    
    def log_message(self, format, *args):
        """Suppress default logging"""
        pass
    
    def do_GET(self):
        """Handle GET requests"""
        if self.path == "/health":
            health = health_check()
            status_code = 200 if health["status"] == "healthy" else 503
            
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(health, indent=2).encode())
        
        elif self.path == "/ready":
            # Readiness check
            if llm_client and llm_client.is_configured():
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"ready": True}).encode())
            else:
                self.send_response(503)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"ready": False}).encode())
        
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        """Handle POST requests"""
        if self.path == "/shutdown":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"message": "Shutting down..."}).encode())
            
            # Trigger graceful shutdown
            threading.Thread(target=graceful_shutdown, daemon=True).start()
        else:
            self.send_response(404)
            self.end_headers()


def start_health_server(port: int = 8080):
    """Start health check HTTP server"""
    global health_server
    
    try:
        health_server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
        logger = get_logger()
        logger.info(f"Health check server started on port {port}")
        
        # Run in separate thread
        server_thread = threading.Thread(target=health_server.serve_forever, daemon=True)
        server_thread.start()
        
        return health_server
    except Exception as e:
        logger = get_logger()
        logger.error(f"Failed to start health server: {e}")
        return None


def graceful_shutdown(signum=None, frame=None):
    """
    Graceful shutdown handler.
    Saves sessions and cleans up resources before exiting.
    """
    global is_shutting_down, chat_manager, health_server, logger
    
    if is_shutting_down:
        return
    
    is_shutting_down = True
    logger = get_logger()
    
    signame = signal.Signals(signum).name if signum else "MANUAL"
    logger.info(f"Graceful shutdown initiated (signal: {signame})...")
    
    try:
        # Stop health server
        if health_server:
            logger.info("Stopping health check server...")
            health_server.shutdown()
        
        # Persist sessions
        if chat_manager:
            logger.info("Saving sessions...")
            chat_manager.close_all_sessions() if hasattr(chat_manager, 'close_all_sessions') else None
        
        # Log shutdown
        logger.info("Shutdown complete")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")
    
    finally:
        sys.exit(0)


def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown"""
    signal.signal(signal.SIGINT, graceful_shutdown)
    signal.signal(signal.SIGTERM, graceful_shutdown)
    
    # Windows specific
    if hasattr(signal, 'SIGBREAK'):
        signal.signal(signal.SIGBREAK, graceful_shutdown)


def main():
    """Main entry point"""
    global chat_manager, llm_client, error_handler, circuit_breaker
    
    logger = get_logger()
    logger.info("UniversalChatbot starting...")
    logger.info(f"Version: {get_version()}")
    
    # Setup error handling
    error_handler = ErrorHandler(logger)
    
    # Setup circuit breaker for LLM API
    circuit_breaker = LLMAPICircuitBreaker(logger)
    
    # Check if running in native messaging mode
    if len(sys.argv) > 1:
        # Registry key passed (Windows)
        registry_key = sys.argv[1]
        logger.info(f"Native host registered with key: {registry_key}")
    
    # Setup signal handlers
    setup_signal_handlers()
    
    try:
        # Initialize components
        chat_manager = ChatManager()
        llm_client = LLMClient()
        
        # Wrap LLM client with circuit breaker
        original_generate_response = llm_client.generate_response
        
        def protected_generate_response(context, system_prompt=None):
            """Generate response with circuit breaker protection"""
            if circuit_breaker.is_rate_limited():
                wait_time = circuit_breaker.get_wait_time()
                logger.warning(f"Circuit breaker open. Waiting {wait_time}s")
                return f"[Rate limited - please wait {wait_time} seconds]"
            
            try:
                result = original_generate_response(context, system_prompt)
                circuit_breaker.circuit.record_success()
                return result
            except Exception as e:
                # Check if it's a rate limit error
                error_str = str(e).lower()
                if "rate" in error_str or "429" in error_str or "limit" in error_str:
                    circuit_breaker.record_rate_limit()
                    wait_time = circuit_breaker.get_wait_time()
                    logger.warning(f"Rate limit hit. Waiting {wait_time}s")
                    return f"[Rate limited - please wait {wait_time} seconds]"
                else:
                    circuit_breaker.circuit.record_failure()
                    raise
        
        llm_client.generate_response = protected_generate_response
        
        # Start health check server (in background)
        health_port = int(os.getenv("HEALTH_PORT", "8080"))
        start_health_server(health_port)
        
        # Start native messaging host
        host = NativeHost()
        
        # Connect error handler to host
        if hasattr(host, 'set_error_handler'):
            host.set_error_handler(error_handler)
        
        logger.info("UniversalChatbot fully initialized")
        host.run()
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
        graceful_shutdown()
    
    except Exception as e:
        logger.error(f"Fatal error in main: {e}")
        error_handler.handle(e, "main")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Shutting down...", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)
