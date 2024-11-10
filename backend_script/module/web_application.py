import logging
import requests
import ssl
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from module.logger_manager import LoggerManager

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class TLSAdapter(HTTPAdapter):
    def __init__(self, ssl_version=None, **kwargs):
        self.ssl_version = ssl_version
        super(TLSAdapter, self).__init__(**kwargs)

    def init_poolmanager(self, *args, **kwargs):
        kwargs['ssl_version'] = self.ssl_version
        return super(TLSAdapter, self).init_poolmanager(*args, **kwargs)

class AppServiceStatusChecker:
    def __init__(self, url, service_name):
        self.url = url
        self.service_name = service_name
        self.logger = LoggerManager.get_logger(__name__, log_level=logging.DEBUG)

    # def check_web_service_status(self):
    #     try:
    #         session = requests.Session()
    #         adapter = TLSAdapter(ssl.PROTOCOL_TLSv1_2)
    #         session.mount('https://', adapter)
    #         response = session.get(self.url, verify=False)
    #         return response.status_code == 200
    #     except requests.exceptions.RequestException as e:
    #         self.logger.error(f"Error checking web service status for {self.url}: {e}")
    #         return False

    def check_web_service_status(self):
        try:
            session = requests.Session()
            adapter = TLSAdapter(ssl.PROTOCOL_TLSv1_2)

            # Adding retry mechanism
            retries = Retry(
                total=5,  # Total number of retries
                backoff_factor=0.5,  # Wait 0.5s, 1s, 2s, 4s, etc. between retries
                status_forcelist=[500, 502, 503, 504],  # Retry on specific HTTP status codes
                raise_on_status=False  # Don't raise an exception on status codes
            )
            adapter.max_retries = retries

            session.mount('https://', adapter)
            response = session.get(self.url, verify=False)
            return response.status_code == 200
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error checking web service status for {self.url}: {e}")
            return False
