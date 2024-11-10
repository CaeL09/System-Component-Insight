import streamlit as st
import time
from module.config_utils import write_config, remove_key_from_section

def modify_method_execution(config, config_file_path):
    if 'function' in config:
        st.subheader("Function Settings")
        updated_values = {}

        # Define comments or descriptions for each key
        key_descriptions = {
            'server_status': 'Verifying the availability of the remote server using a ping command.',
            'windows_service': 'Checking the operational status of a Windows service over the network.',
            'web_application': 'Assessing the reliability of a web application via an HTTP request.',
            'network_storage': 'Checking access and availability of a shared network folder.',
            'database': 'Verifying the accessibility and reliability of the database over the network.',
            'disk_usage': 'Retrieving server disk usage data remotely.',
            'service_account': 'Retrieving information and status of the service account.',
            'data_manager': 'Aggregating data from individual item results.',
            'email_alert': 'Sending an alert notification to the specified recipient via email.'
            # Add more descriptions as needed
        }

        for key in config['function']:
            # Display a subheader or comment above the toggle
            description = key_descriptions.get(key, "No description available.")
            col1, col2 = st.columns([3, 2])
            with col1:
                with st.expander(f"{key.replace('_', ' ').title()} Description"):
                    st.write(description)
            with col2:
                current_value = config['function'][key].lower() == "true"
                updated_values[key] = st.toggle(
                    f"{key.replace('_', ' ').title()}",
                    value=current_value
                )

        if st.button("Save Changes"):
            for key, value in updated_values.items():
                config['function'][key] = str(value)
            write_config(config_file_path, config, sections=['function'])
            st.success("Function settings updated successfully!")
            time.sleep(2)
            st.rerun()
    else:
        st.error("Function section not found in config file")
