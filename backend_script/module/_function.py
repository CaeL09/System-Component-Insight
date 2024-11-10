import configparser
# import concurrent.futures
from module.utils import com_initialized, create_item_data, save_results_to_json, disk_process_section
from module.server_status import ServerPinger
from module.windows_service import WindowsServiceStatusChecker
from module.web_application import AppServiceStatusChecker
from module.network_storage import NetworkStorageAccessChecker
from module.database import DatabaseConnector
from module.email_status_notify import StatusNotifier
from module.email_config_manager import EmailConfigManager
from module.config_manager import ConfigManager
from module.service_account import ServiceAccountChecker

config_ini_path = 'config/config.ini'

@com_initialized
def ping_servers(logger, manager: ConfigManager):
    mymethod = 'server status'
    due_items = manager.get_due_items(method=mymethod)
    logger.info(f"Due items for server status: {due_items}")

    due_servers = {item: manager.last_run[item] for item in due_items if item in manager.last_run}
    section_data = {item: [] for item in due_items if item in manager.last_run}

    server_pinger = ServerPinger(due_servers.values())
    ping_results = server_pinger.ping_servers()

    if not isinstance(ping_results, list):
        logger.error(f"Expected list from ping_servers, got {type(ping_results)}")
        return

    for result in ping_results:
        matched_section = None
        for section_name, item in due_servers.items():
            hostnames = item.get('hostname', '').split(',')
            if (item.get('name', '').lower() == result.get('name', '').lower() and 
                item.get('site', '').lower() == result.get('site', '').lower() and 
                result.get('hostname', '').lower() in [hostname.strip().lower() for hostname in hostnames] and
                item.get('method', '').lower() == mymethod):
                matched_section = section_name
                break
        
        if matched_section:
            add_ping_result_to_data(result, section_data[matched_section])
            # update_last_run_time(result, manager, logger, method=mymethod)
            manager.update_last_run_time(section_name)
        else:
            logger.warning(f"No matching section found for result: {result}")
    
    # Save results to JSON files
    for section_name, data in section_data.items():
        # logger.info(f"Saving data for section [{section_name}]: {data}")
        save_results_to_json(section_name, data, logger)

def add_ping_result_to_data(result: dict, data: list):
    sanitized_status = 'online' if result.get("response_time") is not None else 'offline'
    response_time = "{:.2f} ms".format(result["response_time"]) if result.get("response_time") is not None else "failed"
    
    item_data = create_item_data(result, {
        'response_time': response_time,
        'status': sanitized_status
    })
    data.append(item_data)



@com_initialized
def check_web_application(logger, manager: ConfigManager):
    due_items = manager.get_due_items(method='web application')
    logger.info(f"Due items for web application: {due_items}")

    for item in due_items:
        item_config = manager.last_run.get(item)
        if not item_config:
            logger.warning(f"Configuration for item '{item}' not found in last_run. Skipping.")
            continue

        service_name = item_config.get('name')
        urls = item_config.get('url', '').split(',')
        data = []

        for url in urls:
            url = url.strip()
            if not url:
                logger.warning(f"Empty URL found for service '{service_name}'. Skipping.")
                continue

            app_checker = AppServiceStatusChecker(url, service_name)
            is_service_up = app_checker.check_web_service_status()

            status = 'online' if is_service_up else 'offline'
            logger.info(f"Processing web application: '{service_name}' ({url}): {status}")

            item_data = create_item_data(item_config, {
                'url': url,
                'status': status
            })
            data.append(item_data)

        # Save data to persistent storage (JSON file for each section)
        save_results_to_json(item, data, logger)
        manager.update_last_run_time(item)




def update_last_run_for_service(manager, hostname, service_name, logger):
    for section_name, item in manager.last_run.items():
        if (item.get('hostname', '').lower() == hostname.lower() and 
            service_name.lower() in [s.lower() for s in item.get('service_name', '').split(',')] and
            item.get('method', '').lower() == 'windows service'):
            manager.update_last_run_time(section_name)
            return
    logger.warning(f"Section for hostname '{hostname.lower()}', service '{service_name}', "
                   "not found in last_run. Unable to update last_run time.")

@com_initialized
def check_windows_service(logger, manager):
    due_items = manager.get_due_items(method='windows service')
    logger.info(f"Due items for windows service: {due_items}")
    due_services = [manager.last_run[item] for item in due_items if item in manager.last_run]

    try:
        for server_config in WindowsServiceStatusChecker.read_servers_configuration():
            hostname, username, password, service_names = server_config
            logger.debug(f"Checking configuration for hostname: {hostname}")

            if hostname.lower() not in [service['hostname'].lower() for service in due_services]:
                logger.debug(f"Skipping hostname {hostname} as it is not in due items.")
                continue

            service_checker = WindowsServiceStatusChecker(hostname, username, password, service_names)
            service_statuses = service_checker.check_service_status()

            data = []
            matching_service = next((service for service in due_services 
                                     if service['hostname'].lower() == hostname.lower()), None)

            if not matching_service:
                logger.warning(f"No matching service found for hostname {hostname}. Skipping.")
                continue

            if service_statuses == "access denied":
                for service_name in service_names:
                    item_data = create_item_data(matching_service, {
                        'service_name': service_name,
                        'status': 'access denied'
                    })
                    data.append(item_data)
                logger.error(f"Access denied for hostname: {hostname}")
            elif isinstance(service_statuses, dict):
                for service_name, state in service_statuses.items():
                    if state == "service not found":
                        item_data = create_item_data(matching_service, {
                            'service_name': service_name,
                            'status': 'service not found'
                        })
                    else:
                        sanitized_status = 'online' if state.lower() == 'running' else 'offline'
                        item_data = create_item_data(matching_service, {
                            'service_name': service_name,
                            'status': sanitized_status
                        })
                        update_last_run_for_service(manager, hostname, service_name, logger)
                    data.append(item_data)
            else:
                logger.error(f"Expected dictionary from check_service_status, got {type(service_statuses)}")
                continue

            # Ensure the correct section_name is found
            correct_section = None
            for section_name, item in manager.last_run.items():
                if (item.get('hostname', '').lower() == hostname.lower() and
                    any(service_name.lower() == s.lower() for s in item.get('service_name', '').split(',')) and
                    item.get('method', '').lower() == 'windows service'):
                    correct_section = section_name
                    break

            if correct_section:
                save_results_to_json(correct_section, data, logger)
            else:
                logger.warning(f"No matching section found for hostname: {hostname} and service: {service_names}")

    except Exception as e:
        logger.exception("Error in check_windows_service: %s", e)





@com_initialized
def check_network_storage(logger, manager: ConfigManager):
    due_items = manager.get_due_items(method='network storage')
    logger.info(f"Due items for network storage: {due_items}")

    network_storage_check = NetworkStorageAccessChecker()
    access_results = network_storage_check.check_access()

    for item in due_items:
        if item in access_results:
            result = network_storage_check.config[item]
            path_results = access_results[item]

            data = []
            for path, access_granted in path_results.items():
                sanitized_status = 'online' if access_granted else 'offline'
                
                item_data = create_item_data(result, {
                    'path': path,
                    'status': sanitized_status
                })
                logger.info(f"Network Storage '{item}' path '{path}' access is: {sanitized_status}")
                data.append(item_data)

                # Save data to persistent storage (JSON file for each section)
                save_results_to_json(item, data, logger)
                manager.update_last_run_time(item)




@com_initialized
def check_database_connections(logger, manager: ConfigManager):
    due_items = manager.get_due_items(method='database')
    logger.info(f"Due items for database: {due_items}")
    db_connector = DatabaseConnector(config_file=config_ini_path)

    for item in due_items:
        section_name = item
        db_config = db_connector.config[section_name]

        status = db_connector.connect(section_name)
        query_results = []
        if status == 'online':
            query_results, status = db_connector.execute_queries(section_name)
        else:
            for key in db_config:
                if key.startswith('query'):
                    query = db_config[key].strip('"')
                    query_results.append((query, [], 'offline'))

        db_append_item_data(section_name, db_config, query_results, status, logger)
        manager.update_last_run_time(item)

    db_connector.close_all_connections()

def db_append_item_data(section_name, db_config, query_results, status, logger):
    data = []

    for query, result, query_status in query_results:
        if query_status == 'online':
            for row in result:
                row_data = [str(item) for item in row]
                item_data = create_item_data(db_config, {
                    'query': query,
                    'result': row_data,
                    'status': query_status
                })
                data.append(item_data)
        else:
            item_data = create_item_data(db_config, {
                'query': query,
                'result': '',
                'status': query_status
            })
            data.append(item_data)

    save_results_to_json(section_name, data, logger)



@com_initialized
def check_disk_usage(logger, manager):
    due_items = manager.get_due_items(method='disk usage')
    logger.info(f"Due items for disk usage: {due_items}")

    config = configparser.ConfigParser()
    config.read(config_ini_path)

    results_dict = {}

    for section in config.sections():
        if section.startswith('item') and section in due_items:
            disk_process_section(logger, config, section, results_dict, manager)

    # Save all results for each section to JSON after processing
    for section, results in results_dict.items():
        save_results_to_json(section, results, logger)



@com_initialized
def check_service_account(logger, manager: ConfigManager):
    due_items = manager.get_due_items(method='service account')
    logger.info(f"Due items for service account: {due_items}")
    config_file = config_ini_path

    account_checker = ServiceAccountChecker(config_file)
    results = account_checker.check_service_accounts(due_items)

    for section, section_results in results.items():
        section_data = []
        for result in section_results:
            item_data = create_item_data(account_checker.config[section], result)
            section_data.append(item_data)
        manager.update_last_run_time(section)
        save_results_to_json(section, section_data, logger)

# @com_initialized
def emailStatus_notifier(logger):
    """Function to initialize and run email notifications based on status data."""
    try:
        # Initialize ConfigManager and read configurations
        config_manager = EmailConfigManager('config/config.ini')
        email_config = config_manager.get_email_config()
        filter_config = config_manager.get_filter_config()
        # Initialize StatusNotifier with JSON file and configurations
        notifier = StatusNotifier('data/data.json', email_config, filter_config)
        # Read JSON data
        notifier.read_json()
        # Filter data based on configuration
        notifier.filter_data()
        # Send email with filtered data
        notifier.send_email()
    except Exception as e:
        logger.error(f"An error occurred: {e}")





