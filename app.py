import streamlit as st
import os
from dotenv import load_dotenv
from datetime import datetime
import time
from database.connection import init_database, get_db_connection
from auth.authentication import AuthService

# Load environment variables
load_dotenv()
# skibidi
print("hello")
# Page configuration
st.set_page_config(
    page_title="Learning Platform",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database
init_database()

# Initialize services
auth_service = AuthService()

# Session state initialization
if 'user' not in st.session_state:
    st.session_state.user = None
if 'show_login' not in st.session_state:
    st.session_state.show_login = True


def handle_logout():
    st.session_state.user = None
    st.session_state.show_login = True
    st.rerun()


def show_header():
    """Display header with user info"""
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        st.title("📚 Learning Platform")

    with col3:
        if st.session_state.user:
            st.write(f"👤 {st.session_state.user['username']}")
            if st.button("Logout", key="logout_btn"):
                handle_logout()


def show_login_page():
    """Display login/register page"""
    st.markdown(
        """
        <style>
        .main-header {
            text-align: center;
            padding: 2rem 0;
        }
        .auth-container {
            max-width: 400px;
            margin: 0 auto;
            padding: 2rem;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Check for email verification token in URL
    query_params = st.query_params
    if 'verify' in query_params:
        token = query_params['verify']
        if auth_service.verify_email(token):
            st.success("✅ Email verified successfully! You can now login.")
            st.query_params.clear()
        else:
            st.error("❌ Invalid or expired verification token.")

    # Check for password reset token
    if 'reset' in query_params:
        show_password_reset(query_params['reset'])
        return

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown('<h1 class="main-header">📚 Welcome to Learning Platform</h1>', unsafe_allow_html=True)
        st.markdown('<p style="text-align: center;">Your AI-powered learning companion</p>', unsafe_allow_html=True)

        tab1, tab2, tab3 = st.tabs(["Login", "Register", "Forgot Password"])

        with tab1:
            show_login_form()

        with tab2:
            show_register_form()

        with tab3:
            show_forgot_password_form()


def show_login_form():
    """Display login form"""
    with st.form("login_form"):
        username = st.text_input("Username or Email", placeholder="Enter username or email")
        password = st.text_input("Password", type="password", placeholder="Enter password")
        remember_me = st.checkbox("Remember me")

        col1, col2 = st.columns(2)
        with col1:
            submit = st.form_submit_button("Login", use_container_width=True, type="primary")

        if submit:
            if username and password:
                success, user_data, message = auth_service.login_user(username, password)
                if success:
                    st.session_state.user = user_data
                    st.session_state.show_login = False
                    st.success(message)
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(message)
            else:
                st.error("Please fill in all fields")


def show_register_form():
    """Display registration form"""
    with st.form("register_form"):
        col1, col2 = st.columns(2)

        with col1:
            full_name = st.text_input("Full Name", placeholder="John Doe")
            email = st.text_input("Email", placeholder="john@example.com")

        with col2:
            username = st.text_input("Username", placeholder="johndoe")
            password = st.text_input("Password", type="password", placeholder="Min 6 characters")

        confirm_password = st.text_input("Confirm Password", type="password", placeholder="Re-enter password")
        terms = st.checkbox("I agree to the Terms and Conditions")

        submit = st.form_submit_button("Register", use_container_width=True, type="primary")

        if submit:
            # Validation
            if not all([email, username, password, confirm_password]):
                st.error("Please fill in all required fields")
            elif len(password) < 6:
                st.error("Password must be at least 6 characters")
            elif password != confirm_password:
                st.error("Passwords do not match")
            elif not terms:
                st.error("Please accept the terms and conditions")
            else:
                success, message = auth_service.register_user(email, username, password, full_name)
                if success:
                    st.success(message)
                    st.info("📧 Please check your email to verify your account")
                else:
                    st.error(message)


def show_forgot_password_form():
    """Display forgot password form"""
    with st.form("forgot_password_form"):
        email = st.text_input("Email", placeholder="Enter your registered email")
        submit = st.form_submit_button("Send Reset Link", use_container_width=True, type="primary")

        if submit:
            if email:
                success, message = auth_service.request_password_reset(email)
                if success:
                    st.success(message)
                else:
                    st.error(message)
            else:
                st.error("Please enter your email")


def show_password_reset(token):
    """Show password reset form"""
    st.title("Reset Password")

    with st.form("reset_password_form"):
        new_password = st.text_input("New Password", type="password", placeholder="Min 6 characters")
        confirm_password = st.text_input("Confirm Password", type="password", placeholder="Re-enter password")

        submit = st.form_submit_button("Reset Password", use_container_width=True, type="primary")

        if submit:
            if new_password and confirm_password:
                if len(new_password) < 6:
                    st.error("Password must be at least 6 characters")
                elif new_password != confirm_password:
                    st.error("Passwords do not match")
                else:
                    # Implement password reset logic (MVP placeholder)
                    st.success("Password reset successfully! Please login with your new password.")
                    st.query_params.clear()
                    time.sleep(2)
                    st.rerun()
            else:
                st.error("Please fill in all fields")


def show_dashboard():
    """Display main dashboard"""
    show_header()

    # Sidebar navigation
    with st.sidebar:
        st.markdown("### 📚 Navigation")

        if st.session_state.user['role'] == 'admin':
            st.info("👑 Admin Mode")

        # Quick stats
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Get user's learning stats
            cursor.execute(
                '''
                SELECT COUNT(DISTINCT lesson_id) as lessons_accessed,
                       AVG(progress_percentage) as avg_progress
                FROM learning_progress
                WHERE user_id = ?
                ''',
                (st.session_state.user['id'],),
            )

            stats = cursor.fetchone()

            st.markdown("### 📊 Your Stats")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Lessons", stats['lessons_accessed'] or 0)
            with col2:
                st.metric("Progress", f"{(stats['avg_progress'] or 0):.0f}%")

    # Main content area
    st.markdown(
        "## 🎯 Welcome back, {}!".format(
            st.session_state.user['full_name'] or st.session_state.user['username']
        )
    )

    # Quick actions
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("📚 Browse Lessons", use_container_width=True):
            st.switch_page("pages/1_📚_Lessons.py")

    with col2:
        if st.button("💬 AI Chat", use_container_width=True):
            st.switch_page("pages/2_💬_AI_Chat.py")

    with col3:
        if st.button("👤 My Profile", use_container_width=True):
            st.switch_page("pages/3_👤_Profile.py")

    with col4:
        if st.session_state.user['role'] == 'admin':
            if st.button("🔧 Admin Panel", use_container_width=True):
                st.switch_page("pages/4_🔧_Admin.py")

    # Recent lessons
    st.markdown("### 📖 Recent Lessons")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT l.*, lp.progress_percentage, lp.last_accessed
            FROM lessons l
            LEFT JOIN learning_progress lp ON l.id = lp.lesson_id AND lp.user_id = ?
            WHERE l.status = 'published'
            ORDER BY CASE WHEN lp.last_accessed IS NULL THEN 1 ELSE 0 END, lp.last_accessed DESC, l.created_at DESC
            LIMIT 5
            ''',
            (st.session_state.user['id'],),
        )

        lessons = cursor.fetchall()

        if lessons:
            for lesson in lessons:
                with st.container():
                    col1, col2, col3 = st.columns([3, 1, 1])

                    with col1:
                        st.markdown(f"**{lesson['title']}**")
                        st.caption(f"Subject: {lesson['subject'] or 'General'}")

                    with col2:
                        progress = lesson['progress_percentage'] or 0
                        st.progress(progress / 100)
                        st.caption(f"{progress:.0f}% complete")

                    with col3:
                        if st.button("Continue", key=f"lesson_{lesson['id']}"):
                            st.session_state.selected_lesson_id = lesson['id']
                            st.switch_page("pages/1_📚_Lessons.py")

                    st.divider()
        else:
            st.info("No lessons available yet. Check back soon!")

    # Learning tips
    st.markdown("### 💡 Learning Tips")
    tips = [
        "Set aside dedicated time each day for learning",
        "Take notes while studying to improve retention",
        "Use the AI chat to clarify any doubts",
        "Review summaries before starting new lessons",
        "Practice with exercises to reinforce learning",
    ]

    for tip in tips:
        st.markdown(f"• {tip}")


def main():
    """Main application entry point"""
    if st.session_state.user is None:
        show_login_page()
    else:
        show_dashboard()


if __name__ == "__main__":
    main()
