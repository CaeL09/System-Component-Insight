import logging
import os
from datetime import datetime, timedelta
import configparser
from module.logger_manager import LoggerManager
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class EmailConfigManager:
    def __init__(self, config_file):
        self.config_file = config_file
        self.logger = LoggerManager.get_logger(__name__, log_level=logging.DEBUG)
        self.config = configparser.ConfigParser()
        self.read_config()

    def read_config(self):
        if not os.path.isfile(self.config_file):
            self.logger.error(f"Config file {self.config_file} not found.")
            raise FileNotFoundError(f"Config file {self.config_file} not found.")
        
        try:
            with open(self.config_file, 'r') as file:
                content = file.read()
            self.config.read_string(content)
            # self.logger.debug(f"Sections found: {self.config.sections()}")
        except Exception as e:
            self.logger.error(f"Error reading config file: {e}")
            raise

    def get_email_config(self):
        if 'EmailConfig' in self.config:
            return {
                'from_email': self.config.get('EmailConfig', 'from_email'),
                'cc_email': self.config.get('EmailConfig', 'cc_email'),
                'subject': self.config.get('EmailConfig', 'subject'),
                'smtp_server': self.config.get('EmailConfig', 'smtp_server'),
                'smtp_port': self.config.getint('EmailConfig', 'smtp_port')
            }
        else:
            self.logger.error("EmailConfig section not found in config file.")
            raise ValueError("EmailConfig section not found in config file.")

    def get_filter_config(self):
        if 'FilterConfig' in self.config:
            filter_config = {}
            for key, value in self.config.items('FilterConfig'):
                if key == 'href_streamlit':
                    # Handle `href_streamlit` differently to remove brackets and quotes
                    filter_value = value.strip("[]'")  # Strip brackets and single quotes
                else:
                    # Handle wildcard parsing and spaces for other keys
                    filter_values = value.split(',')
                    filter_value = [item.strip().lower() for item in filter_values]
                filter_config[key.lower()] = filter_value
            return filter_config
        else:
            self.logger.error("FilterConfig section not found in config file.")
            raise ValueError("FilterConfig section not found in config file.")    