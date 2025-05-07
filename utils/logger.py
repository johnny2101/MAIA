import logging
import os
import inspect
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Optional, Dict

class Logger:
    _instance: Optional['Logger'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
            cls._instance._initialize_logger()
        return cls._instance
    
    def _initialize_logger(self):
        """Initialize the logger with file rotation and console handlers."""
        self.logger = logging.getLogger('MAIA')
        self.logger.setLevel(logging.DEBUG)
        
        # Create logs directory if it doesn't exist
        log_dir = 'logs'
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # Generate timestamp for log files
        timestamp = datetime.now().strftime('%Y%m%d')
        
        # Define log levels and their corresponding file names
        log_levels = {
            logging.DEBUG: f'maia_debug_{timestamp}.log',
            logging.INFO: f'maia_info_{timestamp}.log',
            logging.WARNING: f'maia_warning_{timestamp}.log',
            logging.ERROR: f'maia_error_{timestamp}.log',
            logging.CRITICAL: f'maia_critical_{timestamp}.log'
        }
        
        # Create handlers for each log level
        for level, filename in log_levels.items():
            file_handler = RotatingFileHandler(
                os.path.join(log_dir, filename),
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setLevel(level)
            
            # Create formatter for file handler
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - [%(classname)s] - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            
            # Add filter to only log messages of this level
            file_handler.addFilter(lambda record, level=level: record.levelno == level)
            
            # Add handler to logger
            self.logger.addHandler(file_handler)
        
        # Console handler for all levels
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - [%(classname)s] - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
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
    
    def _log(self, level: int, message: str):
        """Internal logging method that adds class name to the log record."""
        extra = {'classname': self._get_caller_class()}
        self.logger.log(level, message, extra=extra)
    
    def debug(self, message: str):
        """Log a debug message."""
        self._log(logging.DEBUG, message)
    
    def info(self, message: str):
        """Log an info message."""
        self._log(logging.INFO, message)
    
    def warning(self, message: str):
        """Log a warning message."""
        self._log(logging.WARNING, message)
    
    def error(self, message: str):
        """Log an error message."""
        self._log(logging.ERROR, message)
    
    def critical(self, message: str):
        """Log a critical message."""
        self._log(logging.CRITICAL, message)

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