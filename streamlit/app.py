#!/usr/bin/env python3
"""
Main Streamlit application entry point for AI Blog Generator.
Uses Django API calls for all backend functionality.
"""

import streamlit as st
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the new API-based base
from base.streamlit_base import StreamlitApp

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
    """Load custom CSS for styling"""
    css_path = Path(__file__).parent / "base" / "style.css"
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)

# --- Entry Point ---

def main():
    """Main application entry point"""
    # Load custom CSS
    load_custom_css()
    
    # Initialize and run the main application
    # Authentication is handled within StreamlitApp
    app = StreamlitApp()
    app.run()

if __name__ == "__main__":
    main()
