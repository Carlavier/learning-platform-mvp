import streamlit as st
from database.connection import get_db_connection

if 'user' not in st.session_state or st.session_state.user is None:
    st.error("Please login to access this page")
    st.stop()

st.set_page_config(page_title="Profile", page_icon="👤", layout="wide")


def main():
    st.title("👤 My Profile")

    user = st.session_state.user
    st.subheader("Account Information")
    col1, col2 = st.columns(2)
    with col1:
        st.text_input("Username", value=user['username'], disabled=True)
        st.text_input("Email", value=user['email'], disabled=True)
    with col2:
        full_name = st.text_input("Full Name", value=user.get('full_name') or "")
        role = st.text_input("Role", value=user.get('role') or 'user', disabled=True)

    if st.button("Save Profile", type="primary"):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET full_name = ? WHERE id = ?", (full_name, user['id']))
            conn.commit()
        st.session_state.user['full_name'] = full_name
        st.success("Profile updated")

    st.subheader("Security")
    with st.form("change_password"):
        pw1 = st.text_input("New Password", type="password")
        pw2 = st.text_input("Confirm Password", type="password")
        submit = st.form_submit_button("Change Password")
        if submit:
            if not pw1 or len(pw1) < 6:
                st.error("Password must be at least 6 characters")
            elif pw1 != pw2:
                st.error("Passwords do not match")
            else:
                st.info("Password change flow not implemented in MVP")


if __name__ == "__main__":
    main()
