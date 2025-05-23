import logging
import os
import inspect
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Optional, Dict

class ClassNameInjector(logging.Filter):
    def filter(self, record):
        if not hasattr(record, 'classname'):
            record.classname = 'N/A'
        return True
class Logger:
    _instance: Optional['Logger'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
            cls._instance._initialize_logger()
        return cls._instance
    
    def _initialize_logger(self):
        print("Initializing logger...")
        self.logger = logging.getLogger('MAIA')
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False
        
        if self.logger.hasHandlers():
            print("Logger already has handlers.")
            return

        # Directory log
        log_dir = 'logs'
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d')

        log_levels = {
            logging.DEBUG: f'maia_debug_{timestamp}.log',
            logging.INFO: f'maia_info_{timestamp}.log',
            logging.WARNING: f'maia_warning_{timestamp}.log',
            logging.ERROR: f'maia_error_{timestamp}.log',
            logging.CRITICAL: f'maia_critical_{timestamp}.log'
        }

        log_format = '%(asctime)s - %(name)s - %(levelname)s - [%(classname)s] - %(message)s'

        # Handlers file
        for level, filename in log_levels.items():
            file_handler = RotatingFileHandler(
                os.path.join(log_dir, filename),
                maxBytes=10 * 1024 * 1024,
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setLevel(level)
            file_handler.setFormatter(logging.Formatter(log_format))
            file_handler.addFilter(ClassNameInjector())
            self.logger.addHandler(file_handler)

        # Handler console
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter(log_format))
        console_handler.addFilter(ClassNameInjector())
        self.logger.addHandler(console_handler)
        
        
    def _get_caller_class(self) -> str:
        """Get the name of the class that called the logger."""
        frame = inspect.currentframe()
        try:
            # Go up two frames: one for the logging method, one for the caller
            caller_frame = frame.f_back.f_back
            caller_class = caller_frame.f_locals.get('self', None)
            if caller_class is not None:
                return caller_class.__class__.__name__
            return "Unknown"
        finally:
            del frame
    
    def _log(self, level: int, message: str, sender: str):
        """Internal logging method that adds class name to the log record."""
        extra = {'classname': sender}
        self.logger.log(level, message, extra=extra)
    
    def debug(self, message: str, sender: str):
        """Log a debug message."""
        self._log(logging.DEBUG, message, sender)
    
    def info(self, message: str, sender: str):
        """Log an info message."""
        self._log(logging.INFO, message, sender)
    
    def warning(self, message: str, sender: str):
        """Log a warning message."""
        self._log(logging.WARNING, message, sender)
    
    def error(self, message: str, sender: str):
        """Log an error message."""
        self._log(logging.ERROR, message, sender)
    
    def critical(self, message: str, sender: str):
        """Log a critical message."""
        self._log(logging.CRITICAL, message, sender)

# Example usage
if __name__ == "__main__":
    class TestClass:
        def __init__(self):
            self.logger = Logger()
        
        def test_logging(self):
            self.logger.debug("This is a debug message")
            self.logger.info("This is an info message")
            self.logger.warning("This is a warning message")
            self.logger.error("This is an error message")
            self.logger.critical("This is a critical message")
    
    test = TestClass()
    test.test_logging() 