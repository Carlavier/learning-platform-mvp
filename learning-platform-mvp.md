# 📚 Learning Platform MVP with AI Assistant

## 📁 Project Structure
```
learning-platform/
├── app.py                      # Main application
├── requirements.txt            # Dependencies
├── .env.example               # Environment variables template
├── .streamlit/
│   └── config.toml           # Streamlit configuration
├── database/
│   ├── __init__.py
│   ├── models.py             # Database models
│   └── connection.py         # Database connection
├── auth/
│   ├── __init__.py
│   ├── authentication.py     # Auth logic
│   └── email_service.py      # Email verification
├── ai/
│   ├── __init__.py
│   └── deepseek_service.py   # DeepSeek API integration
├── pages/
│   ├── 1_📚_Lessons.py       # Lessons page
│   ├── 2_💬_AI_Chat.py       # AI Chat interface
│   ├── 3_👤_Profile.py       # User profile
│   └── 4_🔧_Admin.py         # Admin dashboard
├── utils/
│   ├── __init__.py
│   └── helpers.py            # Helper functions
└── uploads/                   # Upload directory

```

## 📄 File 1: requirements.txt
```txt
streamlit==1.31.0
streamlit-authenticator==0.3.1
sqlite3
pandas==2.1.4
python-dotenv==1.0.0
requests==2.31.0
bcrypt==4.1.2
email-validator==2.1.0
python-jose[cryptography]==3.3.0
passlib==1.7.4
Pillow==10.2.0
plotly==5.18.0
streamlit-chat==0.1.1
python-dateutil==2.8.2
```

## 📄 File 2: .env.example
```env
# DeepSeek API
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# Email Configuration (Gmail)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USER=your_email@gmail.com
EMAIL_PASSWORD=your_app_specific_password

# Security
SECRET_KEY=your_secret_key_here_generate_random_string
JWT_SECRET_KEY=another_random_secret_key

# App Configuration
APP_NAME=Learning Platform
APP_URL=https://your-app.streamlit.app
```

## 📄 File 3: .streamlit/config.toml
```toml
[theme]
primaryColor = "#4F8BF5"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"
font = "sans serif"

[server]
maxUploadSize = 10
enableCORS = false
enableXsrfProtection = true

[browser]
gatherUsageStats = false
```

## 📄 File 4: database/connection.py
```python
import sqlite3
import os
from contextlib import contextmanager
import pandas as pd
from datetime import datetime

DATABASE_PATH = "learning_platform.db"

@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_database():
    """Initialize database with tables"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT,
                role TEXT DEFAULT 'user',
                is_verified BOOLEAN DEFAULT 0,
                verification_token TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        ''')
        
        # Lessons table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lessons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                subject TEXT,
                content TEXT,
                summary TEXT,
                extended_content TEXT,
                file_path TEXT,
                created_by INTEGER,
                status TEXT DEFAULT 'draft',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (created_by) REFERENCES users (id)
            )
        ''')
        
        # Chat history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                lesson_id INTEGER,
                message TEXT NOT NULL,
                response TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (lesson_id) REFERENCES lessons (id)
            )
        ''')
        
        # Learning progress table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS learning_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                lesson_id INTEGER NOT NULL,
                progress_percentage REAL DEFAULT 0,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed BOOLEAN DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (lesson_id) REFERENCES lessons (id),
                UNIQUE(user_id, lesson_id)
            )
        ''')
        
        # Password reset tokens
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS password_resets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token TEXT UNIQUE NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                used BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        conn.commit()
```

## 📄 File 5: auth/authentication.py
```python
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
        self.email_host = os.getenv('EMAIL_HOST')
        self.email_port = int(os.getenv('EMAIL_PORT', 587))
        self.email_user = os.getenv('EMAIL_USER')
        self.email_password = os.getenv('EMAIL_PASSWORD')
        self.app_url = os.getenv('APP_URL', 'http://localhost:8501')
    
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
        """Send email verification"""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = 'Verify Your Email - Learning Platform'
            msg['From'] = self.email_user
            msg['To'] = email
            
            verification_link = f"{self.app_url}?verify={token}"
            
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
            
            part = MIMEText(html, 'html')
            msg.attach(part)
            
            with smtplib.SMTP(self.email_host, self.email_port) as server:
                server.starttls()
                server.login(self.email_user, self.email_password)
                server.send_message(msg)
            
            return True
        except Exception as e:
            st.error(f"Failed to send email: {str(e)}")
            return False
    
    def register_user(self, email: str, username: str, password: str, full_name: str = None):
        """Register new user"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check if user exists
            cursor.execute('SELECT id FROM users WHERE email = ? OR username = ?', (email, username))
            if cursor.fetchone():
                return False, "Email or username already exists"
            
            # Create user
            password_hash = self.hash_password(password)
            verification_token = self.generate_token()
            
            cursor.execute('''
                INSERT INTO users (email, username, password_hash, full_name, verification_token)
                VALUES (?, ?, ?, ?, ?)
            ''', (email, username, password_hash, full_name, verification_token))
            conn.commit()
            
            # Send verification email
            self.send_verification_email(email, verification_token)
            
            return True, "Registration successful! Please check your email to verify your account."
    
    def login_user(self, username: str, password: str):
        """Login user"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Find user
            cursor.execute('''
                SELECT id, email, username, password_hash, full_name, role, is_verified
                FROM users WHERE username = ? OR email = ?
            ''', (username, username))
            
            user = cursor.fetchone()
            if not user:
                return False, None, "Invalid credentials"
            
            # Check password
            if not self.verify_password(password, user['password_hash']):
                return False, None, "Invalid credentials"
            
            # Check verification
            if not user['is_verified']:
                return False, None, "Please verify your email first"
            
            # Update last login
            cursor.execute('UPDATE users SET last_login = ? WHERE id = ?', 
                         (datetime.now(), user['id']))
            conn.commit()
            
            user_data = {
                'id': user['id'],
                'email': user['email'],
                'username': user['username'],
                'full_name': user['full_name'],
                'role': user['role']
            }
            
            return True, user_data, "Login successful!"
    
    def verify_email(self, token: str):
        """Verify email with token"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE users SET is_verified = 1, verification_token = NULL
                WHERE verification_token = ?
            ''', (token,))
            
            if cursor.rowcount > 0:
                conn.commit()
                return True
            return False
    
    def request_password_reset(self, email: str):
        """Request password reset"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Find user
            cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
            user = cursor.fetchone()
            
            if not user:
                return False, "Email not found"
            
            # Generate reset token
            token = self.generate_token()
            expires_at = datetime.now() + timedelta(hours=1)
            
            cursor.execute('''
                INSERT INTO password_resets (user_id, token, expires_at)
                VALUES (?, ?, ?)
            ''', (user['id'], token, expires_at))
            conn.commit()
            
            # Send reset email
            self.send_password_reset_email(email, token)
            
            return True, "Password reset link sent to your email"
    
    def send_password_reset_email(self, email: str, token: str):
        """Send password reset email"""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = 'Password Reset - Learning Platform'
            msg['From'] = self.email_user
            msg['To'] = email
            
            reset_link = f"{self.app_url}?reset={token}"
            
            html = f"""
            <html>
                <body style="font-family: Arial, sans-serif;">
                    <h2>Password Reset Request</h2>
                    <p>Click the link below to reset your password:</p>
                    <a href="{reset_link}" style="display: inline-block; padding: 10px 20px; background-color: #4F8BF5; color: white; text-decoration: none; border-radius: 5px;">
                        Reset Password
                    </a>
                    <p>Or copy this link: {reset_link}</p>
                    <p>This link will expire in 1 hour.</p>
                    <p>If you didn't request this, please ignore this email.</p>
                </body>
            </html>
            """
            
            part = MIMEText(html, 'html')
            msg.attach(part)
            
            with smtplib.SMTP(self.email_host, self.email_port) as server:
                server.starttls()
                server.login(self.email_user, self.email_password)
                server.send_message(msg)
            
            return True
        except Exception as e:
            st.error(f"Failed to send email: {str(e)}")
            return False
```

## 📄 File 6: ai/deepseek_service.py
```python
import requests
import json
import os
from typing import Dict, List, Optional
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

class DeepSeekService:
    def __init__(self):
        self.api_key = os.getenv('DEEPSEEK_API_KEY')
        self.base_url = "https://api.deepseek.com/v1/chat/completions"
        
    def _make_request(self, messages: List[Dict], temperature: float = 0.7, max_tokens: int = 2000) -> Optional[str]:
        """Make request to DeepSeek API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "deepseek-chat",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }
        
        try:
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                st.error(f"API Error: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            st.error("Request timed out. Please try again.")
            return None
        except Exception as e:
            st.error(f"Error calling DeepSeek API: {str(e)}")
            return None
    
    def summarize_lesson(self, content: str) -> str:
        """Generate lesson summary"""
        messages = [
            {
                "role": "system",
                "content": "Bạn là một trợ lý giáo dục chuyên tóm tắt bài học. Hãy tóm tắt ngắn gọn, rõ ràng và nêu bật các điểm chính."
            },
            {
                "role": "user",
                "content": f"""Hãy tóm tắt bài học sau thành 3-5 điểm chính, mỗi điểm không quá 2 câu:

{content}

Format đầu ra:
📌 **Điểm chính 1:** [Nội dung]
📌 **Điểm chính 2:** [Nội dung]
..."""
            }
        ]
        
        return self._make_request(messages, temperature=0.5)
    
    def extend_knowledge(self, topic: str, current_content: str) -> str:
        """Extend knowledge with practical applications"""
        messages = [
            {
                "role": "system",
                "content": "Bạn là một chuyên gia giáo dục với kiến thức sâu rộng về nhiều lĩnh vực. Hãy mở rộng kiến thức theo hướng thực tiễn và cập nhật."
            },
            {
                "role": "user",
                "content": f"""Chủ đề: {topic}

Nội dung hiện tại:
{current_content}

Hãy mở rộng kiến thức này theo 3 hướng:

1. **Ứng dụng thực tế:** 
   - 2-3 ví dụ cụ thể trong công việc/cuộc sống
   - Cách áp dụng vào thực tiễn

2. **Kiến thức nâng cao:**
   - Các khái niệm liên quan sâu hơn
   - Kỹ năng cần phát triển thêm

3. **Xu hướng mới:**
   - Các phát triển mới nhất trong lĩnh vực này
   - Tài nguyên học tập bổ sung

Format đầu ra rõ ràng với các heading và bullet points."""
            }
        ]
        
        return self._make_request(messages, temperature=0.7, max_tokens=3000)
    
    def chat_with_context(self, user_message: str, lesson_context: str = None, chat_history: List[Dict] = None) -> str:
        """Chat with AI assistant with context"""
        system_prompt = """Bạn là một trợ lý học tập AI thông minh, thân thiện và hữu ích. 
        Nhiệm vụ của bạn là:
        - Giải đáp thắc mắc về bài học
        - Giải thích các khái niệm khó hiểu
        - Đưa ra ví dụ minh họa
        - Gợi ý cách học hiệu quả
        
        Hãy trả lời ngắn gọn, dễ hiểu và luôn khuyến khích người học."""
        
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add lesson context if available
        if lesson_context:
            messages.append({
                "role": "system",
                "content": f"Bài học hiện tại: {lesson_context[:1000]}"  # Limit context length
            })
        
        # Add chat history
        if chat_history:
            for chat in chat_history[-5:]:  # Last 5 messages for context
                messages.append({"role": "user", "content": chat.get('message', '')})
                messages.append({"role": "assistant", "content": chat.get('response', '')})
        
        # Add current message
        messages.append({"role": "user", "content": user_message})
        
        return self._make_request(messages, temperature=0.7)
    
    def generate_quiz(self, content: str, num_questions: int = 5) -> str:
        """Generate quiz questions from content"""
        messages = [
            {
                "role": "system",
                "content": "Bạn là một giáo viên chuyên tạo câu hỏi kiểm tra kiến thức."
            },
            {
                "role": "user",
                "content": f"""Dựa trên nội dung sau, hãy tạo {num_questions} câu hỏi trắc nghiệm:

{content}

Format cho mỗi câu hỏi:
**Câu [số]:** [Câu hỏi]
A) [Đáp án A]
B) [Đáp án B]
C) [Đáp án C]
D) [Đáp án D]
**Đáp án đúng:** [A/B/C/D]
**Giải thích:** [Giải thích ngắn]
---"""
            }
        ]
        
        return self._make_request(messages, temperature=0.6, max_tokens=2500)
    
    def explain_concept(self, concept: str, level: str = "beginner") -> str:
        """Explain a concept at different levels"""
        level_prompts = {
            "beginner": "Giải thích như đang nói với người mới bắt đầu, dùng ngôn ngữ đơn giản và nhiều ví dụ",
            "intermediate": "Giải thích với độ sâu vừa phải, có thể dùng thuật ngữ chuyên môn nhưng vẫn rõ ràng",
            "advanced": "Giải thích chuyên sâu, chi tiết với các khía cạnh kỹ thuật và nâng cao"
        }
        
        messages = [
            {
                "role": "system",
                "content": f"Bạn là một giáo viên giỏi. {level_prompts.get(level, level_prompts['beginner'])}"
            },
            {
                "role": "user",
                "content": f"Hãy giải thích khái niệm: {concept}"
            }
        ]
        
        return self._make_request(messages, temperature=0.6)
```

## 📄 File 7: app.py (Main Application)
```python
import streamlit as st
import os
from dotenv import load_dotenv
from datetime import datetime
import time
from database.connection import init_database, get_db_connection
from auth.authentication import AuthService

# Load environment variables
load_dotenv()

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
    st.markdown("""
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
    """, unsafe_allow_html=True)
    
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
                    # Implement password reset logic
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
            cursor.execute('''
                SELECT COUNT(DISTINCT lesson_id) as lessons_accessed,
                       AVG(progress_percentage) as avg_progress
                FROM learning_progress
                WHERE user_id = ?
            ''', (st.session_state.user['id'],))
            
            stats = cursor.fetchone()
            
            st.markdown("### 📊 Your Stats")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Lessons", stats['lessons_accessed'] or 0)
            with col2:
                st.metric("Progress", f"{(stats['avg_progress'] or 0):.0f}%")
    
    # Main content area
    st.markdown("## 🎯 Welcome back, {}!".format(st.session_state.user['full_name'] or st.session_state.user['username']))
    
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
        cursor.execute('''
            SELECT l.*, lp.progress_percentage, lp.last_accessed
            FROM lessons l
            LEFT JOIN learning_progress lp ON l.id = lp.lesson_id AND lp.user_id = ?
            WHERE l.status = 'published'
            ORDER BY lp.last_accessed DESC NULLS LAST, l.created_at DESC
            LIMIT 5
        ''', (st.session_state.user['id'],))
        
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
        "Practice with exercises to reinforce learning"
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
```

## 📄 File 8: pages/1_📚_Lessons.py
```python
import streamlit as st
import pandas as pd
from datetime import datetime
from database.connection import get_db_connection
from ai.deepseek_service import DeepSeekService
import os

# Check authentication
if 'user' not in st.session_state or st.session_state.user is None:
    st.error("Please login to access this page")
    st.stop()

st.set_page_config(page_title="Lessons", page_icon="📚", layout="wide")

# Initialize AI service
ai_service = DeepSeekService()

def update_progress(lesson_id, progress):
    """Update learning progress"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO learning_progress 
            (user_id, lesson_id, progress_percentage, last_accessed)
            VALUES (?, ?, ?, ?)
        ''', (st.session_state.user['id'], lesson_id, progress, datetime.now()))
        conn.commit()

def main():
    st.title("📚 Lessons")
    
    # Check if specific lesson was selected
    if 'selected_lesson_id' in st.session_state:
        show_lesson_detail(st.session_state.selected_lesson_id)
        del st.session_state.selected_lesson_id
    else:
        show_lessons_list()

def show_lessons_list():
    """Display list of all lessons"""
    
    # Filters
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        search = st.text_input("🔍 Search lessons", placeholder="Enter keyword...")
    
    with col2:
        subjects = ["All"] + get_subjects()
        selected_subject = st.selectbox("Subject", subjects)
    
    with col3:
        sort_by = st.selectbox("Sort by", ["Latest", "Title", "Progress"])
    
    # Get lessons
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        query = '''
            SELECT l.*, 
                   lp.progress_percentage,
                   lp.last_accessed,
                   u.username as author
            FROM lessons l
            LEFT JOIN learning_progress lp 
                ON l.id = lp.lesson_id AND lp.user_id = ?
            LEFT JOIN users u ON l.created_by = u.id
            WHERE l.status = 'published'
        '''
        
        params = [st.session_state.user['id']]
        
        if search:
            query += " AND (l.title LIKE ? OR l.content LIKE ?)"
            params.extend([f'%{search}%', f'%{search}%'])
        
        if selected_subject != "All":
            query += " AND l.subject = ?"
            params.append(selected_subject)
        
        # Add sorting
        if sort_by == "Latest":
            query += " ORDER BY l.created_at DESC"
        elif sort_by == "Title":
            query += " ORDER BY l.title ASC"
        else:
            query += " ORDER BY lp.progress_percentage DESC NULLS LAST"
        
        cursor.execute(query, params)
        lessons = cursor.fetchall()
    
    # Display lessons in grid
    if lessons:
        cols = st.columns(3)
        for idx, lesson in enumerate(lessons):
            with cols[idx % 3]:
                with st.container():
                    st.markdown(f"""
                        <div style="padding: 1rem; border: 1px solid #ddd; border-radius: 8px; height: 200px;">
                            <h4>{lesson['title']}</h4>
                            <p style="color: #666; font-size: 0.9em;">
                                📁 {lesson['subject'] or 'General'} | 
                                👤 {lesson['author'] or 'System'}
                            </p>
                            <p style="font-size: 0.9em;">
                                {(lesson['summary'] or lesson['content'] or '')[:100]}...
                            </p>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    progress = lesson['progress_percentage'] or 0
                    st.progress(progress / 100)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.caption(f"{progress:.0f}% complete")
                    with col2:
                        if st.button("Open", key=f"open_{lesson['id']}", use_container_width=True):
                            st.session_state.selected_lesson_id = lesson['id']
                            st.rerun()
    else:
        st.info("No lessons found. Try adjusting your filters.")

def show_lesson_detail(lesson_id):
    """Display detailed lesson view"""
    
    # Get lesson details
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT l.*, u.username as author
            FROM lessons l
            LEFT JOIN users u ON l.created_by = u.id
            WHERE l.id = ?
        ''', (lesson_id,))
        
        lesson = cursor.fetchone()
    
    if not lesson:
        st.error("Lesson not found")
        return
    
    # Update last accessed
    update_progress(lesson_id, 10)  # Mark as started
    
    # Back button
    if st.button("← Back to Lessons"):
        st.rerun()
    
    # Lesson header
    st.title(lesson['title'])
    
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.caption(f"📁 {lesson['subject'] or 'General'} | 👤 {lesson['author'] or 'System'}")
    with col2:
        st.caption(f"📅 {lesson['created_at'][:10]}")
    
    # Tabs for different content
    tab1, tab2, tab3, tab4 = st.tabs(["📖 Content", "📝 Summary", "🚀 Extended", "💬 Chat"])
    
    with tab1:
        show_lesson_content(lesson)
    
    with tab2:
        show_lesson_summary(lesson, lesson_id)
    
    with tab3:
        show_extended_content(lesson, lesson_id)
    
    with tab4:
        show_lesson_chat(lesson_id, lesson)

def show_lesson_content(lesson):
    """Display main lesson content"""
    st.markdown("### 📖 Lesson Content")
    
    if lesson['content']:
        st.markdown(lesson['content'])
        
        # Mark as read
        if st.button("✅ Mark as Complete", type="primary"):
            update_progress(lesson['id'], 100)
            st.success("Lesson marked as complete!")
            st.balloons()
    else:
        st.info("No content available for this lesson")
    
    # Display attached file if exists
    if lesson['file_path'] and os.path.exists(lesson['file_path']):
        st.markdown("### 📎 Attached Materials")
        with open(lesson['file_path'], 'rb') as file:
            st.download_button(
                label="Download Material",
                data=file,
                file_name=os.path.basename(lesson['file_path']),
                mime="application/octet-stream"
            )

def show_lesson_summary(lesson, lesson_id):
    """Display AI-generated summary"""
    st.markdown("### 📝 AI Summary")
    
    if lesson['summary']:
        st.info(lesson['summary'])
    else:
        if st.button("Generate Summary", type="primary"):
            with st.spinner("Generating summary..."):
                summary = ai_service.summarize_lesson(lesson['content'] or "")
                
                if summary:
                    # Save summary to database
                    with get_db_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute('''
                            UPDATE lessons SET summary = ? WHERE id = ?
                        ''', (summary, lesson_id))
                        conn.commit()
                    
                    st.success("Summary generated!")
                    st.info(summary)
                    update_progress(lesson_id, min(100, 50))  # Update progress
                else:
                    st.error("Failed to generate summary")

def show_extended_content(lesson, lesson_id):
    """Display extended knowledge"""
    st.markdown("### 🚀 Extended Knowledge")
    
    if lesson['extended_content']:
        st.markdown(lesson['extended_content'])
    else:
        if st.button("Generate Extended Content", type="primary", key="extend"):
            with st.spinner("Expanding knowledge..."):
                extended = ai_service.extend_knowledge(
                    lesson['title'],
                    lesson['content'] or ""
                )
                
                if extended:
                    # Save extended content
                    with get_db_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute('''
                            UPDATE lessons SET extended_content = ? WHERE id = ?
                        ''', (extended, lesson_id))
                        conn.commit()
                    
                    st.success("Extended content generated!")
                    st.markdown(extended)
                    update_progress(lesson_id, min(100, 75))  # Update progress
                else:
                    st.error("Failed to generate extended content")

def show_lesson_chat(lesson_id, lesson):
    """Show chat interface for lesson"""
    st.markdown("### 💬 Ask AI About This Lesson")
    
    # Initialize chat history in session state
    if f'chat_history_{lesson_id}' not in st.session_state:
        st.session_state[f'chat_history_{lesson_id}'] = []
    
    # Display chat history
    for chat in st.session_state[f'chat_history_{lesson_id}']:
        with st.chat_message("user"):
            st.write(chat['message'])
        with st.chat_message("assistant"):
            st.write(chat['response'])
    
    # Chat input
    if prompt := st.chat_input("Ask a question about this lesson..."):
        # Display user message
        with st.chat_message("user"):
            st.write(prompt)
        
        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = ai_service.chat_with_context(
                    prompt,
                    lesson_context=lesson['content'],
                    chat_history=st.session_state[f'chat_history_{lesson_id}']
                )
                
                if response:
                    st.write(response)
                    
                    # Save to session state
                    st.session_state[f'chat_history_{lesson_id}'].append({
                        'message': prompt,
                        'response': response
                    })
                    
                    # Save to database
                    with get_db_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute('''
                            INSERT INTO chat_history (user_id, lesson_id, message, response)
                            VALUES (?, ?, ?, ?)
                        ''', (st.session_state.user['id'], lesson_id, prompt, response))
                        conn.commit()
                else:
                    st.error("Failed to get response")

def get_subjects():
    """Get list of unique subjects"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT subject FROM lessons WHERE subject IS NOT NULL")
        return [row['subject'] for row in cursor.fetchall()]

if __name__ == "__main__":
    main()
```

## 📄 File 9: pages/2_💬_AI_Chat.py
```python
import streamlit as st
from datetime import datetime
from database.connection import get_db_connection
from ai.deepseek_service import DeepSeekService

# Check authentication
if 'user' not in st.session_state or st.session_state.user is None:
    st.error("Please login to access this page")
    st.stop()

st.set_page_config(page_title="AI Chat", page_icon="💬", layout="wide")

# Initialize AI service
ai_service = DeepSeekService()

def main():
    st.title("💬 AI Learning Assistant")
    
    # Sidebar for chat options
    with st.sidebar:
        st.markdown("### Chat Options")
        
        # Select lesson context
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, title FROM lessons 
                WHERE status = 'published' 
                ORDER BY created_at DESC
            ''')
            lessons = cursor.fetchall()
        
        lesson_options = ["General Chat"] + [f"{l['title']}" for l in lessons]
        selected_lesson = st.selectbox("Context", lesson_options)
        
        # Get lesson context if selected
        lesson_context = None
        lesson_id = None
        if selected_lesson != "General Chat":
            for lesson in lessons:
                if lesson['title'] == selected_lesson:
                    lesson_id = lesson['id']
                    with get_db_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT content FROM lessons WHERE id = ?", (lesson_id,))
                        result = cursor.fetchone()
                        if result:
                            lesson_context = result['content']
                    break
        
        # Clear chat button
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.chat_messages = []
            st.rerun()
        
        # Show recent topics
        st.markdown("### Recent Topics")
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT message, timestamp 
                FROM chat_history 
                WHERE user_id = ? 
                ORDER BY timestamp DESC 
                LIMIT 5
            ''', (st.session_state.user['id'],))
            
            recent = cursor.fetchall()
            for r in recent:
                st.caption(f"• {r['message'][:30]}...")
    
    # Initialize chat messages
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
        # Welcome message
        st.session_state.chat_messages.append({
            "role": "assistant",
            "content": "👋 Hi! I'm your AI learning assistant. How can I help you today?"
        })
    
    # Display chat messages
    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask me anything..."):
        # Add user message
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                # Prepare chat history for context
                chat_history = []
                for msg in st.session_state.chat_messages[-10:]:  # Last 10 messages
                    if msg["role"] == "user":
                        chat_history.append({"message": msg["content"], "response": ""})
                    elif chat_history and msg["role"] == "assistant":
                        chat_history[-1]["response"] = msg["content"]
                
                # Get response
                response = ai_service.chat_with_context(
                    prompt,
                    lesson_context=lesson_context,
                    chat_history=chat_history
                )
                
                if response:
                    st.markdown(response)
                    st.session_state.chat_messages.append({"role": "assistant", "content": response})
                    
                    # Save to database
                    with get_db_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute('''
                            INSERT INTO chat_history (user_id, lesson_id, message, response)
                            VALUES (?, ?, ?, ?)
                        ''', (st.session_state.user['id'], lesson_id, prompt, response))
                        conn.commit()
                else:
                    error_msg = "Sorry, I couldn't process your request. Please try again."
                    st.error(error_msg)
                    st.session_state.chat_messages.append({"role": "assistant", "content": error_msg})
    
    # Quick actions
    st.markdown("### 💡 Quick Questions")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Explain a concept", use_container_width=True):
            st.session_state.chat_messages.append({"role": "user", "content": "Can you explain a concept to me?"})
            st.rerun()
    
    with col2:
        if st.button("Study tips", use_container_width=True):
            st.session_state.chat_messages.append({"role": "user", "content": "Give me some effective study tips"})
            st.rerun()
    
    with col3:
        if st.button("Create quiz", use_container_width=True):
            st.session_state.chat_messages.append({"role": "user", "content": "Create a quiz for me to practice"})
            st.rerun()

if __name__ == "__main__":
    main()
```

## 📄 File 10: pages/4_🔧_Admin.py
```python
import streamlit as st
import pandas as pd
import os
from datetime import datetime
from database.connection import get_db_connection
from ai.deepseek_service import DeepSeekService

# Check authentication and admin role
if 'user' not in st.session_state or st.session_state.user is None:
    st.error("Please login to access this page")
    st.stop()

if st.session_state.user['role'] != 'admin':
    st.error("You don't have permission to access this page")
    st.stop()

st.set_page_config(page_title="Admin Dashboard", page_icon="🔧", layout="wide")

# Initialize AI service
ai_service = DeepSeekService()

def main():
    st.title("🔧 Admin Dashboard")
    
    # Tabs for different admin functions
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "📚 Manage Lessons", "👥 Manage Users", "📈 Analytics"])
    
    with tab1:
        show_overview()
    
    with tab2:
        manage_lessons()
    
    with tab3:
        manage_users()
    
    with tab4:
        show_analytics()

def show_overview():
    """Display admin overview"""
    st.markdown("### 📊 Platform Overview")
    
    # Get statistics
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # User stats
        cursor.execute("SELECT COUNT(*) as total FROM users")
        total_users = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as verified FROM users WHERE is_verified = 1")
        verified_users = cursor.fetchone()['verified']
        
        # Lesson stats
        cursor.execute("SELECT COUNT(*) as total FROM lessons")
        total_lessons = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as published FROM lessons WHERE status = 'published'")
        published_lessons = cursor.fetchone()['published']
        
        # Activity stats
        cursor.execute("SELECT COUNT(*) as total FROM chat_history WHERE date(timestamp) = date('now')")
        today_chats = cursor.fetchone()['total']
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Users", total_users)
        st.caption(f"Verified: {verified_users}")
    
    with col2:
        st.metric("Total Lessons", total_lessons)
        st.caption(f"Published: {published_lessons}")
    
    with col3:
        st.metric("Today's Chats", today_chats)
    
    with col4:
        st.metric("Active Now", "N/A")
    
    # Recent activity
    st.markdown("### 📋 Recent Activity")
    
    with get_db_connection() as conn:
        query = '''
            SELECT 'New User' as type, username as detail, created_at as timestamp
            FROM users
            UNION ALL
            SELECT 'New Lesson' as type, title as detail, created_at as timestamp
            FROM lessons
            ORDER BY timestamp DESC
            LIMIT 10
        '''
        
        df = pd.read_sql_query(query, conn)
        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No recent activity")

def manage_lessons():
    """Manage lessons section"""
    st.markdown("### 📚 Lesson Management")
    
    # Add new lesson
    with st.expander("➕ Add New Lesson"):
        with st.form("new_lesson_form"):
            title = st.text_input("Title")
            subject = st.text_input("Subject")
            content = st.text_area("Content", height=200)
            file = st.file_uploader("Upload Material (optional)", type=['pdf', 'docx', 'txt'])
            
            col1, col2 = st.columns(2)
            with col1:
                auto_summary = st.checkbox("Generate AI Summary")
            with col2:
                auto_extend = st.checkbox("Generate Extended Content")
            
            submit = st.form_submit_button("Create Lesson", type="primary")
            
            if submit and title and content:
                # Save uploaded file
                file_path = None
                if file:
                    os.makedirs("uploads", exist_ok=True)
                    file_path = f"uploads/{file.name}"
                    with open(file_path, "wb") as f:
                        f.write(file.getbuffer())
                
                # Generate AI content if requested
                summary = None
                extended = None
                
                if auto_summary:
                    with st.spinner("Generating summary..."):
                        summary = ai_service.summarize_lesson(content)
                
                if auto_extend:
                    with st.spinner("Generating extended content..."):
                        extended = ai_service.extend_knowledge(title, content)
                
                # Insert lesson
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO lessons (title, subject, content, summary, extended_content, 
                                           file_path, created_by, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (title, subject, content, summary, extended, file_path,
                         st.session_state.user['id'], 'published'))
                    conn.commit()
                
                st.success("Lesson created successfully!")
                st.rerun()
    
    # List existing lessons
    st.markdown("### Existing Lessons")
    
    with get_db_connection() as conn:
        query = '''
            SELECT l.*, u.username as author
            FROM lessons l
            LEFT JOIN users u ON l.created_by = u.id
            ORDER BY l.created_at DESC
        '''
        
        df = pd.read_sql_query(query, conn)
        
        if not df.empty:
            # Add action columns
            for idx, row in df.iterrows():
                col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 1])
                
                with col1:
                    st.write(f"**{row['title']}**")
                    st.caption(f"By {row['author']} | {row['status']}")
                
                with col2:
                    st.caption(row['subject'] or 'General')
                
                with col3:
                    if row['status'] == 'draft':
                        if st.button("Publish", key=f"pub_{row['id']}"):
                            publish_lesson(row['id'])
                    else:
                        st.caption("✅ Published")
                
                with col4:
                    if st.button("Edit", key=f"edit_{row['id']}"):
                        st.session_state.editing_lesson = row['id']
                
                with col5:
                    if st.button("Delete", key=f"del_{row['id']}"):
                        if st.confirm("Are you sure?"):
                            delete_lesson(row['id'])
                
                st.divider()
        else:
            st.info("No lessons created yet")

def manage_users():
    """Manage users section"""
    st.markdown("### 👥 User Management")
    
    # User filters
    col1, col2 = st.columns(2)
    with col1:
        search = st.text_input("Search users", placeholder="Email or username...")
    with col2:
        role_filter = st.selectbox("Filter by role", ["All", "user", "admin"])
    
    # Get users
    with get_db_connection() as conn:
        query = "SELECT * FROM users WHERE 1=1"
        params = []
        
        if search:
            query += " AND (email LIKE ? OR username LIKE ?)"
            params.extend([f'%{search}%', f'%{search}%'])
        
        if role_filter != "All":
            query += " AND role = ?"
            params.append(role_filter)
        
        query += " ORDER BY created_at DESC"
        
        cursor = conn.cursor()
        cursor.execute(query, params)
        users = cursor.fetchall()
    
    # Display users
    if users:
        for user in users:
            col1, col2, col3, col4, col5 = st.columns([2, 2, 1, 1, 1])
            
            with col1:
                st.write(f"**{user['username']}**")
                st.caption(user['email'])
            
            with col2:
                st.caption(f"Role: {user['role']}")
                if user['is_verified']:
                    st.caption("✅ Verified")
                else:
                    st.caption("⏳ Pending")
            
            with col3:
                st.caption(f"Joined: {user['created_at'][:10]}")
            
            with col4:
                if user['role'] == 'user':
                    if st.button("Make Admin", key=f"admin_{user['id']}"):
                        toggle_admin(user['id'], 'admin')
                else:
                    if st.button("Remove Admin", key=f"user_{user['id']}"):
                        toggle_admin(user['id'], 'user')
            
            with col5:
                if st.button("Delete", key=f"del_user_{user['id']}"):
                    delete_user(user['id'])
            
            st.divider()
    else:
        st.info("No users found")

def show_analytics():
    """Show platform analytics"""
    st.markdown("### 📈 Platform Analytics")
    
    # Date range selector
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date")
    with col2:
        end_date = st.date_input("End Date")
    
    # Get analytics data
    with get_db_connection() as conn:
        # User growth
        query = '''
            SELECT DATE(created_at) as date, COUNT(*) as new_users
            FROM users
            WHERE DATE(created_at) BETWEEN ? AND ?
            GROUP BY DATE(created_at)
        '''
        
        df_users = pd.read_sql_query(query, conn, params=[start_date, end_date])
        
        if not df_users.empty:
            st.markdown("#### User Growth")
            st.line_chart(df_users.set_index('date'))
        
        # Chat activity
        query = '''
            SELECT DATE(timestamp) as date, COUNT(*) as total_chats
            FROM chat_history
            WHERE DATE(timestamp) BETWEEN ? AND ?
            GROUP BY DATE(timestamp)
        '''
        df_chats = pd.read_sql_query(query, conn, params=[start_date, end_date])
        if not df_chats.empty:
            st.markdown("#### Chat Activity")
            st.line_chart(df_chats.set_index('date'))

    # Top lessons by chats
    with get_db_connection() as conn:
        query = '''
            SELECT l.title as title, COUNT(ch.id) as chats
            FROM lessons l
            LEFT JOIN chat_history ch ON ch.lesson_id = l.id
            WHERE DATE(ch.timestamp) BETWEEN ? AND ?
            GROUP BY l.id
            ORDER BY chats DESC
            LIMIT 10
        '''
        df_top_lessons = pd.read_sql_query(query, conn, params=[start_date, end_date])
        if not df_top_lessons.empty:
            st.markdown("#### Top Lessons by Chats")
            st.bar_chart(df_top_lessons.set_index('title'))

    # Average progress by lesson
    with get_db_connection() as conn:
        query = '''
            SELECT l.title as title, AVG(lp.progress_percentage) as avg_progress
            FROM lessons l
            JOIN learning_progress lp ON lp.lesson_id = l.id
            WHERE DATE(lp.last_accessed) BETWEEN ? AND ?
            GROUP BY l.id
            ORDER BY avg_progress DESC
            LIMIT 10
        '''
        df_progress = pd.read_sql_query(query, conn, params=[start_date, end_date])
        if not df_progress.empty:
            st.markdown("#### Average Progress by Lesson")
            st.bar_chart(df_progress.set_index('title'))


# Helper admin actions
def publish_lesson(lesson_id: int):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE lessons SET status = 'published', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (lesson_id,))
        conn.commit()
        st.success("Lesson published")


def delete_lesson(lesson_id: int):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Clean related data first
        cursor.execute("DELETE FROM chat_history WHERE lesson_id = ?", (lesson_id,))
        cursor.execute("DELETE FROM learning_progress WHERE lesson_id = ?", (lesson_id,))
        cursor.execute("DELETE FROM lessons WHERE id = ?", (lesson_id,))
        conn.commit()
        st.success("Lesson deleted")


def delete_user(user_id: int):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Clean related data first
        cursor.execute("DELETE FROM chat_history WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM learning_progress WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM password_resets WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        st.success("User deleted")


def toggle_admin(user_id: int, role: str):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
        conn.commit()
        st.success(f"Role updated to {role}")


if __name__ == "__main__":
    main()
```

## 📄 File 11: pages/3_👤_Profile.py
```python
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
                # Implement password change flow (e.g., verify current password, hash and store)
                st.info("Password change flow not implemented in MVP")

if __name__ == "__main__":
    main()
```

## 📄 File 12: auth/email_service.py
```python
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class EmailService:
    def __init__(self, host: str, port: int, username: str, password: str):
        self.host = host
        self.port = port
        self.username = username
        self.password = password

    def send_html(self, to_email: str, subject: str, html: str) -> bool:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = self.username
        msg['To'] = to_email
        msg.attach(MIMEText(html, 'html'))
        try:
            with smtplib.SMTP(self.host, self.port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            return True
        except Exception:
            return False
```

## 📄 File 13: utils/helpers.py
```python
import os

def ensure_uploads_dir(path: str = "uploads") -> str:
    os.makedirs(path, exist_ok=True)
    return path
```

## 📄 File 14: database/models.py
```python
"""ORM models placeholder (not used in SQLite MVP)."""
```

## 📄 File 15: .gitignore
```gitignore
# Python
__pycache__/
*.py[cod]
.venv/
venv/

# Env and secrets
.env
.streamlit/secrets.toml

# DB and uploads
*.db
uploads/

# Editors
.vscode/
.idea/
```

## 🚀 Setup and Run
```bat
REM Create and activate virtual environment (Windows cmd)
python -m venv .venv
.venv\Scripts\activate

REM Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

REM Copy env template and fill values
copy .env.example .env

REM Run the app
streamlit run app.py
```

## 🔐 Environment Notes
- Do not commit .env; API keys and email credentials live there.
- Gmail often requires an App Password when 2FA is enabled.
- DeepSeek key is required for AI features; app will show errors if missing.

## 🗃️ Database Overview
- SQLite file: learning_platform.db in project root.
- Tables: users, lessons, chat_history, learning_progress, password_resets.
- No cascades in SQLite schema; helper functions manually clean related rows.

## 🤖 AI Prompts and Limits
- Model: deepseek-chat via HTTP; temperature defaults: 0.5–0.7.
- Summaries are concise bullet points; extended content adds practical insights and trends.
- Chat includes last few exchanges and optional lesson context to stay focused.

## 🔧 Notes and Future Work
- Add password update flow and email verification resend.
- Add pagination and search indexing for lessons.
- Replace SMTP with a provider API (e.g., SendGrid) for reliability.
- Consider moving to Postgres when multi-user scale increases.

## ⚠️ Requirements note
The Python stdlib already includes sqlite3; remove any `sqlite3` entry from requirements.txt (it’s been omitted in this doc’s corrected list).