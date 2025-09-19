#!/usr/bin/env python3
"""
Main Streamlit application entry point for AI Blog Generator
"""

import streamlit as st
import sys
import os
from pathlib import Path

# IMPORTANT: set_page_config MUST be the first Streamlit command
st.set_page_config(
    page_title="AI Blog Generator",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': "AI Blog Generator - Professional content creation platform"
    }
)

# Configure Python paths for robust module importing
def setup_python_paths():
    """Setup Python paths to ensure proper module importing"""
    current_file = Path(__file__).resolve()
    
    # Get directories
    streamlit_dir = current_file.parent  # /streamlit/
    project_root = streamlit_dir.parent  # /blog-generation-backend/
    
    # Add paths to sys.path if not already present
    paths_to_add = [
        str(project_root),      # For importing management_app, tools, etc.
        str(streamlit_dir),     # For importing streamlit modules directly
    ]
    
    for path in paths_to_add:
        if path not in sys.path:
            sys.path.insert(0, path)
    
    # Set environment variables
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'management_app.config.settings')
    os.environ.setdefault('PYTHONPATH', str(project_root))
    
    # Debug information
    print(f"🔧 Python Path Setup:")
    print(f"   Streamlit Dir: {streamlit_dir}")
    print(f"   Project Root: {project_root}")
    print(f"   Current Dir: {os.getcwd()}")

# Setup paths
setup_python_paths()

# Import the main app with multiple fallback strategies
def import_streamlit_components():
    """Import Streamlit components with fallback strategies"""
    import_strategies = [
        # Strategy 1: Direct import from streamlit directory (when running from project root)
        lambda: __import__('streamlit.base.streamlit_base', fromlist=['StreamlitApp', 'load_custom_css']),
        # Strategy 2: Relative import (when running from streamlit directory)  
        lambda: __import__('base.streamlit_base', fromlist=['StreamlitApp', 'load_custom_css']),
        # Strategy 3: Try importing as if we're in the streamlit directory
        lambda: (lambda m=__import__('base.streamlit_base', fromlist=['StreamlitApp', 'load_custom_css']): m)(),
        # Strategy 4: Absolute path import fallback
        lambda: __import__(f'{Path(__file__).parent.name}.base.streamlit_base', fromlist=['StreamlitApp', 'load_custom_css']),
    ]
    
    for i, strategy in enumerate(import_strategies, 1):
        try:
            module = strategy()
            StreamlitApp = getattr(module, 'StreamlitApp')
            load_custom_css = getattr(module, 'load_custom_css')
            print(f"✅ Import Strategy {i} successful")
            return StreamlitApp, load_custom_css
        except (ImportError, AttributeError) as e:
            print(f"❌ Import Strategy {i} failed: {e}")
            continue
    
    # If all strategies fail, show error
    st.error("🚫 Failed to import required modules")
    st.error("**Troubleshooting Steps:**")
    st.markdown("""
    1. **Check Directory Structure**: Ensure you're running from the correct location
    2. **Verify Python Path**: Make sure the project root is in your Python path
    3. **Install Dependencies**: Run `pip install -r requirements.txt`
    4. **Check File Integrity**: Ensure all frontend files exist and are not corrupted
    """)
    
    with st.expander("🔍 Debug Information"):
        st.write("**Current Working Directory:**", os.getcwd())
        st.write("**File Location:**", str(Path(__file__).resolve()))
        st.write("**Python Path:**", sys.path[:5])  # Show first 5 paths
        st.write("**Environment Variables:**")
        st.json({
            "DJANGO_SETTINGS_MODULE": os.environ.get('DJANGO_SETTINGS_MODULE'),
            "PYTHONPATH": os.environ.get('PYTHONPATH', 'Not set')
        })
    
    st.stop()

# Import components
StreamlitApp, load_custom_css = import_streamlit_components()

def main():
    """Main application entry point"""
    try:
        # Load custom CSS
        load_custom_css()
        
        # Use session state to maintain app instance and avoid recreation
        if 'streamlit_app' not in st.session_state:
            st.session_state.streamlit_app = StreamlitApp()
        
        # Run the app
        st.session_state.streamlit_app.run()
        
    except Exception as e:
        st.error(f"Application Error: {str(e)}")
        st.error("Please check your environment setup and try again.")

if __name__ == "__main__":
    main()
