import requests
import json
import os
from typing import Dict, List, Optional
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

class DeepSeekService:
    def __init__(self):
        self.api_key = os.getenv('DEEPSEEK_API_KEY') or st.secrets['DEEPSEEK_API_KEY']
        # Allow overriding base URL and model via env
        self.base_url = os.getenv('DEEPSEEK_BASE_URL') or st.secrets['DEEPSEEK_BASE_URL'] or "https://api.deepseek.com/v1/chat/completions"
        self.model = os.getenv('DEEPSEEK_MODEL', 'deepseek-chat') or st.secrets['DEEPSEEK_MODEL'] or 'deepseek-chat'
        # Optional request timeout override (seconds)
        try:
            self.timeout = float(os.getenv('DEEPSEEK_TIMEOUT', '30') or st.secrets['DEEPSEEK_TIMEOUT'] or '30')
        except Exception:
            self.timeout = 30.0
        
    def _make_request(self, messages: List[Dict], temperature: float = 0.7, max_tokens: int = 200) -> Optional[str]:
        """Make request to DeepSeek API"""
        if not self.api_key:
            st.warning("DEEPSEEK_API_KEY not set. Returning a placeholder response.")
            # Basic local fallback to avoid hard failures in dev
            # Return the assistant content from the last assistant message if present
            for m in reversed(messages):
                if m.get("role") == "assistant":
                    return m.get("content")
            return "[AI not configured]"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
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
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                # Show full body to help diagnose (invalid key, quota, model access)
                try:
                    err_json = response.json()
                    st.error(f"DeepSeek API error {response.status_code}: {err_json}")
                except Exception:
                    st.error(f"DeepSeek API error {response.status_code}: {response.text}")
                return None

            # Validate success shape
            try:
                result = response.json()
            except Exception:
                st.error("DeepSeek API returned non-JSON response")
                return None

            # Handle API-level error objects
            if isinstance(result, dict) and 'error' in result:
                st.error(f"DeepSeek API error: {result['error']}")
                return None

            try:
                content = result['choices'][0]['message']['content']
            except Exception:
                st.error(f"Unexpected DeepSeek response format: {result}")
                return None

            if isinstance(content, str) and content.strip().lower() in {"[ai not configured]", "ai not configured"}:
                st.error(
                    "DeepSeek responded with '[AI not configured]'. Check: "
                    "(1) your DEEPSEEK_API_KEY validity/quota, (2) DEEPSEEK_MODEL availability, "
                    "and (3) DEEPSEEK_BASE_URL correctness."
                )
                return None

            return content
                
        except requests.exceptions.Timeout:
            st.error("Request timed out. Please try again.")
            return None
        except Exception as e:
            st.error(f"Error calling DeepSeek API: {str(e)}")
            return None

    def chat_with_context(
        self,
        prompt: str,
        lesson_context: Optional[str] = None,
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> Optional[str]:
        """General chat with optional lesson context and short history.
        chat_history: list of {"message": user_msg, "response": assistant_msg}
        """
        system = (
            "You are an expert AI learning assistant. Be concise, clear, and helpful."
            " Use markdown for structure, bullet points for lists, and examples when useful."
        )
        if lesson_context:
            system += (
                " You have the following lesson context available. Prefer it over external knowledge: "
                f"\n\n--- Lesson Context ---\n{lesson_context[:4000]}\n----------------------"
            )

        messages: List[Dict[str, str]] = [{"role": "system", "content": system}]

        if chat_history:
            for turn in chat_history[-6:]:
                user_msg = turn.get("message")
                assistant_msg = turn.get("response")
                if user_msg:
                    messages.append({"role": "user", "content": user_msg})
                if assistant_msg:
                    messages.append({"role": "assistant", "content": assistant_msg})

        messages.append({"role": "user", "content": prompt})
        return self._make_request(messages, temperature=0.6, max_tokens=200)

    def summarize_lesson(self, content: str) -> Optional[str]:
        """Create a student-friendly summary with key points and takeaways."""
        if not content:
            return "No content to summarize."
        messages = [
            {"role": "system", "content": "You summarize lessons for students. Keep it clear and concise."},
            {
                "role": "user",
                "content": (
                    "Summarize the following lesson. Include: \n"
                    "1) A short overview (2-3 sentences)\n"
                    "2) 4-6 bullet key points\n"
                    "3) A practical tip or example.\n\n"
                    f"Lesson Content:\n{content[:6000]}"
                ),
            },
        ]
        return self._make_request(messages, temperature=0.5, max_tokens=800)

    def extend_knowledge(self, title: str, content: str) -> Optional[str]:
        """Expand lesson with related concepts, examples, and further reading."""
        base = content or title or ""
        if not base:
            return "No input to extend."
        messages = [
            {"role": "system", "content": "You extend lessons with related knowledge and examples."},
            {
                "role": "user",
                "content": (
                    f"Expand the lesson '{title}'.\n"
                    "Add 2-3 related concepts, a real-world example, and a short practice exercise.\n\n"
                    f"Lesson Content:\n{content[:6000]}"
                ),
            },
        ]
        return self._make_request(messages, temperature=0.7, max_tokens=1200)

    def generate_quiz(self, content: str, num_questions: int = 5) -> Optional[str]:
        """Generate a small quiz in markdown with answers hidden below spoilers."""
        if not content:
            return "No content to quiz on."
        messages = [
            {"role": "system", "content": "You create short quizzes for students."},
            {
                "role": "user",
                "content": (
                    f"Create a {num_questions}-question quiz from this content."
                    " Use multiple-choice or short-answer. Provide an 'Answers' section at the end.\n\n"
                    f"Content:\n{content[:6000]}"
                ),
            },
        ]
        return self._make_request(messages, temperature=0.6, max_tokens=1000)

    def explain_concept(self, concept: str) -> Optional[str]:
        """Explain a concept simply with an analogy and an example."""
        if not concept:
            return "No concept provided."
        messages = [
            {"role": "system", "content": "You explain concepts simply for students."},
            {
                "role": "user",
                "content": (
                    f"Explain '{concept}' to a beginner. Include: a definition, a simple analogy,"
                    " and a short real-world example."
                ),
            },
        ]
        return self._make_request(messages, temperature=0.5, max_tokens=600)
