"""
Enhanced UI components for Streamlit features.
Provides reusable components for consistent UI across all features.
"""

import streamlit as st
from typing import Dict, Any, List, Optional, Union
from datetime import datetime


class FeatureUIComponents:
    """Reusable UI components for Streamlit features"""
    
    @staticmethod
    def display_success_message(message: str, details: str = None):
        """Display success message with optional details"""
        st.success(f"✅ {message}")
        if details:
            st.info(f"ℹ️ {details}")
    
    @staticmethod
    def display_error_message(message: str, details: str = None):
        """Display error message with optional details"""
        st.error(f"❌ {message}")
        if details:
            st.warning(f"⚠️ {details}")
    
    @staticmethod
    def display_loading_message(message: str):
        """Display loading message"""
        return st.spinner(f"🔄 {message}")
    
    @staticmethod
    def display_metadata_metrics(data: Dict[str, Any], 
                                metric_configs: List[tuple],
                                columns: int = 3):
        """
        Display metadata metrics in columns.
        
        Args:
            data: Dictionary containing the data
            metric_configs: List of (field_name, display_name) tuples
            columns: Number of columns to use
        """
        if not metric_configs:
            return
        
        cols = st.columns(min(columns, len(metric_configs)))
        
        for i, (field_name, display_name) in enumerate(metric_configs):
            with cols[i % columns]:
                value = data.get(field_name, "N/A")
                st.metric(display_name, value)
    
    @staticmethod
    def display_form_section(title: str, description: str = None):
        """Display a form section with title and optional description"""
        st.markdown(f"### {title}")
        if description:
            st.caption(description)
    
    @staticmethod
    def create_form_columns(num_columns: int = 2):
        """Create form columns"""
        return st.columns(num_columns)
    
    @staticmethod
    def display_submit_buttons(primary_text: str, 
                              secondary_text: str = None,
                              primary_type: str = "primary"):
        """Display submit buttons in a row"""
        col1, col2 = st.columns([1, 1])
        
        with col1:
            submitted = st.form_submit_button(
                primary_text, 
                use_container_width=True,
                type=primary_type
            )
        
        with col2:
            if secondary_text:
                if st.form_submit_button(secondary_text, use_container_width=True):
                    st.rerun()
        
        return submitted
    
    @staticmethod
    def display_content_preview(content: str, 
                              max_length: int = 300,
                              expandable: bool = True):
        """Display content preview with optional expandable full content"""
        if len(content) <= max_length:
            st.markdown(content)
            return
        
        preview = content[:max_length] + "..."
        st.markdown(preview)
        
        if expandable:
            with st.expander("View Full Content"):
                st.markdown(content)
    
    @staticmethod
    def display_sources_list(sources: List[Dict[str, Any]], 
                           title: str = "📚 Sources"):
        """Display a list of sources"""
        if not sources:
            return
        
        st.subheader(title)
        for source in sources:
            title_text = source.get('title', 'Untitled')
            url = source.get('url', source.get('link', '#'))
            source_name = source.get('source', 'Unknown')
            
            st.markdown(f"- [{title_text}]({url})")
            if source_name != 'Unknown':
                st.caption(f"Source: {source_name}")
    
    @staticmethod
    def display_images_grid(image_urls: List[str], 
                          title: str = "🖼️ Images",
                          columns: int = 2):
        """Display images in a grid layout"""
        if not image_urls:
            return
        
        st.subheader(title)
        
        # Create columns for grid layout
        cols = st.columns(min(columns, len(image_urls)))
        
        for i, image_url in enumerate(image_urls):
            with cols[i % columns]:
                st.image(image_url, caption=f"Image {i+1}")
    
    @staticmethod
    def display_status_badge(status: str, 
                          status_config: Dict[str, str] = None):
        """Display a status badge with appropriate styling"""
        if status_config is None:
            status_config = {
                'pending': '🟡 Pending',
                'generating': '🔄 Generating',
                'completed': '✅ Completed',
                'failed': '❌ Failed',
                'success': '✅ Success',
                'error': '❌ Error'
            }
        
        status_display = status_config.get(status.lower(), f"❓ {status}")
        
        if '✅' in status_display:
            st.success(status_display)
        elif '❌' in status_display:
            st.error(status_display)
        elif '🔄' in status_display:
            st.info(status_display)
        elif '🟡' in status_display:
            st.warning(status_display)
        else:
            st.info(status_display)
    
    @staticmethod
    def display_progress_info(current: int, total: int, 
                            message: str = "Processing"):
        """Display progress information"""
        progress = current / total if total > 0 else 0
        st.progress(progress)
        st.caption(f"{message}: {current}/{total}")
    
    @staticmethod
    def display_timestamp(timestamp: Union[str, datetime], 
                         format_str: str = "%Y-%m-%d %H:%M:%S"):
        """Display formatted timestamp"""
        if isinstance(timestamp, str):
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                formatted = dt.strftime(format_str)
            except:
                formatted = timestamp
        elif isinstance(timestamp, datetime):
            formatted = timestamp.strftime(format_str)
        else:
            formatted = str(timestamp)
        
        st.caption(f"📅 {formatted}")
    
    @staticmethod
    def display_keywords(keywords: List[str], 
                        title: str = "🔍 Keywords"):
        """Display keywords as tags"""
        if not keywords:
            return
        
        st.markdown(f"**{title}:**")
        keyword_text = ", ".join(keywords)
        st.info(keyword_text)
    
    @staticmethod
    def display_expandable_section(title: str, 
                                 content: str,
                                 expanded: bool = False):
        """Display expandable section with content"""
        with st.expander(title, expanded=expanded):
            st.markdown(content)
    
    @staticmethod
    def display_action_buttons(actions: List[Dict[str, Any]]):
        """Display action buttons in a row"""
        if not actions:
            return
        
        cols = st.columns(len(actions))
        
        for i, action in enumerate(actions):
            with cols[i]:
                if st.button(
                    action.get('text', 'Action'),
                    key=action.get('key', f'action_{i}'),
                    help=action.get('help', ''),
                    use_container_width=True
                ):
                    if 'callback' in action:
                        action['callback']()
    
    @staticmethod
    def display_data_table(data: List[Dict[str, Any]], 
                         title: str = "Data Table"):
        """Display data in a table format"""
        if not data:
            st.info("No data available")
            return
        
        st.subheader(title)
        
        # Convert to DataFrame for better display
        import pandas as pd
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
    
    @staticmethod
    def display_json_data(data: Dict[str, Any], 
                        title: str = "Raw Data",
                        expandable: bool = True):
        """Display JSON data in a formatted way"""
        if expandable:
            with st.expander(title):
                st.json(data)
        else:
            st.subheader(title)
            st.json(data)
    
    @staticmethod
    def display_code_block(code: str, 
                         language: str = None,
                         title: str = "Code"):
        """Display code block with optional title"""
        if title:
            st.subheader(title)
        st.code(code, language=language)
    
    @staticmethod
    def display_copy_button(content: str, 
                           button_text: str = "📋 Copy",
                           success_message: str = "Copied to clipboard!"):
        """Display copy button for content"""
        if st.button(button_text):
            st.code(content)
            st.success(success_message)
    
    @staticmethod
    def display_filter_options(options: List[str], 
                             default: str = "All",
                             key: str = "filter"):
        """Display filter options"""
        return st.selectbox(
            "Filter:",
            [default] + options,
            key=key
        )
    
    @staticmethod
    def display_refresh_button(text: str = "🔄 Refresh"):
        """Display refresh button"""
        if st.button(text, use_container_width=True):
            st.rerun()
    
    @staticmethod
    def display_empty_state(message: str, 
                          icon: str = "📭",
                          action_text: str = None,
                          action_callback: callable = None):
        """Display empty state with optional action"""
        st.markdown(f"## {icon}")
        st.markdown(f"### {message}")
        
        if action_text and action_callback:
            if st.button(action_text, use_container_width=True):
                action_callback()
    
    @staticmethod
    def display_loading_placeholder(message: str = "Loading..."):
        """Display loading placeholder"""
        with st.spinner(f"🔄 {message}"):
            st.empty()
    
    @staticmethod
    def display_feature_intro(title: str, 
                            description: str,
                            features: List[str] = None):
        """Display feature introduction"""
        st.title(title)
        st.markdown(description)
        
        if features:
            st.markdown("### ✨ Features:")
            for feature in features:
                st.markdown(f"- {feature}")
            st.markdown("---")
    
    @staticmethod
    def display_form_validation_errors(errors: List[str]):
        """Display form validation errors"""
        if errors:
            for error in errors:
                st.error(f"❌ {error}")
    
    @staticmethod
    def display_form_success_message(message: str):
        """Display form success message"""
        st.success(f"✅ {message}")
    
    @staticmethod
    def display_warning_message(message: str, 
                               details: str = None):
        """Display warning message"""
        st.warning(f"⚠️ {message}")
        if details:
            st.caption(details)
    
    @staticmethod
    def display_info_message(message: str, 
                           details: str = None):
        """Display info message"""
        st.info(f"ℹ️ {message}")
        if details:
            st.caption(details)
