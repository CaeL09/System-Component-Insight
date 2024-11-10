import streamlit as st
import time
from module.config_utils import write_config

def modify_email_config(config, config_file_path):
    if 'EmailConfig' in config:
        st.subheader("EmailConfig Settings")
        updated_values = {}

        # Define the order of the keys
        keys_order = ['from_email', 'cc_email', 'subject', 'smtp_server', 'smtp_port']

        for key in keys_order:
            if key in config['EmailConfig']:
                # Handling different input types for each key
                if key in ['from_email', 'cc_email', 'subject']:
                    updated_values[key] = st.text_input(f"{key.replace('_', ' ').title()}", config['EmailConfig'][key])
                elif key == 'smtp_server':
                    col1, col2 = st.columns(2)
                    with col1:
                        updated_values[key] = st.text_input(f"{key.replace('_', ' ').title()}", config['EmailConfig'][key])
                elif key == 'smtp_port':
                    with col2:
                        updated_values[key] = st.number_input(f"{key.replace('_', ' ').title()}", value=int(config['EmailConfig'][key]), step=1)

        if st.button("Save Changes "):
            for key, value in updated_values.items():
                config['EmailConfig'][key] = str(value)
            write_config(config_file_path, config, sections=['EmailConfig'])
            st.success("EmailConfig settings updated successfully!")
            time.sleep(2)
            st.rerun()
    else:
        st.error("EmailConfig section not found in config file")
