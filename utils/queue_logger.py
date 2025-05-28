import logging
import os
import inspect
from logging.handlers import RotatingFileHandler
from datetime import datetime
import time
from typing import Optional
from core.message_broker import MessageConsumer
from core.message_broker2 import MessageBroker


class ClassNameInjector(logging.Filter):
    def filter(self, record):
        if not hasattr(record, 'classname'):
            record.classname = 'N/A'
        return True

class QueueLogger:
    _instance: Optional['QueueLogger'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_logger()
        return cls._instance

    def _initialize_logger(self):
        print("Initializing logger...")
        self.logger = logging.getLogger('MAIA')
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
        
        # Config RabbitMQ
        message_broker_config = {
            'host': 'localhost',
            'port': 5672,
            'username': 'admin',
            'password': 'password',
            'virtual_host': '/'
        }
        self.message_broker = MessageConsumer(message_broker_config)

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

    def _log(self, level: int, sender: str, message: str):
        extra = {'classname': sender}
        self.logger.log(level, message, extra=extra)

    def debug(self, sender, message: str):
        self._log(logging.DEBUG, sender, message)

    def info(self, sender, message: str):
        self._log(logging.INFO, sender, message)

    def warning(self, sender, message: str):
        self._log(logging.WARNING, sender, message)

    def error(self, sender, message: str):
        self._log(logging.ERROR, sender, message)

    def critical(self, sender, message: str):
        self._log(logging.CRITICAL, sender, message)

    def auto_log(self):
        self.message_broker.connect()
        print("QueueLogger: Subscribing to messages...")

        def log_everything(**kwargs):
            print("QueueLogger: Received a message")
            try:
                method, properties, body = kwargs['method'], kwargs['properties'], kwargs['body']
            except KeyError as e:
                print('QueueLogger', f'Error unpacking message: {e}')
                return
            try:
                sender = method.routing_key.split('.')[0]
                severity = method.routing_key.split('.')[-1]
                message = body.decode()

                if severity == 'debug':
                    self.debug(sender, message)
                elif severity == 'info':
                    self.info(sender, message)
                elif severity == 'warning':
                    self.warning(sender, message)
                elif severity == 'error':
                    self.error(sender, message)
                elif severity == 'critical':
                    self.critical(sender, message)
                else:
                    self.info(sender, f"(UNKNOWN LEVEL) {message}")
            except Exception as e:
                self.error('QueueLogger', f'Failed to log message: {e}')

        self.message_broker.subscribe("*.log.*", log_everything)


# Test locale
if __name__ == "__main__":
    class TestClass:
        def __init__(self):
            self.logger = QueueLogger()

        def test_logging(self):
            self.logger.auto_log()
            while True:
                time.sleep(1)
    
    test = TestClass()
    test.test_logging()
