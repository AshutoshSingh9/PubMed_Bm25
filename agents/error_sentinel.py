"""
Error Sentinel Agent — A parallel background agent that monitors other components 
for errors, intercepts logging events or exceptions, and manages recovery/retries.
"""

import logging
import queue
import threading
import time
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ErrorSentinel:
    """
    An autonomous agent that runs in parallel to monitor, catch, and handle 
    errors across the entire application (pipeline, retrieval, genomics).
    """

    def __init__(self, max_retries: int = 3, retry_delay: float = 2.0):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.error_queue = queue.Queue()
        self.is_running = False
        self._monitor_thread = None
        self.error_history: List[Dict[str, Any]] = []

    def start(self):
        """Start the parallel monitoring agent in a background thread."""
        if self.is_running:
            return
        self.is_running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("ErrorSentinel parallel agent started.")

    def stop(self):
        """Stop the parallel monitoring agent."""
        self.is_running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2.0)
        logger.info("ErrorSentinel parallel agent stopped.")

    def report_error(self, component: str, error: Exception, context: Dict[str, Any] = None):
        """
        Other agents/components can report non-fatal errors here for async handling.
        """
        self.error_queue.put({
            "component": component,
            "error": error,
            "context": context or {},
            "timestamp": time.time(),
        })

    def _monitor_loop(self):
        """Background loop to process queue and handle errors continuously."""
        while self.is_running:
            try:
                # Block with timeout to allow graceful shutdown
                error_event = self.error_queue.get(timeout=1.0)
                self._handle_error_event(error_event)
                self.error_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"ErrorSentinel internal error while polling: {e}")

    def _handle_error_event(self, event: Dict[str, Any]):
        """Analyze and classify the error, then decide on a recovery strategy."""
        component = event["component"]
        error = event["error"]
        
        self.error_history.append(event)

        logger.warning(
            f"[ErrorSentinel] Intercepted error from '{component}': {type(error).__name__} - {str(error)}"
        )
        
        # Diagnostics and recovery heuristics
        if isinstance(error, ConnectionError):
            logger.info(f"[ErrorSentinel] Network issue detected in '{component}'. Suggesting immediate retry or fallback.")
        elif isinstance(error, TimeoutError):
            logger.info(f"[ErrorSentinel] Timeout in '{component}'. System might be overloaded. Backing off.")
        elif type(error).__name__ in ("JSONDecodeError", "ValueError"):
            logger.info(f"[ErrorSentinel] Parsing/validation error in '{component}'. Likely bad input or LLM hallucination.")
        else:
            logger.info(f"[ErrorSentinel] Unknown error class in '{component}'. Manual intervention may be required.")

    def execute_with_retry(self, component_name: str, func: Callable, *args, **kwargs) -> Any:
        """
        Wrapper to execute a function, catching errors synchronously and
        attempting retries while logging to the sentinel.
        """
        attempts = 0
        while attempts <= self.max_retries:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                attempts += 1
                self.report_error(component_name, e, {"attempt": attempts, "func": func.__name__})
                
                if attempts > self.max_retries:
                    logger.error(f"[ErrorSentinel] '{component_name}' max retries ({self.max_retries}) exhausted.")
                    raise
                
                logger.info(f"[ErrorSentinel] Retrying '{component_name}' ({attempts}/{self.max_retries}) after {self.retry_delay}s...")
                time.sleep(self.retry_delay)

# Global singleton for easy import and parallel use
sentinel = ErrorSentinel()
