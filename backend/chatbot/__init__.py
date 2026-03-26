"""UniversalChatbot Python Backend Package"""

__version__ = "0.1.0"
__author__ = "AI Coding Team"

# Core components
from .chat_manager import ChatManager
from .llm_client import LLMClient
from .native_host import NativeHost
from .logger import get_logger

# Error handling & reliability
from .error_handler import ErrorHandler
from .circuit_breaker import CircuitBreaker, LLMAPICircuitBreaker, CircuitBreakerOpen

__all__ = [
    "ChatManager",
    "LLMClient", 
    "NativeHost",
    "get_logger",
    "ErrorHandler",
    "CircuitBreaker",
    "LLMAPICircuitBreaker",
    "CircuitBreakerOpen",
]