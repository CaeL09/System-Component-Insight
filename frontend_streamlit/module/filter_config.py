import streamlit as st
import time
from module.config_utils import write_config, remove_key_from_section

# def modify_filter_config_section(config, config_file_path):
#     if 'FilterConfig' in config:
#         st.subheader("Alert Settings")
#         # existing_keys = list(config['FilterConfig'].keys())
#         existing_keys = [key for key in config['FilterConfig'].keys() if key != "href_streamlit"]
#         selected_key = st.selectbox("Select Label to Modify or Remove", [""] + existing_keys)
        
#         if selected_key:
#             new_value = st.text_input("Failed Value(s)", config['FilterConfig'][selected_key])
#             if st.button("Update"):
#                 new_value = new_value.replace('%', '%%')
#                 config['FilterConfig'][selected_key] = new_value
#                 write_config(config_file_path, config, sections=['FilterConfig'])
#                 st.success(f"Label '{selected_key}' updated successfully!")
#                 time.sleep(2)
#                 st.rerun()
            
#             if st.button("Remove"):
#                 remove_key_from_section(config_file_path, 'FilterConfig', selected_key)
#                 st.success(f"Label '{selected_key}' removed successfully!")
#                 time.sleep(2)
#                 st.rerun()
        
#         st.subheader("Add New Failed Value Pair")
#         new_key = st.text_input("Add Failed Label")
#         new_value = st.text_input("Failed Value(s)")
#         st.text("Use commas to separate multiple values. You may use the following operators:")
#         st.text(">, <, like")
#         if st.button("Add New Value Pair"):
#             new_value = new_value.replace('%', '%%')
#             if new_key and new_value:
#                 config['FilterConfig'][new_key] = new_value
#                 write_config(config_file_path, config, sections=['FilterConfig'])
#                 st.success(f"Label '{new_key}' added successfully!")
#                 time.sleep(2)
#                 st.rerun()
#             else:
#                 st.error("Both Label and value are required to add a new entry.")
#     else:
#         st.error("FilterConfig section not found in config file")

def extract_operator_and_value(value):
    """Helper function to extract operator and value from a string."""
    operators = ["<", ">", "like"]
    value = value.strip()
    for operator in operators:
        if value.startswith(operator):
            return operator, value[len(operator):].strip()
    return "", value  # Default case: no operator

def modify_filter_config_section(config, config_file_path):
    if 'FilterConfig' in config:
        st.subheader("Alert Settings")

        # Select Label to Modify or Remove
        existing_keys = [key for key in config['FilterConfig'].keys() if key != "href_streamlit"]
        selected_key = st.selectbox("Select Label to Modify or Remove", [""] + existing_keys, key="modify_selectbox")
        
        if selected_key:
            current_value = config['FilterConfig'][selected_key]
            current_operator, current_value = extract_operator_and_value(current_value)

            st.subheader("Update or Remove Label")
            col1, col2 = st.columns([2, 3])
            with col1:
                operator_options = ["", "<", ">", "like"]
                operator_index = operator_options.index(current_operator) if current_operator in operator_options else 0
                operator = st.selectbox("Choose Operator (Optional)", operator_options, index=operator_index, key="update_operator")
            with col2:
                new_value = st.text_input("Alert Value(s)", current_value, key="update_value")

            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("Update", key="update_button"):
                    final_value = (operator + " " + new_value).strip() if operator else new_value.strip()
                    final_value = final_value.replace('%', '%%')
                    config['FilterConfig'][selected_key] = final_value
                    write_config(config_file_path, config, sections=['FilterConfig'])
                    st.success(f"Label '{selected_key}' updated successfully!")
                    time.sleep(2)
                    st.rerun()
            with col2:
                if st.button("Remove", key="remove_button"):
                    remove_key_from_section(config_file_path, 'FilterConfig', selected_key)
                    st.success(f"Label '{selected_key}' removed successfully!")
                    time.sleep(2)
                    st.rerun()

        # Add New Alert Value Pair: Using columns for a better layout
        st.subheader("New Alert Value Pair")
        new_key = st.text_input("Alert Label", key="add_label")

        col1, col2 = st.columns([2, 3])
        with col1:
            operator = st.selectbox("Choose Operator (Optional)", ["", "<", ">", "like"], index=0, key="add_operator")
        with col2:
            new_value = st.text_input("Alert Value(s)", key="add_value")
            st.text("Use commas to separate multiple values.")

        if st.button("Save New Alert", key="add_button"):
            final_value = (operator + " " + new_value).strip() if operator else new_value.strip()
            final_value = final_value.replace('%', '%%')
            if new_key and final_value:
                config['FilterConfig'][new_key] = final_value
                write_config(config_file_path, config, sections=['FilterConfig'])
                st.success(f"Label '{new_key}' added successfully!")
                time.sleep(2)
                st.rerun()
            else:
                st.error("Both Label and value are required to add a new entry.")
    else:
        st.error("FilterConfig section not found in config file")
