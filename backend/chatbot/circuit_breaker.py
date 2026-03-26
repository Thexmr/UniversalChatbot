"""
UniversalChatbot - Circuit Breaker Pattern
Prevents cascading failures by temporarily blocking requests after errors
"""
import time
import threading
import logging
from typing import Optional, Callable, Any
from enum import Enum
from datetime import datetime, timedelta


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"       # Normal operation
    OPEN = "open"          # Blocking requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit Breaker pattern implementation for LLM API protection.
    
    - CLOSED: Normal operation, requests pass through
    - OPEN: After 5 errors, blocks all requests for 60 seconds
    - HALF_OPEN: After timeout, allows one test request
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_max_calls: int = 1,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before half-open
            half_open_max_calls: Max calls in half-open state
            logger: Optional logger instance
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self.logger = logger or logging.getLogger("UniversalChatbot")
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0
        self._total_failures = 0
        self._total_successes = 0
        
        self._lock = threading.Lock()
    
    @property
    def state(self) -> CircuitState:
        """Current circuit state"""
        with self._lock:
            return self._state
    
    def can_execute(self) -> bool:
        """
        Check if request can be executed.
        
        Returns:
            True if request should be allowed
        """
        with self._lock:
            if self._state == CircuitState.CLOSED:
                return True
            
            if self._state == CircuitState.OPEN:
                # Check if timeout elapsed
                if self._last_failure_time and \
                   time.time() - self._last_failure_time >= self.recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
                    self.logger.info("Circuit breaker entering HALF_OPEN state")
                    return True
                return False
            
            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls < self.half_open_max_calls:
                    self._half_open_calls += 1
                    return True
                return False
            
            return True
    
    def record_success(self):
        """Record a successful call"""
        with self._lock:
            self._total_successes += 1
            
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.half_open_max_calls:
                    self._close_circuit()
            else:
                self._failure_count = 0
    
    def record_failure(self):
        """Record a failed call"""
        with self._lock:
            self._total_failures += 1
            self._failure_count += 1
            self._last_failure_time = time.time()
            
            if self._state == CircuitState.HALF_OPEN:
                self._open_circuit()
            elif self._failure_count >= self.failure_threshold:
                self._open_circuit()
    
    def _open_circuit(self):
        """Open the circuit (block requests)"""
        self._state = CircuitState.OPEN
        self.logger.warning(
            f"Circuit breaker OPENED after {self._failure_count} failures. "
            f"Blocking requests for {self.recovery_timeout}s"
        )
    
    def _close_circuit(self):
        """Close the circuit (normal operation)"""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0
        self.logger.info("Circuit breaker CLOSED - normal operation resumed")
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to call
            *args: Arguments for function
            **kwargs: Keyword arguments for function
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerOpen: If circuit is open
            Exception: Any exception from the function
        """
        if not self.can_execute():
            raise CircuitBreakerOpen(
                f"Circuit breaker is OPEN. Requests blocked for {self.recovery_timeout}s"
            )
        
        try:
            result = func(*args, **kwargs)
            self.record_success()
            return result
        except Exception as e:
            self.record_failure()
            raise
    
    def get_stats(self) -> dict:
        """Get circuit breaker statistics"""
        with self._lock:
            return {
                "state": self._state.value,
                "failure_count": self._failure_count,
                "success_count": self._success_count,
                "total_failures": self._total_failures,
                "total_successes": self._total_successes,
                "last_failure_time": datetime.fromtimestamp(
                    self._last_failure_time
                ).isoformat() if self._last_failure_time else None,
                "is_open": self._state == CircuitState.OPEN
            }
    
    def reset(self):
        """Reset circuit breaker to initial state"""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._half_open_calls = 0
            self._last_failure_time = None
            self.logger.info("Circuit breaker reset")


class CircuitBreakerOpen(Exception):
    """Exception raised when circuit breaker is open"""
    pass


class LLMAPICircuitBreaker:
    """
    Specialized circuit breaker for LLM API with rate limit protection.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.circuit = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60,
            half_open_max_calls=1,
            logger=logger
        )
        
        # Rate limiting tracking
        self._rate_limit_hits = 0
        self._last_rate_limit_time: Optional[float] = None
    
    def is_rate_limited(self) -> bool:
        """Check if currently rate limited"""
        return self.circuit.state == CircuitState.OPEN
    
    def record_rate_limit(self):
        """Record a rate limit error"""
        self._rate_limit_hits += 1
        self._last_rate_limit_time = time.time()
        self.circuit.record_failure()
    
    def get_wait_time(self) -> int:
        """Get remaining wait time in seconds"""
        stats = self.circuit.get_stats()
        if stats["last_failure_time"]:
            elapsed = time.time() - self.circuit._last_failure_time
            return max(0, self.circuit.recovery_timeout - int(elapsed))
        return 0
    
    def get_stats(self) -> dict:
        """Get combined statistics"""
        stats = self.circuit.get_stats()
        stats["rate_limit_hits"] = self._rate_limit_hits
        stats["last_rate_limit_time"] = datetime.fromtimestamp(
            self._last_rate_limit_time
        ).isoformat() if self._last_rate_limit_time else None
        return stats
