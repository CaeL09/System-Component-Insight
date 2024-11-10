import logging
import configparser
import cx_Oracle
import pymysql
import pyodbc
import os
from module.logger_manager import LoggerManager

class DatabaseConnector:
    oracle_client_initialized = False

    def __init__(self, config_file='config/config.ini'):
        self.config = self.load_config(config_file)
        self.connections = {}
        self.logger = LoggerManager.get_logger(__name__, log_level=logging.DEBUG)
        self.setup_oracle_client()

    @staticmethod
    def load_config(config_file):
        config = configparser.ConfigParser()
        config.optionxform = str
        config.read(config_file)
        return config

    def connect(self, section_name, retries=3):
        db_config = self.config[section_name]
        db_type = db_config['database']
        for attempt in range(retries):
            try:
                self.logger.info(f"Attempting to connect to {db_config['name']}, attempt {attempt + 1}...")
                connection = self._create_connection(db_config, db_type)
                self.connections[db_config['name']] = connection
                self.logger.info(f"Connected to {db_config['name']}!")
                return 'online'
            except (cx_Oracle.DatabaseError, pymysql.MySQLError, pyodbc.Error) as db_err:
                self.logger.error(f"Database error while connecting to {db_config['name']}: {db_err}")
            except Exception as e:
                self.logger.error(f"Unexpected error while connecting to {db_config['name']}: {e}")
        self.logger.error(f"Failed to connect to {db_config['name']} after {retries} attempts.")
        return 'offline'

    def _create_connection(self, db_config, db_type):
        connection = None
        if db_type == 'oracle':
            connection = self._create_oracle_connection(db_config)
        elif db_type == 'mysql':
            connection = self._create_mysql_connection(db_config)
        elif db_type == 'sqlserver':
            connection = self._create_sqlserver_connection(db_config)
        else:
            raise ValueError(f"Unsupported database type: {db_type}")
        return connection

    def _create_oracle_connection(self, db_config):
        dsn = cx_Oracle.makedsn(
            db_config['server'],
            db_config.getint('port', 1521),
            sid=db_config.get('sid')
        )
        return cx_Oracle.connect(
            user=db_config['username'],
            password=db_config['password'],
            dsn=dsn
        )

    def _create_mysql_connection(self, db_config):
        return pymysql.connect(
            host=db_config['server'],
            port=db_config.getint('port', 3306),
            user=db_config['username'],
            password=db_config['password'],
            database=db_config['database_name']
        )

    def _create_sqlserver_connection(self, db_config):
        return pyodbc.connect(
            f"DRIVER={{{db_config['driver']}}};"
            f"SERVER={db_config['server']},{db_config.get('port', 1433)};"
            f"DATABASE={db_config['database_name']};"
            f"UID={db_config['username']};"
            f"PWD={db_config['password']}"
        )

    def execute_queries(self, section_name):
        db_config = self.config[section_name]
        db_name = db_config['name']
        if db_name not in self.connections:
            self.logger.error(f"Not connected to {db_name}!")
            return [], 'offline'

        results = []
        overall_status = 'online'
        for key in db_config:
            if key.startswith('query'):
                try:
                    query = db_config[key].strip('"')
                    self.logger.info(f"Executing query on {db_name}: {query}")

                    connection = self.connections[db_name]
                    with connection.cursor() as cursor:
                        cursor.execute(query)
                        result = cursor.fetchall()
                        self.logger.info(f"Query executed successfully on {db_name}.")
                        results.append((query, result, 'online'))
                except (cx_Oracle.DatabaseError, pymysql.MySQLError, pyodbc.Error) as db_err:
                    self.logger.error(f"Database error while executing query on {db_name}: {db_err}")
                    overall_status = 'query error'
                    results.append((query, [], 'query error'))
                except Exception as e:
                    self.logger.error(f"Unexpected error while executing query on {db_name}: {e}")
                    overall_status = 'query error'
                    results.append((query, [], 'query error'))
        return results, overall_status

    def close_all_connections(self):
        for db_name, connection in self.connections.items():
            if connection:
                try:
                    connection.close()
                    self.logger.info(f"Connection to {db_name} closed.")
                except Exception as e:
                    self.logger.error(f"Error closing connection to {db_name}: {e}")
        self.logger.info("All connections closed.")

    def setup_oracle_client(self):
        if not DatabaseConnector.oracle_client_initialized:
            for section in self.config.sections():
                if self.config[section].get('database') == 'oracle':
                    oracle_client_path = self.config[section].get('driver', fallback=None)
                    if oracle_client_path:
                        os.environ['PATH'] = f"{oracle_client_path};{os.environ['PATH']}"
                        try:
                            cx_Oracle.init_oracle_client(lib_dir=oracle_client_path)
                            DatabaseConnector.oracle_client_initialized = True
                        except cx_Oracle.DatabaseError as e:
                            self.logger.error(f"Error initializing Oracle client: {e}")
                        except Exception as e:
                            self.logger.error(f"Unexpected error initializing Oracle client: {e}")
