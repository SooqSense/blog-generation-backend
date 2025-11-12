"""
Styling Module
Contains custom CSS styling for the Streamlit application
"""

import streamlit as st


class CustomCSS:
    """Custom CSS styling for the Streamlit application"""
    
    @staticmethod
    def load_custom_css():
        """Load custom CSS for better UI styling"""
        st.markdown("""
        <style>
        /* Main container styling */
        .main .block-container {
            padding-top: 1rem;
            padding-bottom: 1rem;
            max-width: 1200px;
        }
        
        /* Sidebar styling */
        .css-1d391kg {
            padding-top: 1rem;
        }
        
        /* Feature cards */
        .feature-card {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            padding: 1.5rem;
            border-radius: 10px;
            margin: 1rem 0;
            border-left: 4px solid #667eea;
        }
        
        /* Success/Error messages */
        .stSuccess {
            background-color: #d4edda !important;
            border-color: #c3e6cb !important;
            color: #155724 !important;
        }
        
        .stError {
            background-color: #f8d7da !important;
            border-color: #f5c6cb !important;
            color: #721c24 !important;
        }
        
        .stInfo {
            background-color: #d1ecf1 !important;
            border-color: #bee5eb !important;
            color: #0c5460 !important;
        }
        
        .stWarning {
            background-color: #fff3cd !important;
            border-color: #ffeaa7 !important;
            color: #856404 !important;
        }
        
        /* Button styling */
        .stButton > button {
            border-radius: 8px;
            border: none;
            transition: all 0.3s ease;
            font-weight: 500;
        }
        
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        
        /* Primary button styling */
        .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
        }
        
        .stButton > button[kind="primary"]:hover {
            background: linear-gradient(135deg, #5a67d8 0%, #6b46c1 100%);
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(102, 126, 234, 0.4);
        }
        
        /* Metric styling */
        .metric-container {
            background: white;
            padding: 1.5rem;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            border: 1px solid #e2e8f0;
        }
        
        /* Text area styling */
        .stTextArea > div > div > textarea {
            background-color: #ffffff;
            color: #2d3748;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            font-family: 'Segoe UI', system-ui, sans-serif;
        }
        
        .stTextArea > div > div > textarea:focus {
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        /* Content display containers */
        .content-container {
            background: #ffffff;
            border: 2px solid #0077b5;
            border-left: 6px solid #0077b5;
            border-radius: 12px;
            padding: 24px;
            margin: 15px 0;
            color: #2d3748;
            line-height: 1.6;
            font-size: 16px;
            box-shadow: 0 2px 8px rgba(0, 119, 181, 0.1);
        }
        
        /* Dark theme adjustments */
        @media (prefers-color-scheme: dark) {
            .content-container {
                background: #2d3748;
                color: #e2e8f0;
                border-color: #4299e1;
            }
            
            .stTextArea > div > div > textarea {
                background-color: #2d3748;
                color: #e2e8f0;
            }
        }
        </style>
        """, unsafe_allow_html=True)

