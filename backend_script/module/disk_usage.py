import logging
import wmi
import paramiko
from module.logger_manager import LoggerManager


class DiskUsage:
    def __init__(self, hostname, username, password, connection_timeout=15):
        self.logger = LoggerManager.get_logger(__name__, log_level=logging.DEBUG)
        self.hostname = hostname
        self.username = username
        self.password = password
        self.os_type = None
        self.connection = None
        self.connection_timeout = connection_timeout
        self.detect_os()

    def detect_os(self):
        try:
            self.logger.info(f"Detecting OS type for {self.hostname}")
            if self.is_windows():
                self.os_type = 'Windows'
                self.logger.info(f"{self.hostname} is a Windows server.")
            elif self.is_linux():
                self.os_type = 'Linux'
                self.logger.info(f"{self.hostname} is a Linux server.")
            else:
                self.os_type = 'Unknown'
                self.logger.warning(f"Could not determine the OS type for {self.hostname}.")
        except Exception as e:
            self.logger.error(f"Error detecting OS for {self.hostname}: {e}")

    def is_windows(self):
        try:
            self.logger.debug(f"Attempting WMI connection to {self.hostname}")
            conn = wmi.WMI(
                computer=self.hostname,
                user=self.username,
                password=self.password,
                namespace='root\\cimv2'
            )
            # Check if connection is established by querying the OS
            os_name = conn.Win32_OperatingSystem()[0].Caption
            self.connection = conn
            self.logger.debug(f"Detected Windows OS: {os_name} on {self.hostname}")
            return True
        except wmi.x_wmi as e:
            self.logger.error(f"WMI query failed for {self.hostname}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error during Windows detection for {self.hostname}: {e}")
            return False

    def is_linux(self):
        try:
            self.logger.debug(f"Attempting SSH connection to {self.hostname}")
            with paramiko.SSHClient() as ssh:
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(self.hostname, username=self.username, password=self.password, timeout=self.connection_timeout)
                stdin, stdout, stderr = ssh.exec_command('uname -s')
                output = stdout.read().decode('utf-8').strip()
                self.logger.debug(f"SSH command output for {self.hostname}: {output}")
                return output == 'Linux'
        except Exception as e:
            self.logger.debug(f"Linux detection failed for {self.hostname}: {e}")
            return False

    def get_disk_usage(self):
        if self.os_type == 'Windows':
            return self.get_windows_disk_usage()
        elif self.os_type == 'Linux':
            return self.get_linux_disk_usage()
        else:
            self.logger.error(f"Unsupported OS type {self.os_type} for {self.hostname}.")
            return None

    def get_windows_disk_usage(self):
        try:
            partitions = self.connection.Win32_LogicalDisk(DriveType=3)
            disk_usage_info = {}
            for partition in partitions:
                disk_usage_info[partition.DeviceID] = {
                    'Total': self._bytes_to_gb(partition.Size),
                    'Used': self._bytes_to_gb(int(partition.Size) - int(partition.FreeSpace)),
                    'Free': self._bytes_to_gb(partition.FreeSpace),
                    'Percent': f"{round(100 - (int(partition.FreeSpace) / int(partition.Size) * 100), 2)}%"
                }
            return disk_usage_info
        except Exception as e:
            self.logger.error(f"Error retrieving disk usage for Windows server {self.hostname}: {e}")
            return None
    
    def _bytes_to_gb(self, bytes):
        try:
            return f"{round(int(bytes) / (1024 ** 3), 2)}G"
        except (ValueError, TypeError) as e:
            self.logger.error(f"Error converting bytes to GB: {e}")
            return None

    def get_linux_disk_usage(self):
        try:
            self.logger.info(f"Retrieving disk usage for Linux server {self.hostname}")
            with paramiko.SSHClient() as ssh:
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(self.hostname, username=self.username, password=self.password, timeout=self.connection_timeout)
                stdin, stdout, stderr = ssh.exec_command('df -h')
                error_output = stderr.read().decode('utf-8').strip()
                if error_output:
                    self.logger.error(f"Error executing `df -h` command on {self.hostname}: {error_output}")
                df_output = stdout.read().decode('utf-8')
                self.logger.debug(f"Raw `df -h` output for {self.hostname}:\n{df_output}")
                return self._parse_df_output(df_output)
        except Exception as e:
            self.logger.error(f"Error retrieving disk usage for Linux server {self.hostname}: {e}")
            return None

    def _parse_df_output(self, df_output):
        lines = df_output.strip().split('\n')
        disk_usage_info = {}
        i = 1  # Skip the header line

        while i < len(lines):
            line = lines[i].strip()
            if line:
                parts = line.split()
                if len(parts) >= 6:
                    disk_usage_info.update(self._parse_df_line(parts))
                elif len(parts) < 6 and i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    combined_line = line + " " + next_line
                    combined_parts = combined_line.split()
                    if len(combined_parts) >= 6:
                        disk_usage_info.update(self._parse_df_line(combined_parts))
                    else:
                        self.logger.warning(f"Unexpected line format in `df -h` output: {line} {next_line}")
                    i += 1
                else:
                    self.logger.warning(f"Unexpected line format in `df -h` output: {line}")
            else:
                self.logger.warning(f"Empty line in `df -h` output: {line}")
            i += 1

        return disk_usage_info

    def _parse_df_line(self, parts):
        if len(parts) >= 6:
            filesystem = parts[0]
            size = parts[1]
            used = parts[2]
            available = parts[3]
            percent = parts[4]
            mountpoint = " ".join(parts[5:])
            return {
                filesystem: {
                    'Total': size,
                    'Used': used,
                    'Free': available,
                    'Percent': percent,
                    'Mounted on': mountpoint
                }
            }
        return {}
