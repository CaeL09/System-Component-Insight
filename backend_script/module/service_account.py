import configparser
import subprocess
import re
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from module.logger_manager import LoggerManager

class ServiceAccountChecker:
    def __init__(self, config_file):
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.logger = LoggerManager.get_logger(__name__, log_level=logging.DEBUG)
        self.config.read(config_file)
    
    def get_service_account_items(self, due_items):
        items = {}
        for section in due_items:
            if section.startswith('item') and self.config[section].get('method') == 'service account':
                service_names = [name.strip() for name in self.config[section].get('service_name', '').split(',')]
                items[section] = service_names
                self.logger.info(f'Found service account: {section}, {service_names}')
        return items

    # def parse_account_info(self, info):
    #     parsed_info = {}
    #     patterns = {
    #         'username': r'User name\s+(.*)',
    #         'fullname': r'Full Name\s+(.*)',
    #         'comment': r'Comment\s+(.*)',
    #         'active': r'Account active\s+(.*)',
    #         'password_last_set': r'Password last set\s+(.*)',
    #         'password_expires': r'Password expires\s+(.*)',
    #         'last_logon': r'Last logon\s+(.*)'
    #     }

    #     for key, pattern in patterns.items():
    #         match = re.search(pattern, info)
    #         if match:
    #             parsed_info[key] = match.group(1).strip().lower()

    #     parsed_info['status'] = 'online' if parsed_info.get('active', '').lower() == 'yes' else 'offline'
    #     expiration_str = parsed_info.get('password_expires', '')
    #     parsed_info['password_expires'] = expiration_str
    #     parsed_info['days_until_expiration'] = self.calculate_days_until_expiration(expiration_str)

    #     return parsed_info

    def parse_account_info(self, info):
        parsed_info = {}
        patterns = {
            'username': r'User name\s+(.*)',
            'fullname': r'Full Name\s+(.*)',
            'comment': r'Comment\s+(.*)',
            'active': r'Account active\s+(.*)',
            'password_last_set': r'Password last set\s+(.*)',
            'password_expires': r'Password expires\s+(.*)',
            'last_logon': r'Last logon\s+(.*)'
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, info)
            if match:
                parsed_info[key] = match.group(1).strip().lower()

        parsed_info['status'] = 'online' if parsed_info.get('active', '').lower() == 'yes' else 'offline'
        
        # Get expiration_str for calculation
        expiration_str = parsed_info.get('password_expires', '')
        parsed_info['password_expires'] = expiration_str
        parsed_info['days_until_expiration'] = self.calculate_days_until_expiration(expiration_str)

        # Create an ordered dictionary to maintain the desired order
        ordered_parsed_info = {
            'username': parsed_info.get('username'),
            'fullname': parsed_info.get('fullname'),
            'comment': parsed_info.get('comment'),
            'active': parsed_info.get('active'),
            'password_last_set': parsed_info.get('password_last_set'),
            'password_expires': parsed_info.get('password_expires'),
            'days_until_expiration': parsed_info.get('days_until_expiration'),
            'last_logon': parsed_info.get('last_logon'),
            'status': parsed_info.get('status')
        }
        return ordered_parsed_info

    def calculate_days_until_expiration(self, expiration_str):
        date_formats = [
            "%m/%d/%Y %I:%M:%S %p",
            "%m/%d/%Y %I:%M %p",
            "%m/%d/%Y %H:%M:%S",
            "%m/%d/%Y %H:%M",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d %I:%M:%S %p",
            "%Y-%m-%d %I:%M %p"
        ]

        if not expiration_str or not expiration_str.strip():
            self.logger.warning(f"No expiration date provided.")
            return None
        
        expiration_str = expiration_str.strip().lower()
        if expiration_str == "never":
            return None
        
        for date_format in date_formats:
            try:
                expiration_date = datetime.strptime(expiration_str, date_format)
                current_date = datetime.now()
                delta = expiration_date - current_date
                return delta.days
            except ValueError:
                continue
        
        self.logger.error(f"Error parsing date: {expiration_str}. No valid format found.")
        return None

    def retrieve_account_info(self, account_name):
        try:
            result = subprocess.run(['net', 'user', account_name, '/domain'], capture_output=True, text=True, check=True)
            output = result.stdout
            return self.parse_account_info(output)
        except subprocess.CalledProcessError as e:
            self.logger.error(f'Error retrieving info for account: {account_name}\n{e.output}')
            return None

    def check_service_accounts(self, due_items):
        service_account_items = self.get_service_account_items(due_items)
        results = {}

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(self.retrieve_account_info, account_name): (section, account_name)
                       for section, service_names in service_account_items.items()
                       for account_name in service_names}

            for future in as_completed(futures):
                section, account_name = futures[future]
                try:
                    info = future.result()
                    if info:
                        if section not in results:
                            results[section] = []
                        results[section].append(info)
                except Exception as e:
                    self.logger.error(f'Error processing account: {account_name}\n{e}')

        return results
