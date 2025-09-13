import streamlit as st
import bcrypt
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from database.connection import get_db_connection

load_dotenv()

class AuthService:
    def __init__(self):
        self.email_host = os.getenv('EMAIL_HOST') or st.secrets['EMAIL_HOST']
        self.email_port = os.getenv('EMAIL_PORT') or st.secrets['EMAIL_PORT'] or 587
        self.email_user = os.getenv('EMAIL_USER') or st.secrets['EMAIL_USER']
        self.email_password = os.getenv('EMAIL_PASSWORD') or st.secrets['EMAIL_PASSWORD']
        self.app_url = os.getenv('APP_URL') or st.secrets['APP_URL'] or 'http://localhost:8501'

    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    def generate_token(self) -> str:
        """Generate verification token"""
        return secrets.token_urlsafe(32)
    
    def send_verification_email(self, email: str, token: str):
        """Send email verification; fall back to showing link if SMTP isn't configured."""
        verification_link = f"{self.app_url}?verify={token}"
        try:
            # Fallback for local dev if SMTP isn't configured
            if not self.email_host or not self.email_user or not self.email_password:
                st.warning("Email not configured. Showing verification link below (dev mode).")
                st.info(f"Verification link: {verification_link}")
                return False

            msg = MIMEMultipart('alternative')
            msg['Subject'] = 'Verify Your Email - Learning Platform'
            msg['From'] = self.email_user
            msg['To'] = email

            html = f"""
            <html>
                <body style="font-family: Arial, sans-serif;">
                    <h2>Welcome to Learning Platform!</h2>
                    <p>Please click the link below to verify your email:</p>
                    <a href="{verification_link}" style="display: inline-block; padding: 10px 20px; background-color: #4F8BF5; color: white; text-decoration: none; border-radius: 5px;">
                        Verify Email
                    </a>
                    <p>Or copy this link: {verification_link}</p>
                    <p>This link will expire in 24 hours.</p>
                </body>
            </html>
            """

            msg.attach(MIMEText(html, 'html'))

            # Robust SMTP connect with TLS/SSL handling
            if int(self.email_port) == 465:
                server = smtplib.SMTP_SSL(self.email_host, self.email_port, timeout=10)
            else:
                server = smtplib.SMTP(self.email_host, self.email_port, timeout=10)
                server.ehlo()
                try:
                    server.starttls()
                    server.ehlo()
                except Exception:
                    # Some servers may not require TLS
                    pass

            server.login(self.email_user, self.email_password)
            server.sendmail(self.email_user, email, msg.as_string())
            server.quit()
            return True
        except Exception as e:
            st.error(f"Failed to send email: {str(e)}")
            st.info(f"Use this verification link instead: {verification_link}")
            return False

    # New methods below
    def register_user(self, email: str, username: str, password: str, full_name: str | None = None):
        """Create a new user, store hashed password, and send verification email."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                # Check duplicates
                cursor.execute("SELECT id FROM users WHERE email = ? OR username = ?", (email, username))
                if cursor.fetchone():
                    return False, "Email or username already in use"

                password_hash = self.hash_password(password)
                token = self.generate_token()

                cursor.execute(
                    '''
                    INSERT INTO users (email, username, password_hash, full_name, verification_token, is_verified)
                    VALUES (?, ?, ?, ?, ?, 0)
                    ''',
                    (email, username, password_hash, full_name, token),
                )
                conn.commit()

            # Try to send email (non-blocking for success of registration)
            sent = self.send_verification_email(email, token)
            msg = "Registration successful. Check your email to verify your account."
            if not sent:
                msg += " (Email sending failed; contact admin to verify manually.)"
            return True, msg
        except Exception as e:
            return False, f"Registration failed: {str(e)}"

    def login_user(self, username_or_email: str, password: str):
        """Authenticate user by email or username and set last_login."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM users WHERE email = ? OR username = ?",
                    (username_or_email, username_or_email),
                )
                user = cursor.fetchone()
                if not user:
                    return False, None, "User not found"
                if not self.verify_password(password, user['password_hash']):
                    return False, None, "Incorrect password"
                if not user['is_verified']:
                    return False, None, "Email not verified. Please check your inbox."

                # Update last_login
                cursor.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?", (user['id'],))
                conn.commit()

                # Build session user dict
                user_data = {
                    'id': user['id'],
                    'email': user['email'],
                    'username': user['username'],
                    'full_name': user['full_name'],
                    'role': user['role'],
                    'is_verified': bool(user['is_verified']),
                }
                return True, user_data, "Login successful"
        except Exception as e:
            return False, None, f"Login failed: {str(e)}"

    def verify_email(self, token: str) -> bool:
        """Verify a user's email using the token."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM users WHERE verification_token = ?", (token,))
                user = cursor.fetchone()
                if not user:
                    return False

                cursor.execute(
                    "UPDATE users SET is_verified = 1, verification_token = NULL WHERE id = ?",
                    (user['id'],),
                )
                conn.commit()
                return True
        except Exception:
            return False

    def request_password_reset(self, email: str):
        """Generate a password reset token and email it."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
                user = cursor.fetchone()
                if not user:
                    return False, "No account found with that email"

                token = self.generate_token()
                expires = datetime.utcnow() + timedelta(hours=1)
                cursor.execute(
                    '''
                    INSERT INTO password_resets (user_id, token, expires_at, used)
                    VALUES (?, ?, ?, 0)
                    ''',
                    (user['id'], token, expires),
                )
                conn.commit()

            sent = self.send_password_reset_email(email, token)
            if sent:
                return True, "Password reset link sent to your email"
            else:
                reset_link = f"{self.app_url}?reset={token}"
                return False, f"Email send failed. Use this reset link: {reset_link}"
        except Exception as e:
            return False, f"Failed to request password reset: {str(e)}"

    def send_password_reset_email(self, email: str, token: str) -> bool:
        reset_link = f"{self.app_url}?reset={token}"
        try:
            # Fallback for local dev if SMTP isn't configured
            if not self.email_host or not self.email_user or not self.email_password:
                st.warning("Email not configured. Showing reset link below (dev mode).")
                st.info(f"Reset link: {reset_link}")
                return False

            msg = MIMEMultipart('alternative')
            msg['Subject'] = 'Reset Your Password - Learning Platform'
            msg['From'] = self.email_user
            msg['To'] = email

            html = f"""
            <html>
                <body style="font-family: Arial, sans-serif;">
                    <h2>Reset your password</h2>
                    <p>Click the link below to reset your password. This link expires in 1 hour.</p>
                    <a href="{reset_link}" style="display: inline-block; padding: 10px 20px; background-color: #4F8BF5; color: white; text-decoration: none; border-radius: 5px;">Reset Password</a>
                    <p>Or copy this link: {reset_link}</p>
                </body>
            </html>
            """
            msg.attach(MIMEText(html, 'html'))

            # Robust SMTP connect with TLS/SSL handling
            if int(self.email_port) == 465:
                server = smtplib.SMTP_SSL(self.email_host, self.email_port, timeout=10)
            else:
                server = smtplib.SMTP(self.email_host, self.email_port, timeout=10)
                server.ehlo()
                try:
                    server.starttls()
                    server.ehlo()
                except Exception:
                    pass

            server.login(self.email_user, self.email_password)
            server.sendmail(self.email_user, email, msg.as_string())
            server.quit()
            return True
        except Exception as e:
            st.error(f"Failed to send password reset email: {str(e)}")
            st.info(f"Use this reset link instead: {reset_link}")
            return False
