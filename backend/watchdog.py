"""
UniversalChatbot - Watchdog
Monitors main.py process and auto-restarts on crash
Max 3 restarts in 1 minute
"""
import subprocess
import sys
import time
import signal
import os
from datetime import datetime, timedelta
from collections import deque
from pathlib import Path

from chatbot.logger import get_logger


class Watchdog:
    """
    Process watchdog that monitors and restarts the main application.
    
    Features:
    - Monitors main.py process
    - Auto-restart on crash
    - Max 3 restarts in 1 minute
    - Graceful shutdown handling
    """
    
    def __init__(
        self,
        max_restarts: int = 3,
        restart_window: int = 60,
        script_path: str = None,
        logger=None
    ):
        """
        Initialize watchdog.
        
        Args:
            max_restarts: Maximum restarts in window
            restart_window: Time window in seconds
            script_path: Path to script to monitor
            logger: Logger instance
        """
        self.max_restarts = max_restarts
        self.restart_window = restart_window
        self.script_path = script_path or self._find_main_script()
        self.logger = logger or get_logger("Watchdog")
        
        self._restart_times: deque = deque(maxlen=max_restarts * 2)
        self._current_process: subprocess.Popen = None
        self._running = False
        self._restart_count = 0
        self._start_time: datetime = None
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _find_main_script(self) -> str:
        """Find the main.py script path"""
        backend_dir = Path(__file__).parent
        main_script = backend_dir / "main.py"
        if main_script.exists():
            return str(main_script)
        raise FileNotFoundError("Could not find main.py script")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        signame = signal.Signals(signum).name
        self.logger.info(f"Watchdog received {signame}, shutting down...")
        self._running = False
        if self._current_process:
            self._terminate_process()
    
    def _terminate_process(self):
        """Terminate current process gracefully"""
        if not self._current_process:
            return
        
        self.logger.info("Terminating child process...")
        try:
            # First try graceful termination
            self._current_process.terminate()
            
            # Wait up to 5 seconds
            try:
                self._current_process.wait(timeout=5)
                self.logger.info("Child process terminated gracefully")
            except subprocess.TimeoutExpired:
                self.logger.warning("Child process didn't terminate, killing...")
                self._current_process.kill()
                self._current_process.wait()
                self.logger.info("Child process killed")
                
        except Exception as e:
            self.logger.error(f"Error terminating process: {e}")
    
    def _can_restart(self) -> bool:
        """
        Check if restart is allowed.
        
        Returns:
            True if restart is within limits
        """
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.restart_window)
        
        # Remove old restart times
        while self._restart_times and self._restart_times[0] < cutoff:
            self._restart_times.popleft()
        
        return len(self._restart_times) < self.max_restarts
    
    def _run_process(self) -> int:
        """
        Run the main process.
        
        Returns:
            Process return code
        """
        self.logger.info(f"Starting process: python {self.script_path}")
        
        try:
            self._current_process = subprocess.Popen(
                [sys.executable, self.script_path],
                cwd=os.path.dirname(self.script_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            # Wait for process to complete
            return_code = self._current_process.wait()
            
            if return_code != 0:
                self.logger.error(
                    f"Process exited with code {return_code}"
                )
            else:
                self.logger.info("Process exited normally")
            
            return return_code
            
        except Exception as e:
            self.logger.error(f"Failed to run process: {e}")
            return -1
        finally:
            self._current_process = None
    
    def run(self):
        """
        Main watchdog loop.
        
        Keeps restarting the process until:
        - Watchdog is stopped via signal
        - Too many restarts in time window
        """
        self.logger.info(
            f"Watchdog started (max {self.max_restarts} restarts/"
            f"{self.restart_window}s)"
        )
        self._running = True
        self._start_time = datetime.now()
        
        while self._running:
            # Check if we can restart
            if not self._can_restart():
                self.logger.error(
                    f"Too many restarts ({self.max_restarts} in "
                    f"{self.restart_window}s). Giving up."
                )
                break
            
            # Record restart
            self._restart_times.append(datetime.now())
            self._restart_count += 1
            
            # Run the process
            return_code = self._run_process()
            
            # Check if we should restart
            if not self._running:
                break
            
            if return_code == 0:
                # Normal exit, don't restart
                self.logger.info("Process exited normally, watchdog stopping")
                break
            
            # Wait before restart
            self.logger.info("Waiting 2 seconds before restart...")
            time.sleep(2)
        
        runtime = datetime.now() - self._start_time
        self.logger.info(
            f"Watchdog stopped. Runtime: {runtime}, Restarts: {self._restart_count}"
        )
    
    def get_stats(self) -> dict:
        """Get watchdog statistics"""
        return {
            "running": self._running,
            "restart_count": self._restart_count,
            "recent_restarts": len(self._restart_times),
            "max_restarts": self.max_restarts,
            "restart_window": self.restart_window,
            "script_path": self.script_path,
            "start_time": self._start_time.isoformat() if self._start_time else None
        }


def run_watchdog():
    """Entry point for running watchdog"""
    import argparse
    
    parser = argparse.ArgumentParser(description="UniversalChatbot Watchdog")
    parser.add_argument(
        "--max-restarts",
        type=int,
        default=3,
        help="Maximum restarts in time window (default: 3)"
    )
    parser.add_argument(
        "--restart-window",
        type=int,
        default=60,
        help="Time window in seconds (default: 60)"
    )
    parser.add_argument(
        "--script",
        type=str,
        default=None,
        help="Path to script to monitor"
    )
    
    args = parser.parse_args()
    
    watchdog = Watchdog(
        max_restarts=args.max_restarts,
        restart_window=args.restart_window,
        script_path=args.script
    )
    
    try:
        watchdog.run()
    except KeyboardInterrupt:
        print("\nWatchdog interrupted", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    run_watchdog()
