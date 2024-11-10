import json
import smtplib
import os
import re
import logging
from datetime import datetime
from module.logger_manager import LoggerManager
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sqlite3
import ijson
from jinja2 import Environment, FileSystemLoader
from collections import defaultdict

class StatusNotifier:
    def __init__(self, json_file, email_config, filter_config, last_sent_db='data/last_sent_times.db'):
        self.json_file = json_file
        self.email_config = email_config
        self.filter_config = filter_config
        self.last_sent_db = last_sent_db
        self.logger = LoggerManager.get_logger(__name__, log_level=logging.DEBUG)
        # self.logger.setLevel(logging.DEBUG)
        self.data = []
        self.filtered_data = []
        self.conn = self.init_db()
        self.env = Environment(loader=FileSystemLoader('templates'))

    def init_db(self):
        """Initialize SQLite database to store last sent times."""
        with sqlite3.connect(self.last_sent_db) as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS last_sent_times (
                            item_key TEXT PRIMARY KEY, 
                            last_sent_time TEXT)''')
        return conn

    def __del__(self):
        """Ensure that the database connection is closed."""
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()

    def get_last_sent_time(self, item_key):
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute("SELECT last_sent_time FROM last_sent_times WHERE item_key = ?", (item_key,))
            result = cursor.fetchone()
            return result[0] if result else None

    def update_last_sent_time(self, item_key, current_time):
        with self.conn:
            self.conn.execute("REPLACE INTO last_sent_times (item_key, last_sent_time) VALUES (?, ?)", 
                              (item_key, current_time))

    def read_json(self):
        if not os.path.isfile(self.json_file):
            self.logger.error(f"JSON file {self.json_file} not found.")
            return

        try:
            with open(self.json_file, 'r') as file:
                self.data = [
                    {k.lower(): v for k, v in item.items()}
                    for item in ijson.items(file, 'item')
                ]
            # self.logger.debug(f"Loaded JSON data: {self.data}")
        except (json.JSONDecodeError, Exception) as e:
            self.logger.error(f"Error reading JSON file: {e}")
            self.data = []

    def interval_to_seconds(self, interval_str):
        """Convert interval string (e.g., '1hr') to seconds."""
        match = re.search(r'\d+', interval_str)
        if not match:
            self.logger.error(f"Invalid interval string: {interval_str}")
            return 0
        num = int(match.group())
        unit_multipliers = {
            'min': 60,
            'hr': 3600,
            'day': 86400
        }
        for unit, multiplier in unit_multipliers.items():
            if unit in interval_str:
                return num * multiplier
        return 0

    def should_send_email(self, item):
        """Check if email should be sent based on interval and last sent time."""
        interval_str = item.get('interval', '0min')
        item_key = item.get('item_no', str(item))
        last_sent_time = self.get_last_sent_time(item_key)
        current_time = datetime.now()

        if last_sent_time:
            last_sent_time = datetime.strptime(last_sent_time, '%Y-%m-%d %H:%M:%S')
            interval_seconds = self.interval_to_seconds(interval_str)
            if (current_time - last_sent_time).total_seconds() < interval_seconds:
                self.logger.debug(f"Skipping email for item {item_key} as interval has not elapsed.")
                return False

        self.logger.debug(f"Email will be sent for item {item_key}.")
        self.update_last_sent_time(item_key, current_time.strftime('%Y-%m-%d %H:%M:%S'))
        return True

    def filter_data(self):
        """Filters the loaded data based on the filter configuration."""

        def extract_numeric(value):
            if not value:
                return None
            match = re.search(r"[-+]?\d*\.?\d+|\d+", str(value))
            return float(match.group()) if match else None

        def match_condition(item_value, filter_values):
            item_value_str = str(item_value).lower()

            for filter_value in filter_values:
                filter_value_str = str(filter_value).lower()

                if filter_value_str.startswith('>'):
                    item_numeric = extract_numeric(item_value_str)
                    filter_numeric = extract_numeric(filter_value_str[1:])
                    if item_numeric is not None and filter_numeric is not None and item_numeric > filter_numeric:
                        return True  # Match found, return True

                elif filter_value_str.startswith('<'):
                    item_numeric = extract_numeric(item_value_str)
                    filter_numeric = extract_numeric(filter_value_str[1:])
                    if item_numeric is not None and filter_numeric is not None and item_numeric < filter_numeric:
                        return True  # Match found, return True

                elif filter_value_str.startswith('like'):
                    like_pattern = filter_value_str[5:].strip()
                    like_pattern = re.escape(like_pattern).replace(r'\%', '.*')
                    like_pattern = f".*{like_pattern}.*"
                    if re.search(like_pattern, item_value_str):
                        return True  # Match found, return True

                elif item_value_str == filter_value_str:
                    return True  # Direct match found, return True

            return False  # No match found

        self.filtered_data = [
            item for item in self.data
            if item.get('email_notify', 'false').lower() == 'true' and any(
                match_condition(item.get(key_name, ''), filter_values)
                for key_name, filter_values in self.filter_config.items()
                if key_name != 'href_streamlit'
            )
        ]

        self.filtered_data = list({json.dumps(d, sort_keys=True): d for d in self.filtered_data}.values())
        self.logger.debug(f"Filtered data: {self.filtered_data}")

    def send_email(self):
        carbon_copy = self.email_config.get('cc_email')
        all_valid_items = []
        all_recipients = set()

        # Group data by item_no
        valid_groups = defaultdict(list)
        for item in self.filtered_data:
            item_no = item.get('item_no')
            if item_no:
                valid_groups[item_no].append(item)

        for item_no, items in valid_groups.items():
            # Check if email should be sent for this group of items
            if not self.should_send_email(items[0]):
                continue

            self.logger.info(f"Preparing to send group of items with item_no: {item_no}")

            # Collect recipients from all items in the group
            for item in items:
                recipient = item.get('recipient')
                if recipient:
                    if isinstance(recipient, str):
                        all_recipients.add(recipient.strip())
                    elif isinstance(recipient, list):
                        all_recipients.update(rec.strip() for rec in recipient)

            # Add all valid items from this group to the final list
            all_valid_items.extend(items)

        if not all_valid_items or not all_recipients:
            self.logger.info("No items to notify.")
            return

        # Generate a single email with all valid items
        recipients_list = list(all_recipients)
        table = self.create_html_table(all_valid_items)
        body = self.create_email_body(table, all_valid_items)

        msg = MIMEMultipart()
        msg['From'] = self.email_config['from_email']
        msg['To'] = ', '.join(recipients_list)
        if carbon_copy:
            msg['Cc'] = carbon_copy
        msg['Subject'] = self.email_config['subject']
        msg.attach(MIMEText(body, 'html'))

        try:
            self.logger.info("Connecting to the SMTP server...")
            with smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port'], timeout=10) as server:
                # server.set_debuglevel(1)
                self.logger.info("Sending email...")
                server.sendmail(self.email_config['from_email'], recipients_list + ([carbon_copy] if carbon_copy else []), msg.as_string())
                self.logger.info("Email sent successfully.")

        except Exception as e:
            self.logger.error(f"Failed to send email: {e}")


    def create_html_table(self, sorted_data):
        # Use the already initialized environment to load the template
        template = self.env.get_template('table.html')

        # Predefined order for columns
        predefined_order = [
            'item_no', 'method', 'name', 'description', 'site', 'interval', 'database', 'hostname', 'status',
            'response_time', 'service_name', 'url', 'database_name', 'path', 'result',
            'drive', 'total', 'used', 'free', 'usage_percent', 'mounted_on',
            'username', 'fullname', 'active', 'password_last_set', 'password_expires', 'days_until_expiration', 'last_logon'
        ]

        # Removing excluded columns and sorting based on predefined order
        excluded_columns = {'recipient', 'query', 'comment', 'email_notify'}
        all_columns = {key for item in sorted_data for key in item.keys() if key not in excluded_columns}
        sorted_columns = [col for col in predefined_order if col in all_columns]
        sorted_columns += [col for col in all_columns if col not in predefined_order]

        # Rendering the table using the Jinja2 template
        return template.render(sorted_columns=sorted_columns, sorted_data=sorted_data)

    def create_email_body(self, table, valid_items):
        # Generate matching conditions specifically for the items being emailed
        matching_conditions = {}
        for item in valid_items:
            for key_name, filter_values in self.filter_config.items():
                if key_name != 'href_streamlit' and key_name in item:
                    if key_name not in matching_conditions:
                        matching_conditions[key_name] = set()
                    matching_conditions[key_name].add(str(item[key_name]))

        # Convert matching conditions to a string
        conditions_str = "; ".join(
            f"'{key}' in '{', '.join(map(str, values))}'" for key, values in matching_conditions.items()
        )

        # Use Jinja2 to render the email body with the conditions and the table
        template = self.env.get_template('email_body.html')
        return template.render(conditions_str=conditions_str, table=table)
