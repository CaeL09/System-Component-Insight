import os
import configparser
import time
import logging
import subprocess
from threading import Lock
from module.logger_manager import LoggerManager

class NetworkStorageAccessChecker:
    def __init__(self, config_file='config/config.ini'):
        self.config = configparser.ConfigParser()
        self.config.read(config_file)
        self.default_timeout = 5
        self.logger = LoggerManager.get_logger(__name__, log_level=logging.DEBUG)
        self.mutex = Lock()

    def check_access(self):
        access_results = {}
        for section in self.config.sections():
            if section.startswith('item') and self.config[section].get('method') == 'network storage':
                paths = self.config[section].get('path', '').split(',')
                path_results = {path.strip(): self._check_single_folder(path.strip(), self.config[section]) for path in paths if path.strip()}
                access_results[section] = path_results
        return access_results

    def _disconnect_existing_connections(self, networkStorage_path):
        try:
            net_use_list_command = 'net use'
            result = subprocess.run(net_use_list_command, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                existing_connections = result.stdout.splitlines()
                for connection in existing_connections:
                    if networkStorage_path in connection:
                        net_use_delete_command = f'net use {networkStorage_path} /delete /y'
                        del_result = subprocess.run(net_use_delete_command, shell=True, capture_output=True, text=True)
                        if del_result.returncode == 0:
                            self.logger.info(f"Successfully disconnected existing connection to {networkStorage_path}")
                        else:
                            self.logger.error(f"Failed to disconnect existing network connection to {networkStorage_path}: {del_result.stderr.strip()}")
            else:
                self.logger.error(f"Failed to list existing network connections: {result.stderr.strip()}")
        except Exception as e:
            self.logger.error(f"Error during disconnecting existing network connections: {e}")

    def _check_single_folder(self, networkStorage_path, config_section):
        if not networkStorage_path:
            return False

        with self.mutex:
            self._disconnect_existing_connections(networkStorage_path)
            try:
                if config_section.get('username') and config_section.get('password'):
                    username = config_section.get('username')
                    password = config_section.get('password')
                    net_use_command = f'net use {networkStorage_path} /user:{username} {password}'
                    subprocess.run(net_use_command, shell=True, check=True)

                start_time = time.time()
                _ = os.listdir(networkStorage_path)
                elapsed_time = time.time() - start_time

                if config_section.get('username') and config_section.get('password'):
                    self._disconnect_existing_connections(networkStorage_path)

                if elapsed_time < self.default_timeout:
                    return True
                else:
                    self.logger.warning(f"Timeout occurred while accessing folder '{networkStorage_path}'")
                    return False
            except PermissionError:
                self.logger.error(f"Permission denied for '{networkStorage_path}'")
                return False
            except FileNotFoundError:
                self.logger.error(f"Folder not found: '{networkStorage_path}'")
                return False
            except subprocess.CalledProcessError as e:
                self.logger.error(f"Network access error: {e}")
                return False
            except Exception as e:
                self.logger.error(f"Unexpected error: {e}")
                return False
