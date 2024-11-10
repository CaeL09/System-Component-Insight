# pages/main.py

import os
import logging
import streamlit as st
from module.auth import login
from module.item_management import add_new_section, modify_existing_section, remove_section 
from module.method_execution import modify_method_execution
from module.email_config import modify_email_config
from module.filter_config import modify_filter_config_section
from module.config_utils import read_config, create_sample_config
from view_src.load_css import apply_css

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

CONFIG_FILE_PATH = os.getenv("CONFIG_FILE_PATH", "../backend_script/config/config.ini")

def main():
    st.set_page_config(layout="centered")
    st.logo("view_src/logo.jpg")
    apply_css('view_src/style_config.css')
    
    if "logged_in" not in st.session_state or not st.session_state.logged_in:
        login()
    else:
        st.title("Configuration Management")
        config = read_config(CONFIG_FILE_PATH)
        sections = [section for section in config.sections() if section.startswith('item')]
        
        if not sections:
            create_sample_config(CONFIG_FILE_PATH)
            config = read_config(CONFIG_FILE_PATH)
            sections = [section for section in config.sections() if section.startswith('item')]
        
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Add New Item", "Update Item", "Remove Item", "Alert Section", "Method Execution", "Email"])
        
        with tab1:
            add_new_section(config, CONFIG_FILE_PATH)
        with tab2:
            modify_existing_section(config, CONFIG_FILE_PATH, sections)
        with tab3:
            remove_section(config, CONFIG_FILE_PATH, sections)
        with tab4:
            modify_filter_config_section(config, CONFIG_FILE_PATH)
        with tab5:
            modify_method_execution(config, CONFIG_FILE_PATH)
        with tab6:
            modify_email_config(config, CONFIG_FILE_PATH)

if __name__ == "__main__":
    main()
