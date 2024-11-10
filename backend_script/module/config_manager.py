import json
import configparser
from datetime import datetime, timedelta
import os
from module.logger_manager import LoggerManager
from module.utils import com_initialized
import logging

class ConfigManager:
    DEFAULT_INTERVAL = timedelta(minutes=5)  # Default to 5 minutes if parsing fails
    INTERVAL_MAP = {
        'min': 'minutes',
        'hr': 'hours',
        'day': 'days'
    }

    def __init__(self, config_file='config/config.ini', last_run_file='data/configManager.json'):
        self.config_file = config_file
        self.last_run_file = last_run_file
        self.logger = LoggerManager.get_logger(__name__, log_level=logging.DEBUG)
        self.config = self.load_config()
        self.last_run = self.load_last_run()
    
    def load_config(self) -> dict:
        """Load configuration from the specified INI file."""
        self.logger.info(f"Loading configuration from {self.config_file}")
        config = configparser.ConfigParser()
        config.optionxform = str
        config.read(self.config_file)
        items = {section: dict(config.items(section)) for section in config.sections() if section.startswith('item') if section != 'item1'}
        # self.logger.debug(f"Loaded configuration: {items}")
        return items

    def load_last_run(self) -> dict:
        """Load last run data from the specified JSON file."""
        self.logger.info(f"Loading last run data from {self.last_run_file}")
        if os.path.exists(self.last_run_file):
            try:
                with open(self.last_run_file, 'r') as file:
                    last_run_data = json.load(file)
                    # self.logger.debug(f"Loaded last run data: {last_run_data}")
                    return last_run_data
            except json.JSONDecodeError as e:
                self.logger.error(f"Error decoding JSON from {self.last_run_file}: {e}")
                return {}
        else:
            self.logger.debug("Last run file does not exist. Starting with an empty dictionary.")
            return {}

    def save_last_run(self):
        """Save the current state of last run data to the JSON file."""
        try:
            with open(self.last_run_file, 'w') as file:
                json.dump(self.last_run, file, indent=4)
                # self.logger.info(f"Last run data successfully saved to {self.last_run_file}")
        except Exception as e:
            self.logger.error(f"Error saving last run data to {self.last_run_file}: {e}")

    def synchronize(self):
        """Synchronize the configuration and last run data."""
        self.logger.info("Synchronizing configuration and last run data.")
        updated = False
        
        for section, items in self.config.items():
            if section not in self.last_run:
                self.last_run[section] = {'last_run': datetime.now().isoformat(), **items}
                self.logger.info(f"Added new item: {section} with data {self.last_run[section]}")
                updated = True
            else:
                current_item = self.last_run[section]
                if any(current_item.get(key) != value for key, value in items.items()):
                    self.last_run[section].update(items)
                    temp_file_path = os.path.join('temp', f"{section}.json")
                    try:
                        os.remove(temp_file_path)
                        self.logger.info(f"Deleted temp file: {temp_file_path}")
                    except FileNotFoundError:
                        self.logger.warning(f"File {temp_file_path} not found, could not delete.")
                    self.logger.info(f"Updated item: {section} with data {self.last_run[section]}")
                    updated = True
        
        for section in list(self.last_run.keys()):
            if section not in self.config:
                self.logger.info(f"Removed item: {section}")
                del self.last_run[section]
                temp_file_path = os.path.join('temp', f"{section}.json")
                try:
                    os.remove(temp_file_path)
                    self.logger.info(f"Deleted temp file: {temp_file_path}")
                except FileNotFoundError:
                    self.logger.warning(f"File {temp_file_path} not found, could not delete.")
                updated = True
        
        if updated:
            self.save_last_run()

    def parse_interval(self, interval_str: str) -> timedelta:
        """Parse an interval string into a timedelta object."""
        for key, value in self.INTERVAL_MAP.items():
            if key in interval_str:
                try:
                    amount = int(interval_str.replace(key, '').strip())
                    return timedelta(**{value: amount})
                except ValueError as e:
                    self.logger.warning(f"Error parsing interval '{interval_str}': {e}")
                    return self.DEFAULT_INTERVAL
        self.logger.warning(f"Unknown interval format '{interval_str}', using default interval.")
        return self.DEFAULT_INTERVAL

    def get_due_items(self, method: str = None) -> list:
        """Get a list of items that are due for processing."""
        due_items = []
        now = datetime.now()
        
        for section, item in self.last_run.items():
            # self.logger.debug(f"Processing item: {section} with details: {item}")
            if not all(key in item for key in ('method', 'last_run', 'interval')):
                self.logger.warning(f"Item '{section}' does not have all required keys (method, last_run, interval)")
                continue
            
            if method and item['method'].lower() != method.lower():
                continue
            
            try:
                last_run_time = datetime.fromisoformat(item['last_run'])
                interval = self.parse_interval(item['interval'])
                if now - last_run_time >= interval:
                    due_items.append(section)
            except ValueError as e:
                self.logger.warning(f"Error parsing last_run timestamp for section '{section}': {e}")
        
        self.logger.debug(f"Due items identified: {due_items}")
        return due_items

    def update_last_run_time(self, section: str):
        """Update the last run time for a given section."""
        section = section.lower()
        if section in self.last_run:
            self.last_run[section]['last_run'] = datetime.now().isoformat()
            self.save_last_run()
            # self.logger.info(f"Updated last_run time for {section} to {self.last_run[section]['last_run']}")
        else:
            self.logger.warning(f"Section '{section}' not found in last_run. Unable to update last_run time.")

    
    def run(self):
        """Run the synchronization and identify due items."""
        self.logger.info("Starting synchronization process.")
        self.synchronize()
        self.logger.info("Synchronization process completed.")
        
        due_items = self.get_due_items()
        self.logger.info(f"Due items: {due_items}")
        return due_items
