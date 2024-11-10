import logging
import streamlit as st

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def apply_css(file_path):
    """Apply CSS for Streamlit styling."""
    try:
        with open(file_path, 'r') as f:
            css_content = f.read()
            st.markdown(f'<style>{css_content}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        logging.error("CSS file not found. Please check the file path.")
        st.error("CSS file not found. Please check the file path.")