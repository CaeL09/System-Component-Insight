import subprocess
import platform
import re
import logging
import time
from module.logger_manager import LoggerManager

class ServerPinger:
    def __init__(self, last_run_data, retries=3, delay=2):
        self.servers = last_run_data
        self.logger = LoggerManager.get_logger(__name__, log_level=logging.DEBUG)
        self.retries = retries
        self.delay = delay

    # def _ping(self, server):
    #     param = '-n' if platform.system().lower() == 'windows' else '-c'
    #     try:
    #         output = subprocess.check_output(
    #             ['ping', param, '1', server],
    #             stderr=subprocess.STDOUT,
    #             universal_newlines=True
    #         )
    #         match = re.search(r'time[<|=](\d+(\.\d+)?)ms', output)
    #         if match:
    #             return float(match.group(1))
    #         return None
    #     except subprocess.CalledProcessError as e:
    #         self.logger.error(f"Ping failed for {server}: {e}")
    #         return None

    def _ping(self, server):
        param = '-n' if platform.system().lower() == 'windows' else '-c'
        attempt = 0
        while attempt < self.retries:
            try:
                output = subprocess.check_output(
                    ['ping', param, '1', server],
                    stderr=subprocess.STDOUT,
                    universal_newlines=True
                )
                match = re.search(r'time[<|=](\d+(\.\d+)?)ms', output)
                if match:
                    return float(match.group(1))
                return None
            except subprocess.CalledProcessError as e:
                attempt += 1
                self.logger.error(f"Ping failed for {server}, attempt {attempt} of {self.retries}: {e}")
                if attempt < self.retries:
                    time.sleep(self.delay)
        return None

    def ping_hostnames(self, hostnames):
        response_times = []
        for hostname in hostnames:
            hostname = hostname.strip()
            if hostname:
                response_time = self._ping(hostname)
                self.logger.info(f"Ping result for hostname '{hostname}': {response_time} ms")
                response_times.append({
                    "hostname": hostname,
                    "response_time": response_time
                })
        return response_times

    def ping_server(self, server_info):
        hostnames = server_info["hostname"].split(',')
        return self.ping_hostnames(hostnames)

    def ping_servers(self):
        results = []
        for info in self.servers:
            hostname_responses = self.ping_server(info)
            for response in hostname_responses:
                result_info = info.copy()
                result_info.update(response)
                results.append(result_info)
        return results
