"""
UniversalChatbot - Error Handler
Centralized error handling with recovery strategies
"""
import logging
import traceback
import time
from typing import Optional, Callable, Dict, Any
from datetime import datetime, timedelta
from collections import defaultdict


class ErrorHandler:
    """Centralized error handling with recovery"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("UniversalChatbot")
        self.error_counts: Dict[str, int] = {}
        self.error_timestamps: Dict[str, list] = defaultdict(list)
        self.recovery_strategies: Dict[str, Callable] = {}
        self._last_error_time: Optional[datetime] = None
        self._recovered_errors: set = set()
    
    def handle(self, error: Exception, context: str = "") -> bool:
        """
        Handle error and attempt recovery.
        
        Args:
            error: The exception to handle
            context: Context where error occurred
            
        Returns:
            bool: True if error was recovered, False otherwise
        """
        error_type = type(error).__name__
        
        # Update error statistics
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        self._last_error_time = datetime.now()
        
        # Track error timestamps for rate calculation
        self.error_timestamps[error_type].append(datetime.now())
        
        # Keep only last 100 timestamps per error type
        if len(self.error_timestamps[error_type]) > 100:
            self.error_timestamps[error_type] = self.error_timestamps[error_type][-100:]
        
        # Log error with full traceback
        self.logger.error(f"[{context}] {error_type}: {str(error)}")
        self.logger.debug(traceback.format_exc())
        
        # Recovery strategy
        if error_type in self.recovery_strategies:
            try:
                self.logger.info(f"Attempting recovery for {error_type}")
                self.recovery_strategies[error_type]()
                self._recovered_errors.add(error_type)
                self.logger.info(f"Recovery successful for {error_type}")
                return True
            except Exception as e:
                self.logger.error(f"Recovery failed for {error_type}: {e}")
        
        return False
    
    def register_recovery(self, error_type: str, strategy: Callable):
        """
        Register a recovery strategy for an error type.
        
        Args:
            error_type: Name of the exception class
            strategy: Callable that attempts recovery
        """
        self.recovery_strategies[error_type] = strategy
        self.logger.debug(f"Registered recovery strategy for {error_type}")
    
    def get_error_rate(self, error_type: str, window_seconds: int = 60) -> int:
        """
        Get error rate for a specific error type within a time window.
        
        Args:
            error_type: Type of error to check
            window_seconds: Time window in seconds
            
        Returns:
            Number of errors in the time window
        """
        cutoff = datetime.now() - timedelta(seconds=window_seconds)
        timestamps = self.error_timestamps.get(error_type, [])
        return len([t for t in timestamps if t > cutoff])
    
    def is_error_spike(self, error_type: str, threshold: int = 5, 
                       window_seconds: int = 60) -> bool:
        """
        Check if there's an error spike for a specific error type.
        
        Args:
            error_type: Type of error to check
            threshold: Number of errors to consider a spike
            window_seconds: Time window in seconds
            
        Returns:
            True if error rate exceeds threshold
        """
        return self.get_error_rate(error_type, window_seconds) >= threshold
    
    def get_stats(self) -> Dict[str, Any]:
        """Get error statistics"""
        return {
            "total_errors": sum(self.error_counts.values()),
            "error_counts": self.error_counts.copy(),
            "last_error_time": self._last_error_time.isoformat() if self._last_error_time else None,
            "recovered_errors": list(self._recovered_errors),
            "registered_strategies": list(self.recovery_strategies.keys())
        }
    
    def reset_stats(self):
        """Reset error statistics"""
        self.error_counts.clear()
        self.error_timestamps.clear()
        self._recovered_errors.clear()
        self.logger.info("Error statistics reset")
