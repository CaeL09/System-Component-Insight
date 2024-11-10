import os
import logging
import configparser
import streamlit as st
from functools import lru_cache

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define choices
METHOD_CHOICES = ["server status", "windows service", "web application", "network storage", "database", "disk usage", "service account"]
EMAIL_NOTIFY_CHOICES = ["True", "False"]
DATABASE_CHOICES = ["oracle", "sqlserver", "mysql"]
INTERVAL_UNITS = ["min", "hr", "day"]

# Define driver choices mapping
DRIVER_CHOICES = {
    "Oracle Client 64bit": "driver\\Oracle Client 64bit\\instantclient_11_2",
    "ODBC Driver 17 for SQL Server": "ODBC Driver 17 for SQL Server",
    "Other": ""
}

# Define fields to hide based on method
HIDE_FIELDS = {
    "server status": ['database', 'username', 'password', 'service_name', 'url', 'path', 'database_name', 'server', 'port', 'sid', 'driver', 'query'],
    "windows service": ['database', 'url', 'path', 'database_name', 'server', 'port', 'sid', 'driver', 'query'],
    "web application": ['database', 'hostname', 'username', 'password', 'service_name', 'path', 'database_name', 'server', 'port', 'sid', 'driver', 'query'],
    "network storage": ['database', 'hostname', 'service_name', 'url', 'database_name', 'server', 'port', 'sid', 'driver', 'query'],
    "database": ['hostname', 'service_name', 'url', 'path'],
    "disk usage": ['database', 'service_name', 'url', 'path', 'database_name', 'server', 'port', 'sid', 'driver', 'query'],
    "service account": ['database', 'hostname', 'username', 'password', 'url', 'path', 'database_name', 'server', 'port', 'sid', 'driver', 'query']
}

@lru_cache(maxsize=1)
def read_config(file_path):
    """Read the configuration file with caching."""
    config = configparser.ConfigParser()
    try:
        config.read(file_path)
        logging.info("Config file read successfully.")
    except Exception as e:
        logging.error(f"Error reading config file: {e}")
        st.error(f"Error reading config file: {e}")
    return config

def write_config(file_path, config, sections=None):
    """Write to the configuration file."""
    try:
        with open(file_path, 'r+') as configfile:
            current_config = configparser.ConfigParser()
            current_config.read_file(configfile)

            if sections:
                for section in sections:
                    if section in config:
                        if not current_config.has_section(section):
                            current_config.add_section(section)
                        for key, value in config[section].items():
                            current_config.set(section, key, value)
                    else:
                        if current_config.has_section(section):
                            current_config.remove_section(section)
            else:
                for section in config.sections():
                    if not current_config.has_section(section):
                        current_config.add_section(section)
                    for key, value in config[section].items():
                        current_config.set(section, key, value)

            configfile.seek(0)
            current_config.write(configfile)
            configfile.truncate()
            
        logging.info("Config file updated successfully.")
        read_config.cache_clear()  # Clear the cache after writing
    except Exception as e:
        logging.error(f"Error updating config file: {e}")
        st.error(f"Error updating config file: {e}")

def remove_key_from_section(file_path, section, key):
    """Remove a key from a section in the configuration file."""
    try:
        config = configparser.ConfigParser()
        config.read(file_path)
        if config.has_section(section):
            config.remove_option(section, key)
            with open(file_path, 'w') as configfile:
                config.write(configfile)
            logging.info(f"Key '{key}' removed from section '{section}' successfully.")
            read_config.cache_clear()  # Clear the cache after writing
        else:
            logging.error(f"Section '{section}' not found.")
            st.error(f"Section '{section}' not found.")
    except Exception as e:
        logging.error(f"Error removing key from section: {e}")
        st.error(f"Error removing key from section: {e}")

def create_sample_config(file_path):
    """Create a sample configuration file if it doesn't exist."""
    sample_config = configparser.ConfigParser()
    sample_config['item1'] = {
        'name': '',
        'description': '',
        'site': '',
        'method': '',
        'database': '',
        'interval': '',
        'hostname': '',
        'username': '',
        'password': '',
        'service_name': '',
        'url': '',
        'path': '',
        'database_name': '',
        'server': '',
        'port': '',
        'sid': '',
        'driver': '',
        'query': '',
        'email_notify': '',
        'recipient': ''
    }
    sample_config['function'] = {
        'ping_servers': 'True',
        'check_windows_service': 'True',
        'check_app_service': 'True',
        'check_network_storage': 'True',
        'check_database_connections': 'True',
        'check_disk_usage': 'True',
        'check_service_account': 'True',
        'manage_json_files': 'True',
        'emailStatus_notifier': 'False'
    }
    sample_config['FilterConfig'] = {
        'status': 'offline, query error, service not found, access denied',
        'free': '95G',
        'usage_percent': '98%%'
    }
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    write_config(file_path, sample_config)

def split_interval(interval):
    """Split interval into number and unit."""
    for unit in INTERVAL_UNITS:
        if unit in interval:
            number = interval.replace(unit, '').strip()
            return number, unit
    return interval, ''

def is_hidden(field, method, database):
    """Check if a field should be hidden based on method and database."""
    hidden = field in HIDE_FIELDS.get(method, [])
    if database == 'oracle' and field in ['database_name', 'hostname']:
        hidden = True
    if database == 'sqlserver' and field in ['database_name', 'sid', 'hostname']:
        hidden = True
    if database == 'mysql' and field in ['sid', 'driver', 'hostname']:
        hidden = True
    return hidden

def create_input_widget(key, value, label, hidden, col, unique_id, disabled=False):
    """Create an input widget."""
    if hidden:
        return ""
    if key == 'email_notify':
        value = value.lower()
        email_choices = [choice.lower() for choice in EMAIL_NOTIFY_CHOICES]
        return col.selectbox(label, EMAIL_NOTIFY_CHOICES, index=email_choices.index(value) if value in email_choices else 0, key=f"{key}_{label}_{unique_id}")
    if key == 'database':
        database_choice = col.selectbox(label, [value] + DATABASE_CHOICES, key=f"{key}_{label}_{unique_id}")
        st.session_state[f"{key}_{label}_{unique_id}_database"] = database_choice
        return database_choice
    elif key == 'interval':
        interval_col1, interval_col2 = col.columns([2, 1])
        number, unit = split_interval(value)
        if disabled:
            interval_number = interval_col1.text_input(f"{label} Number", number, key=f"{key}_number_{label}_{unique_id}", disabled=True)
            interval_unit = interval_col2.selectbox(f"{label} Unit", INTERVAL_UNITS, index=INTERVAL_UNITS.index(unit) if unit in INTERVAL_UNITS else 0, key=f"{key}_unit_{label}_{unique_id}", disabled=True)
        else:
            interval_number = interval_col1.text_input(f"{label} Number", number, key=f"{key}_number_{label}_{unique_id}")
            interval_unit = interval_col2.selectbox(f"{label} Unit", INTERVAL_UNITS, index=INTERVAL_UNITS.index(unit) if unit in INTERVAL_UNITS else 0, key=f"{key}_unit_{label}_{unique_id}")
        return interval_number, interval_unit
    elif key in ['description', 'query', 'recipient', 'hostname', 'url', 'service_name']:
        return col.text_area(label, value, key=f"{key}_{label}_{unique_id}")
    elif key == 'driver':
        driver_titles = list(DRIVER_CHOICES.keys())
        driver_values = list(DRIVER_CHOICES.values())
        database_choice = st.session_state.get(f"database_{label}_{unique_id}_database", "")
        current_value_index = driver_values.index(database_choice) if database_choice else driver_values.index(value) if value in driver_values else 0
        selected_title = col.selectbox(label, driver_titles, index=current_value_index, key=f"{key}_{label}_{unique_id}")
        if selected_title == "Other":
            return col.text_input(f"Specify {label}", key=f"{key}_other_{label}_{unique_id}")
        return DRIVER_CHOICES[selected_title]
    elif key == 'password':
        return col.text_input(label, value, type="password", key=f"{key}_{label}_{unique_id}")
    else:
        return col.text_input(label, value, key=f"{key}_{label}_{unique_id}")

