import os
import logging
from logging.handlers import RotatingFileHandler

# class LoggerManager:
#     _instance = None

#     def __new__(cls, *args, **kwargs):
#         if not cls._instance:
#             cls._instance = super(LoggerManager, cls).__new__(cls, *args, **kwargs)
#             cls._instance._initialize(*args, **kwargs)
#         return cls._instance

#     def _initialize(self, log_folder='log', log_file='app.log', max_bytes=10*1024*1024, backup_count=5):
#         self.logger = logging.getLogger()
#         self.logger.setLevel(logging.INFO)
#         self.formatter = logging.Formatter('%(asctime)s - %(name)s - %(funcName)s - %(levelname)s - %(message)s')

#         self._setup_console_handler()
#         self._setup_file_handler(log_folder, log_file, max_bytes, backup_count)

#     def _setup_console_handler(self):
#         ch = logging.StreamHandler()
#         ch.setLevel(logging.INFO)
#         ch.setFormatter(self.formatter)
#         self.logger.addHandler(ch)

#     def _setup_file_handler(self, log_folder, log_file, max_bytes, backup_count):
#         if not os.path.exists(log_folder):
#             os.makedirs(log_folder)
#         log_file_path = os.path.join(log_folder, log_file)
#         fh = RotatingFileHandler(log_file_path, maxBytes=max_bytes, backupCount=backup_count)
#         fh.setLevel(logging.INFO)
#         fh.setFormatter(self.formatter)
#         self.logger.addHandler(fh)

    # @classmethod
    # def get_logger(cls):
    #     if cls._instance is None:
    #         cls._instance = LoggerManager()
    #     return cls._instance.logger

    # @classmethod
    # def get_logger(cls, name):
    #     if cls._instance is None:
    #         cls._instance = LoggerManager()
    #     return cls._instance.logger.getChild(name)


class LoggerManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        # Ensure that only one instance is created (singleton pattern)
        if not cls._instance:
            cls._instance = super(LoggerManager, cls).__new__(cls)
            # Initialize the instance with provided arguments
            cls._instance._initialize(**kwargs)
        return cls._instance

    def _initialize(self, log_folder='log', log_file='app.log', max_bytes=10*1024*1024, backup_count=5, log_level=logging.DEBUG):
        # Initialize logger only once
        if hasattr(self, 'logger'):
            return

        self.logger = logging.getLogger()
        self.logger.setLevel(log_level)
        self.formatter = logging.Formatter('%(asctime)s - %(name)s - %(funcName)s - %(levelname)s - %(message)s')

        if not self.logger.hasHandlers():
            self._setup_console_handler(log_level)
            self._setup_file_handler(log_folder, log_file, max_bytes, backup_count, log_level)

    def _setup_console_handler(self, log_level):
        ch = logging.StreamHandler()
        ch.setLevel(log_level)
        ch.setFormatter(self.formatter)
        self.logger.addHandler(ch)

    def _setup_file_handler(self, log_folder, log_file, max_bytes, backup_count, log_level):
        if not os.path.exists(log_folder):
            os.makedirs(log_folder)
        log_file_path = os.path.join(log_folder, log_file)
        fh = RotatingFileHandler(log_file_path, maxBytes=max_bytes, backupCount=backup_count)
        fh.setLevel(log_level)
        fh.setFormatter(self.formatter)
        self.logger.addHandler(fh)

    @classmethod
    def get_logger(cls, name='root', log_level=logging.DEBUG):
        if cls._instance is None:
            cls._instance = LoggerManager(log_level=log_level)
        return cls._instance.logger.getChild(name)