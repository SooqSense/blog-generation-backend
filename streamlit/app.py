#!/usr/bin/env python3
"""
Main Streamlit application entry point for AI Blog Generator.
Uses Django API calls and reads configuration from Django settings.
"""

import streamlit as st
import requests
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from authentication.auth_service import StreamlitAuthManager
from authentication.ui_components import AuthUI, SidebarAuth

# --- Streamlit setup ---
st.set_page_config(
    page_title="AI Blog Generator",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"About": "AI Blog Generator - Professional content creation platform"},
)

# --- Load backend API base URL from environment variables ---
API_BASE_URL = os.getenv("BACKEND_API_BASE_URL", "http://localhost:8000")

# --- Utility functions ---

def load_custom_css():
    css_path = Path(__file__).parent / "base" / "style.css"
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)

def call_api(endpoint: str, method: str = "GET", data=None, files=None, params=None):
    """Helper for making API requests with JWT authentication."""
    url = f"{API_BASE_URL.rstrip('/')}/{endpoint.lstrip('/')}"
    headers = {"Content-Type": "application/json"}

    # Get auth manager and add JWT token if available
    auth_manager = StreamlitAuthManager()
    auth_headers = auth_manager.get_auth_headers()
    headers.update(auth_headers)

    try:
        if method == "GET":
            response = requests.get(url, params=params, headers=headers)
        elif method == "POST":
            response = requests.post(url, json=data, files=files, headers=headers)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API request failed: {e}")
        return None

# --- Auth + UI ---

def handle_auth():
    """Handle authentication using the new Clerk JWT system"""
    auth_manager = StreamlitAuthManager()
    
    # Check if user is authenticated
    if not auth_manager.is_authenticated():
        # Render login page
        auth_ui = AuthUI()
        auth_ui.render_login_page()
        st.stop()
    else:
        # Verify session token
        if not auth_manager.verify_session():
            st.error("Session expired. Please login again.")
            st.stop()

def render_blog_generator():
    st.title("🧠 AI Blog Generator")

    topic = st.text_input("Enter your blog topic")
    keywords = st.text_area("Enter keywords (comma-separated)", height=80)
    tone = st.selectbox("Choose tone", ["Professional", "Conversational", "Educational", "Inspirational"])
    
    if st.button("Generate Blog"):
        if not topic:
            st.warning("Please enter a topic first.")
            return

        with st.spinner("Generating blog post... ✨"):
            payload = {
                "topic": topic,
                "keywords": [k.strip() for k in keywords.split(",") if k.strip()],
                "tone": tone.lower(),
            }
            response = call_api("blogs/generate/", "POST", data=payload)
            if response and response.get("success"):
                st.markdown("### 📝 Generated Blog Post")
                st.write(response["content"])
            else:
                st.error("❌ Failed to generate blog post. Check API logs for details.")

def render_dashboard():
    """Render main dashboard with authentication sidebar"""
    # Initialize authentication components
    auth_manager = StreamlitAuthManager()
    sidebar_auth = SidebarAuth()
    
    # Render authentication section in sidebar
    sidebar_auth.render_auth_section()
    
    st.sidebar.markdown("---")
    st.sidebar.title("Navigation")
    choice = st.sidebar.radio("Go to", ["Blog Generator", "My Posts", "Settings"])

    if choice == "Blog Generator":
        render_blog_generator()
    elif choice == "My Posts":
        response = call_api("Blogs/list/", "GET")
        if response:
            st.subheader("📚 Your Generated Blogs")
            for post in response.get("results", []):
                st.markdown(f"### {post['title']}")
                st.write(post["excerpt"])
                st.write(f"🗓️ {post['created_at']}")
                st.divider()
        else:
            st.warning("No blogs found.")
    elif choice == "Settings":
        st.subheader("⚙️ Settings")
        if st.button("Logout"):
            auth_manager.logout()

# --- Entry Point ---

def main():
    load_custom_css()
    handle_auth()
    render_dashboard()

if __name__ == "__main__":
    main()
