import time
import streamlit as st
from module.config_utils import write_config, is_hidden, create_input_widget, METHOD_CHOICES

def add_new_section(config, config_file_path):
    last_item_number = max([int(section.replace('item', '')) for section in config.sections() if section.startswith("item")], default=0)
    new_section = f"item{last_item_number + 1}"
    
    st.subheader(f"Add: {new_section}")
    new_values = {}
    
    method = st.selectbox("Select Method", [""] + METHOD_CHOICES, index=0, key="method_add")
    new_values['method'] = method
    
    if method:
        col1, col2 = st.columns(2)
        database = ''
        unique_id = new_section
        
        for key in config['item1']:
            if key == 'method':
                continue
            with col1 if key in ['name', 'site', 'database', 'hostname', 'service_name', 'url', 'path', 'database_name', 'driver', 'recipient', 'sid', 'port'] else col2:
                widget_value = create_input_widget(key, '', key.title(), is_hidden(key, method, database), st, unique_id)
                if key == 'interval':
                    if isinstance(widget_value, tuple) and len(widget_value) == 2:
                        new_values['interval_number'], new_values['interval_unit'] = widget_value
                        new_values[key] = new_values['interval_number'] + new_values['interval_unit']
                    else:
                        new_values['interval_number'], new_values['interval_unit'] = '', ''
                else:
                    new_values[key] = widget_value
                if key == 'database':
                    database = new_values[key]
        
        if st.button("Save New Item", key="save_add"):
            required_fields = ['name', 'site', 'interval_number', 'interval_unit', 
                            'hostname', 'username', 'password', 'service_name', 
                            'url', 'path', 'database_name', 'driver', 'server', 
                            'port', 'sid', 'query']
            
            if new_values.get('email_notify') == 'True':
                required_fields.append('recipient')
            
            errors = [field for field in required_fields if not new_values.get(field) and not is_hidden(field, method, database)]
            
            if errors:
                st.error(f"The following fields are required and cannot be empty: {', '.join(errors)}")
            else:
                if new_section not in config:
                    new_values_str = {k: str(v) for k, v in new_values.items() if k != 'interval_number' and k != 'interval_unit'}
                    config[new_section] = new_values_str
                    write_config(config_file_path, config)
                    st.success(f"Section '{new_section}' added successfully!")
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error("Item name already exists.")

def modify_existing_section(config, config_file_path, sections):
    st.subheader("Update an Existing Item")
    update_sections = [section for section in sections if section != "item1"]
    section_to_modify = st.selectbox("Select Item", [""] + update_sections, key="section_modify")
    if section_to_modify and section_to_modify != "Select an item":
        st.subheader(f"Update: {section_to_modify}")
        updated_values = {}
        
        method = st.selectbox("Method", METHOD_CHOICES, index=METHOD_CHOICES.index(config[section_to_modify]['method']), key=f"method_{section_to_modify}")
        updated_values['method'] = method
        
        col1, col2 = st.columns(2)
        database = config[section_to_modify].get('database', '')
        
        unique_id = section_to_modify
        
        for key, value in config[section_to_modify].items():
            if key == 'method':
                continue
            with col1 if key in ['name', 'site', 'database', 'hostname', 'service_name', 'url', 'path', 'database_name', 'driver', 'recipient', 'sid', 'port'] else col2:
                # disabled = key == 'interval'
                # widget_value = create_input_widget(key, value, key.title(), is_hidden(key, method, database), st, unique_id, disabled=disabled)
                widget_value = create_input_widget(key, value, key.title(), is_hidden(key, method, database), st, unique_id)
                if key == 'interval':
                    if isinstance(widget_value, tuple) and len(widget_value) == 2:
                        updated_values['interval_number'], updated_values['interval_unit'] = widget_value
                        updated_values[key] = updated_values['interval_number'] + updated_values['interval_unit']
                    else:
                        updated_values['interval_number'], updated_values['interval_unit'] = '', ''
                else:
                    updated_values[key] = widget_value
                if key == 'database':
                    database = updated_values[key]
        
        if st.button("Save Updated Item", key="save_modify"):
            required_fields = ['name', 'site', 'interval_number', 'interval_unit', 
                               'hostname', 'username', 'password', 'service_name', 
                               'url', 'path', 'database_name', 'driver', 'server', 
                               'port', 'sid', 'query']
            
            if updated_values.get('email_notify') == 'True':
                required_fields.append('recipient')
            
            errors = [field for field in required_fields if not updated_values.get(field) and not is_hidden(field, method, database)]
            
            if errors:
                st.error(f"The following fields are required and cannot be empty: {', '.join(errors)}")
            else:
                updated_values_str = {k: str(v) for k, v in updated_values.items() if k != 'interval_number' and k != 'interval_unit'}
                for key, value in updated_values_str.items():
                    config[section_to_modify][key] = value
                write_config(config_file_path, config)
                st.success(f"Section '{section_to_modify}' updated successfully!")
                time.sleep(2)
                st.rerun()

def remove_section(config, config_file_path, sections):
    st.subheader("Remove Item")
    removable_sections = [section for section in sections if section != "item1"]
    sections_to_remove = st.multiselect("Select Item(s)", removable_sections, key="section_remove")
    if sections_to_remove:
        if st.button("Remove Selected Items", key="remove_section"):
            for section in sections_to_remove:
                config.remove_section(section)
                write_config(config_file_path, config, sections=[section])
            st.success(f"{', '.join(sections_to_remove)} removed successfully!")
            time.sleep(2)
            st.rerun()
