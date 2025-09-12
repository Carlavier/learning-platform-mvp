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
            cursor.execute(
                '''
                SELECT id, title FROM lessons 
                WHERE status = 'published' 
                ORDER BY created_at DESC
                '''
            )
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
            cursor.execute(
                '''
                SELECT DISTINCT message, timestamp 
                FROM chat_history 
                WHERE user_id = ? 
                ORDER BY timestamp DESC 
                LIMIT 5
                ''',
                (st.session_state.user['id'],),
            )

            recent = cursor.fetchall()
            for r in recent:
                st.caption(f"• {r['message'][:30]}...")

    # Initialize chat messages
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
        # Welcome message
        st.session_state.chat_messages.append(
            {
                "role": "assistant",
                "content": "👋 Hi! I'm your AI learning assistant. How can I help you today?",
            }
        )

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
                    chat_history=chat_history,
                )

                if response:
                    st.markdown(response)
                    st.session_state.chat_messages.append({"role": "assistant", "content": response})

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
