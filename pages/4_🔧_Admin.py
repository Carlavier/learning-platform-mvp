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
        query = (
            '''
            SELECT 'New User' as type, username as detail, created_at as timestamp
            FROM users
            UNION ALL
            SELECT 'New Lesson' as type, title as detail, created_at as timestamp
            FROM lessons
            ORDER BY timestamp DESC
            LIMIT 10
            '''
        )

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
                    cursor.execute(
                        '''
                        INSERT INTO lessons (title, subject, content, summary, extended_content, 
                                           file_path, created_by, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''',
                        (
                            title,
                            subject,
                            content,
                            summary,
                            extended,
                            file_path,
                            st.session_state.user['id'],
                            'published',
                        ),
                    )
                    conn.commit()

                st.success("Lesson created successfully!")
                st.rerun()

    # List existing lessons
    st.markdown("### Existing Lessons")

    with get_db_connection() as conn:
        query = (
            '''
            SELECT l.*, u.username as author
            FROM lessons l
            LEFT JOIN users u ON l.created_by = u.id
            ORDER BY l.created_at DESC
            '''
        )

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
        query = (
            '''
            SELECT DATE(created_at) as date, COUNT(*) as new_users
            FROM users
            WHERE DATE(created_at) BETWEEN ? AND ?
            GROUP BY DATE(created_at)
            '''
        )

        df_users = pd.read_sql_query(query, conn, params=[start_date, end_date])

        if not df_users.empty:
            st.markdown("#### User Growth")
            st.line_chart(df_users.set_index('date'))

        # Chat activity
        query = (
            '''
            SELECT DATE(timestamp) as date, COUNT(*) as total_chats
            FROM chat_history
            WHERE DATE(timestamp) BETWEEN ? AND ?
            GROUP BY DATE(timestamp)
            '''
        )
        df_chats = pd.read_sql_query(query, conn, params=[start_date, end_date])
        if not df_chats.empty:
            st.markdown("#### Chat Activity")
            st.line_chart(df_chats.set_index('date'))

    # Top lessons by chats
    with get_db_connection() as conn:
        query = (
            '''
            SELECT l.title as title, COUNT(ch.id) as chats
            FROM lessons l
            LEFT JOIN chat_history ch ON ch.lesson_id = l.id
            WHERE DATE(ch.timestamp) BETWEEN ? AND ?
            GROUP BY l.id
            ORDER BY chats DESC
            LIMIT 10
            '''
        )
        df_top_lessons = pd.read_sql_query(query, conn, params=[start_date, end_date])
        if not df_top_lessons.empty:
            st.markdown("#### Top Lessons by Chats")
            st.bar_chart(df_top_lessons.set_index('title'))

    # Average progress by lesson
    with get_db_connection() as conn:
        query = (
            '''
            SELECT l.title as title, AVG(lp.progress_percentage) as avg_progress
            FROM lessons l
            JOIN learning_progress lp ON lp.lesson_id = l.id
            WHERE DATE(lp.last_accessed) BETWEEN ? AND ?
            GROUP BY l.id
            ORDER BY avg_progress DESC
            LIMIT 10
            '''
        )
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
