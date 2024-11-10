import streamlit as st
import time

def login():
    st.markdown(
        """
        <style>
        .login-title {
            font-size: 2rem;
            margin-bottom: 1rem;
            color: #ffff !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False

    if st.session_state.logged_in:
        st.rerun()
    else:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        st.markdown('<div class="login-title">Login</div>', unsafe_allow_html=True)

        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            submit_button = st.form_submit_button("Login")

            if submit_button:
                if username == 'admin' and password == 'MOSTech':
                    st.session_state.logged_in = True
                    st.success("Login successful!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Invalid username or password")

        st.markdown('</div>', unsafe_allow_html=True)
