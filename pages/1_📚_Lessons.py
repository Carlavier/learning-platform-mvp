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
        cursor.execute(
            '''
            INSERT OR REPLACE INTO learning_progress 
            (user_id, lesson_id, progress_percentage, last_accessed)
            VALUES (?, ?, ?, ?)
            ''',
            (st.session_state.user['id'], lesson_id, progress, datetime.now()),
        )
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

        query = (
            '''
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
        )

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
            query += " ORDER BY COALESCE(lp.progress_percentage, 0) DESC"

        cursor.execute(query, params)
        lessons = cursor.fetchall()

    # Display lessons in grid
    if lessons:
        cols = st.columns(3)
        for idx, lesson in enumerate(lessons):
            with cols[idx % 3]:
                with st.container():
                    st.markdown(
                        f"""
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
                        """,
                        unsafe_allow_html=True,
                    )

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
        cursor.execute(
            '''
            SELECT l.*, u.username as author
            FROM lessons l
            LEFT JOIN users u ON l.created_by = u.id
            WHERE l.id = ?
            ''',
            (lesson_id,),
        )

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
                mime="application/octet-stream",
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
                        cursor.execute(
                            '''
                            UPDATE lessons SET summary = ? WHERE id = ?
                            ''',
                            (summary, lesson_id),
                        )
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
                    lesson['content'] or "",
                )

                if extended:
                    # Save extended content
                    with get_db_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute(
                            '''
                            UPDATE lessons SET extended_content = ? WHERE id = ?
                            ''',
                            (extended, lesson_id),
                        )
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
                    chat_history=st.session_state[f'chat_history_{lesson_id}'],
                )

                if response:
                    st.write(response)

                    # Save to session state
                    st.session_state[f'chat_history_{lesson_id}'].append(
                        {
                            'message': prompt,
                            'response': response,
                        }
                    )

                    # Save to database
                    with get_db_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute(
                            '''
                            INSERT INTO chat_history (user_id, lesson_id, message, response)
                            VALUES (?, ?, ?, ?)
                            ''',
                            (st.session_state.user['id'], lesson_id, prompt, response),
                        )
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
