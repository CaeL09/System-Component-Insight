# DATE	     WHO			COMMENTS
# ---------- -------------- ----------------------------------------------
# 05/21/2024 Elvin Yalung   Author
# 06/10/2024 Elvin Yalung   Added EmailStatusNotifier.py: Notifies users based on status conditions.
# 06/17/2024 Elvin Yalung   Added ServerDiskChecker.py: Checks and displays disk usage for both Windows and Linux operating systems.
#                           Improved StatusNotifier: Now parses FilterConfig (in config.ini) to handle multiple filter conditions.
#                           Improved create_html_table and create_email_body functions: Dynamically generate filtered data.
#                           Added a Option to Conditionally Execute Functions Based on Boolean Conditions in config.ini
#
# Script Function:  This Python tool monitors servers and services as per user-configured settings in config.ini. 
#                   It conducts various checks including server pinging, Windows service, web service, network storage, 
#                   database connection, disk usage, and domain account checks and can trigger email alerts according to predefined conditions.
# 
# Version 1.3.0
# 07/10/2024 Elvin Yalung   Refined logic in various functions, adding additional validations.
# 07/26/2024 Elvin Yalung   Added functionality to retrieve details of domain service accounts, including their active status.
# 08/17/2024 Elvin Yalung   Enhanced email status notifier to validate and respect item intervals before sending alerts.
#                           Implemented support for "<, >, like" operators in predefined alert conditions.
# Version 1.3.1
#11/28/2024 Elvin Yalung    v.1.3.1 Added the status summary chart of records for each method to Home page.

########################
# IMPORT MODULES
########################

import argparse
import logging
import configparser
import sys
import os
import psutil
import time
from datetime import datetime
from multiprocessing import Pool

from apscheduler.schedulers.background import BackgroundScheduler

from module._function import (
    check_database_connections, check_disk_usage, check_network_storage, 
    check_service_account, check_web_application, check_windows_service, 
    emailStatus_notifier, ping_servers
)
from module.config_manager import ConfigManager
from module.logger_manager import LoggerManager
from module.utils import manage_json_files

def clear_screen():
    """Clear the terminal screen based on the OS type."""
    os.system('cls' if os.name == 'nt' else 'clear')

def validate_config(config):
    """Validate the necessary sections and options in the config file."""
    required_sections = ['function', 'scheduler']
    for section in required_sections:
        if section not in config:
            raise ValueError(f"Missing required section: {section}")

def run_check_wrapper(func, logger, manager):
    """Wrapper function to handle exceptions and logging."""
    try:
        func(logger, manager)
    except Exception as exc:
        logger.error(f"{func.__name__} generated an exception: {exc}", exc_info=True)
    else:
        logger.info(f"{func.__name__} completed successfully.")

def run_checks():
    """Run the status checks and write the results to JSON files."""
    logger = LoggerManager.get_logger(__name__, log_level=logging.DEBUG)
    config_ini_path = 'config/config.ini'

    logger.info("=" * 92)
    logger.info("Starting status checks...")
    logger.info("=" * 92)

    try:
        manager = ConfigManager()
        manager.run()

        config = configparser.ConfigParser()
        config.read(config_ini_path)

        validate_config(config)

        # Mapping configuration keys to their respective functions
        config_functions = {
            'server_status': ping_servers,
            'windows_service': check_windows_service,
            'web_application': check_web_application,
            'network_storage': check_network_storage,
            'database': check_database_connections,
            'disk_usage': check_disk_usage,
            'service_account': check_service_account
        }

        # Execute selected functions in parallel using multiprocessing
        functions = [
            func for key, func in config_functions.items() 
            if config.getboolean('function', key, fallback=False)
        ]

        if not functions:
            logger.warning("No functions selected for execution.")
            return

        with Pool(len(functions)) as pool:
            pool.starmap(run_check_wrapper, [(func, logger, manager) for func in functions])

        # Manage JSON files and send email notifications if enabled
        if config.getboolean('function', 'data_manager', fallback=False):
            manage_json_files(logger, 'temp', 'data/data.json')

        if config.getboolean('function', 'email_alert', fallback=False):
            emailStatus_notifier(logger)

    except Exception as e:
        logger.error(f"An error occurred during the status checks: {e}", exc_info=True)
    finally:
        logger.info("=" * 92)
        logger.info("Status checks completed.")
        logger.info("=" * 92)

def restart_application(logger):
    """Restart the application."""
    logger.info("Memory usage is too high. Restarting the application to free up memory.")
    python = sys.executable
    os.execv(python, [python] + sys.argv)

def monitor_memory_and_restart(logger, threshold=500):
    """Monitor memory usage and restart the application if it exceeds the threshold."""
    memory_usage_mb = psutil.Process(os.getpid()).memory_info().rss / 1024**2
    logger.info(f"Current Memory Usage: {memory_usage_mb:.2f} MB")
    if memory_usage_mb > threshold:
        logger.warning(f"Memory usage exceeded threshold of {threshold} MB. Restarting application.")
        restart_application(logger)

def main():
    clear_screen()
    run_checks()

    parser = argparse.ArgumentParser(description='Run status checks with configurable scheduler.')
    parser.add_argument('--interval', type=int, help='Interval in minutes for the scheduler.')
    args = parser.parse_args()

    config = configparser.ConfigParser()
    config.read('config/config.ini')

    interval_minutes = args.interval or config.getint('scheduler', 'interval_minutes', fallback=1)
    logger = LoggerManager.get_logger(__name__, log_level=logging.DEBUG)
    
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_checks, 'interval', minutes=interval_minutes, next_run_time=datetime.now())

    # Monitor memory usage every 15 minutes and restart if necessary
    scheduler.add_job(monitor_memory_and_restart, 'interval', minutes=15, args=[logger])

    scheduler.start()

    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()

if __name__ == "__main__":
    main()
