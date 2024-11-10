import json
import os
import pythoncom
import configparser
from functools import wraps
from datetime import datetime, timedelta
from module.disk_usage import DiskUsage
import threading
import uuid

# Decorator for COM initialization
def com_initialized(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        pythoncom.CoInitialize()
        try:
            return func(*args, **kwargs)
        finally:
            pythoncom.CoUninitialize()
    return wrapper

def create_item_data(config, extra_data):
    item_data = {
        'method': config.get("method", ''),
        'name': config.get("name", ''),
        'description': config.get("description", ''),
        'site': config.get("site", ''),
        'interval': config.get("interval", ''),
        'hostname': config.get("hostname", ''),
        'email_notify': config.get("email_notify", ''),
        'recipient': config.get("recipient", '').split(',')
    }
    item_data.update(extra_data)
    return item_data



# def save_results_to_json(section_name, data, logger):
#     """Save the results to a JSON file named after the section."""
#     filename = section_name.strip('[]')
#     output_folder = 'temp'
#     os.makedirs(output_folder, exist_ok=True)
#     output_filename = os.path.join(output_folder, f"{filename}.json")
#     try:
#         with open(output_filename, 'w') as json_file:
#             json.dump(data, json_file, indent=4)
#         # logger.info(f"Results for section {section_name} have been written to {output_filename}")
#     except Exception as e:
#         logger.error(f"Failed to save results for section {section_name} to {output_filename}: {e}")

# @com_initialized
def save_results_to_json(section_name, data, logger):
    """Save the results to a JSON file named after the section, ensuring thread-safe writes."""
    filename = section_name.strip('[]')
    output_folder = 'temp'
    os.makedirs(output_folder, exist_ok=True)
    output_filename = os.path.join(output_folder, f"{filename}.json")
    # Generate a unique temporary filename
    unique_tmp_filename = output_filename + f".{uuid.uuid4()}.tmp"
    # Use a lock to prevent race conditions
    lock = threading.Lock()

    try:
        with lock:
            # Write data to the unique temporary file
            with open(unique_tmp_filename, 'w') as json_file:
                json.dump(data, json_file, indent=4)
            
            # Rename the temporary file to the final filename
            if os.path.exists(output_filename):
                os.remove(output_filename)  # Remove the existing file first
            
            os.rename(unique_tmp_filename, output_filename)
            # logger.info(f"Results for section {section_name} have been written to {output_filename}")
    
    except Exception as e:
        logger.error(f"Failed to save results for section {section_name} to {output_filename}: {e}")
        # Clean up the temporary file in case of an error
        if os.path.exists(unique_tmp_filename):
            os.remove(unique_tmp_filename)


def manage_json_files(logger, temp_folder, data_file):
    # Create data directory if it doesn't exist
    os.makedirs(os.path.dirname(data_file), exist_ok=True)
    collected_data = []  # This will store the data from all JSON files

    for filename in os.listdir(temp_folder):
        if filename.endswith('.json'):
            file_path = os.path.join(temp_folder, filename)

            # Check if the file name starts with "item"
            if filename.startswith('item'):
                with open(file_path, 'r') as file:
                    try:
                        data = json.load(file)
                        item_name = os.path.splitext(filename)[0]  # Get the filename without the extension            
                        if isinstance(data, list):
                            # Add the item name as the first field in each entry of the list
                            for entry in data:
                                # Ensure 'item' is the first key by creating a new dict
                                entry_with_item_first = {'item_no': item_name}
                                entry_with_item_first.update(entry)
                                collected_data.append(entry_with_item_first)
                        else:
                            # Add the item name as the first field in the JSON object
                            entry_with_item_first = {'item_no#': item_name}
                            entry_with_item_first.update(data)
                            collected_data.append(entry_with_item_first)                    
                    except json.JSONDecodeError:
                        logger.error(f"Error decoding JSON from file: {filename}")
    
    # Write collected data to data_file, overwriting any existing content
    with open(data_file, 'w') as df:
        json.dump(collected_data, df, indent=4)



def disk_process_section(logger, config, section, results_dict, manager):
    try:
        hostname_list = config.get(section, 'hostname').split(',')
        username = config.get(section, 'username')
        password = config.get(section, 'password')

        item_data = create_item_data(config[section], {})

        for hostname in hostname_list:
            hostname = hostname.strip()
            disk_process_hostname(logger, hostname, username, password, section, results_dict, item_data.copy(), manager)

    except configparser.NoOptionError as e:
        logger.error(f"Missing configuration option in {section}: {e}")
    except configparser.NoSectionError as e:
        logger.error(f"Missing configuration section: {e}")
    except Exception as e:
        logger.error(f"Error processing {section}: {e}")

def disk_process_hostname(logger, hostname, username, password, section, results_dict, item_data, manager):
    try:
        disk_usage = DiskUsage(hostname, username, password)
        if disk_usage.os_type is None:
            logger.error(f"Could not determine OS type for {hostname}. Skipping disk usage check.")
            item_data.update({
                'hostname': hostname,
                'status': 'offline'
            })
            if section not in results_dict:
                results_dict[section] = []
            results_dict[section].append(dict(item_data))
            return

        result = retrieve_and_store_disk_usage(logger, disk_usage, hostname, item_data)
        manager.update_last_run_time(section)
        if result:
            if section not in results_dict:
                results_dict[section] = []
            results_dict[section].extend(result)
    except Exception as e:
        logger.error(f"Error initializing or processing DiskUsage for {hostname}: {e}")
        item_data.update({
            'hostname': hostname,
            'status': 'offline'
        })
        if section not in results_dict:
            results_dict[section] = []
        results_dict[section].append(dict(item_data))

def retrieve_and_store_disk_usage(logger, disk_usage, hostname, item_data):
    try:
        disk_info = disk_usage.get_disk_usage()
        status = "online" if disk_info else "offline"
        if disk_info is None:
            logger.error(f"Failed to retrieve disk usage for {hostname}.")
            item_data.update({
                'hostname': hostname,
                'status': status
            })
            return [dict(item_data)]

        data = []

        for disk_drive, info in disk_info.items():
            item_data.update({
                'hostname': hostname,
                'drive' if disk_usage.os_type == 'Windows' else 'filesystem': disk_drive,
                'total': info['Total'],
                'used': info['Used'],
                'free': info['Free'],
                'usage_percent': info['Percent'],
                'mounted_on': info.get('Mounted on', ''),  # 'Mounted on' is Linux-specific
                'status': status
            })
            data.append(dict(item_data))  # Append a copy of item_data to data list
        
        return data
    except Exception as e:
        logger.error(f"Error retrieving or storing disk usage data for {hostname}: {e}")
        item_data.update({
            'hostname': hostname,
            'status': 'offline'
        })
        return [dict(item_data)]

