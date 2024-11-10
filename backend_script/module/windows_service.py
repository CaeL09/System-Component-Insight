import logging
import wmi
import configparser
from module.logger_manager import LoggerManager

class WindowsServiceStatusChecker:
    def __init__(self, server, username, password, service_names):
        self.server = server
        self.username = username
        self.password = password
        self.service_names = service_names
        self.logger = LoggerManager.get_logger(__name__, log_level=logging.DEBUG)

    def check_service_status(self):
        try:
            connection = wmi.WMI(computer=self.server, user=self.username, password=self.password)
            statuses = {}
            for service_name in self.service_names:
                services = connection.Win32_Service(Name=service_name)
                if services:
                    service = services[0]
                    statuses[service_name] = service.State
                    self.logger.info(f"Service {service_name} status: {service.State}")
                else:
                    statuses[service_name] = "service not found"
                    self.logger.info(f"Service {service_name} not found")
            return statuses
        except wmi.x_wmi:
            self.logger.error("Access denied or invalid credentials for server: %s", self.server)
            return "access denied"
        except Exception as e:
            self.logger.exception("Error checking service status: %s", e)
            return None

    @staticmethod
    def read_servers_configuration(config_file='config/config.ini'):
        config = configparser.ConfigParser()
        config.read(config_file)
        servers = []
        for section in config.sections():
            if section.startswith('item'):
                server_config = config[section]
                method = server_config.get('method', '')
                if method == 'windows service':
                    hostname = server_config.get('hostname', '')
                    username = server_config.get('username', '')
                    password = server_config.get('password', '')
                    service_names = server_config.get('service_name', '').split(',')
                    servers.append((hostname, username, password, service_names))
        return servers
