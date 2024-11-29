# DATE         WHO            COMMENTS
# ---------- -------------- -------------------------------------------------
# 05/21/2024 Elvin Yalung   Author
# 06/15/2024 Elvin Yalung   v.1.2.1 Converted the URL column data into clickable hyperlink.
#
# 07/30/2024 Elvin Yalung   v.1.3.0 Configuration Management User Interface.
# 08/02/2024 Elvin Yalung   Implemented CRUD functionality for program configuration to minimize user errors and 
#                           ensure that each section remains complete and intact, with no missing details.

########################
# IMPORT MODULES
########################

import json
import logging
import configparser
import streamlit as st
import pandas as pd
from view_src.load_css import apply_css

program_version = "1.3.0"

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def read_config():
    """Read configuration file."""
    config = configparser.ConfigParser()
    try:
        config.read('../backend_script/config/config.ini')
        return config
    except (configparser.Error, FileNotFoundError) as e:
        logging.error(f"Error reading config file: {e}")
        st.error("Configuration file error. Please check the config file.")
        return None

# Load the JSON data
@st.cache_data(ttl=60)  # Set TTL to 1 minute
def fetch_data():
    """Fetch data from JSON file and process it."""
    try:
        with open('../backend_script/data/data.json') as f:
            data = json.load(f)
        for item in data:
            for key, value in item.items():
                if key not in ['url', 'hostname', 'path', 'query', 'username', 'fullname', 'mounted_on', 'service_name', 'filesystem'] and isinstance(value, str):
                    item[key] = value.title()
        return data
    except (json.JSONDecodeError, FileNotFoundError) as e:
        logging.error(f"Error loading data: {e}")
        st.error(f"Error loading data: {e}")
        return []

# Apply filter and search
def apply_filter_and_search(data, filter_type, search_term, site_filter):
    """Filter and search data based on filter type, search term, and site filter."""
    if not data:
        return []
    filtered_data = [
        item for item in data
        if (not filter_type or item.get("method") == filter_type)
        and (not site_filter or item.get("site") == site_filter)
        and (not search_term or any(search_term.lower() in str(value).lower() for value in item.values()))
    ]
    return filtered_data

# Get unique types for filtering
def get_unique_types(data):
    """Get unique filter types from data."""
    return sorted({item["method"] for item in data if "method" in item})

# Get unique sites for filtering
def get_unique_sites(data):
    """Get unique sites from data."""
    return sorted({item["site"] for item in data if "site" in item})

# Add icon to status
def add_icon(status):
    """Add icon to status based on its value."""
    icons = {
        'Online': '🟢 Online',
        'Query Error': '🟠 Query Error',
        'Offline': '🟠 Offline',
        'Service Not Found': '❌ Service Not Found',
        'Access Denied': '❌ Access Denied'
    }
    return icons.get(status.title(), status.title())

# Streamlit app layout
def main():
    """Main function for Streamlit app layout."""
    st.set_page_config(layout="wide")
    st.logo("view_src/logo.jpg")
    apply_css('view_src/style.css')

    config = read_config()
    if not config:
        return

    # pageTitle = config['Page']['pageTitle']

    st.title('MOS Insight')
    st.markdown(f"<p style='font-size: 12px; color: gray;'>V {program_version}</p>", unsafe_allow_html=True)

    # Fetch data
    data = fetch_data()

    # Sidebar for filters
    filter_type = st.sidebar.selectbox("Filter:", [""] + get_unique_types(data))
    site_filter = st.sidebar.selectbox("Site Option:", [""] + get_unique_sites(data))
    search_term = st.sidebar.text_input("Search:", "")
    
    # Filter and search
    filtered_data = apply_filter_and_search(data, filter_type, search_term, site_filter)
    
    # Display table with conditional formatting
    if filtered_data:
        df = pd.DataFrame(filtered_data)
        if 'result' in df.columns:
            df['result'] = df['result'].apply(lambda x: [x] if not isinstance(x, list) else x)

        # Capitalize every word in column names except 'url'
        df.columns = [col.title() for col in df.columns]

        # Apply the conditional formatting
        if 'Status' in df.columns:
            df['Status'] = df['Status'].apply(add_icon)
        
        # implementation of LinkColumn
        try:
            url_column = st.column_config.LinkColumn('url', display_text= 'Open Link')
            st.dataframe(df, column_config={'Url': url_column})
        except AttributeError:
            st.error("LinkColumn feature is not available. Please update Streamlit or use an alternative method.")

        # try:
        # # Convert the 'Name' column (which is a Series) to a list for display_text
        #     display_text_list = df['Name'].tolist()
            
        #     # Create a LinkColumn with Name as the display text for each URL
        #     url_column = st.column_config.LinkColumn('url', display_text=display_text_list)
            
        #     # Display dataframe with the custom LinkColumn
        #     st.dataframe(df, column_config={'Url': url_column})

        # except AttributeError:
        #     st.error("LinkColumn feature is not available. Please update Streamlit or use an alternative method.")

    else:
        st.write("No data found")

        

if __name__ == "__main__":
    main()
