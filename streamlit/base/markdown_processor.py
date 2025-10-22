"""
Markdown processing utilities for Streamlit features.
Handles proper rendering of markdown content from various data formats.
"""

import streamlit as st
from typing import Dict, Any, List, Union, Optional


class MarkdownProcessor:
    """Utility class for processing and rendering markdown content"""
    
    @staticmethod
    def display_content(data: Dict[str, Any], content_fields: List[str] = None) -> bool:
        """
        Display content from various data formats with proper markdown rendering.
        
        Args:
            data: Dictionary containing content data
            content_fields: List of field names to check for content (in priority order)
            
        Returns:
            bool: True if content was displayed, False otherwise
        """
        if content_fields is None:
            content_fields = ["raw_content", "content", "sections"]
        
        for field in content_fields:
            if field in data and data[field]:
                content_to_display = MarkdownProcessor._process_content(data[field])
                if content_to_display:
                    st.markdown(content_to_display)
                    return True
        
        # If no content found, show a message
        st.info("No content available to display.")
        return False
    
    @staticmethod
    def _process_content(content: Union[str, List, Dict]) -> str:
        """
        Process content field and return formatted markdown.
        
        Args:
            content: Content in various formats (string, list, dict)
            
        Returns:
            str: Formatted markdown content
        """
        if isinstance(content, list):
            # If content is a list, join it
            return '\n'.join(str(item) for item in content if item)
        elif isinstance(content, str):
            # If content is a string, use it directly
            return content
        elif isinstance(content, dict):
            # If content is a dict, convert to markdown sections
            markdown_parts = []
            for section, text in content.items():
                if text:
                    processed_text = MarkdownProcessor._process_content(text)
                    if processed_text.strip():
                        markdown_parts.append(f"## {section.replace('_', ' ').title()}")
                        markdown_parts.append(processed_text)
                        markdown_parts.append("")
            return '\n'.join(markdown_parts)
        else:
            # Convert other types to string
            return str(content)
    
    @staticmethod
    def _process_sections(sections: Union[List, Dict]) -> str:
        """
        Process sections field and return formatted markdown.
        
        Args:
            sections: Sections in various formats (list, dict)
            
        Returns:
            str: Formatted markdown content
        """
        if isinstance(sections, list):
            markdown_parts = []
            for section in sections:
                if isinstance(section, dict):
                    title = section.get('title', 'Untitled')
                    content = section.get('content', '')
                    
                    if content:
                        processed_content = MarkdownProcessor._process_content(content)
                        if processed_content.strip():
                            markdown_parts.append(f"## {title}")
                            markdown_parts.append(processed_content)
                            markdown_parts.append("")
                elif isinstance(section, str):
                    markdown_parts.append(section)
            return '\n'.join(markdown_parts)
        elif isinstance(sections, dict):
            return MarkdownProcessor._process_content(sections)
        else:
            return str(sections)
    
    @staticmethod
    def display_with_metadata(data: Dict[str, Any], title: str, 
                            metadata_fields: List[tuple] = None,
                            content_fields: List[str] = None) -> bool:
        """
        Display content with metadata in a structured format.
        
        Args:
            data: Dictionary containing content data
            title: Title for the content section
            metadata_fields: List of (field_name, display_name) tuples for metadata
            content_fields: List of field names to check for content
            
        Returns:
            bool: True if content was displayed, False otherwise
        """
        st.subheader(title)
        
        # Display metadata if provided
        if metadata_fields:
            cols = st.columns(len(metadata_fields))
            for i, (field_name, display_name) in enumerate(metadata_fields):
                with cols[i]:
                    st.metric(display_name, data.get(field_name, "N/A"))
        
        # Display content
        return MarkdownProcessor.display_content(data, content_fields)
    
    @staticmethod
    def display_sources(sources: List[Dict[str, Any]], title: str = "📚 Sources") -> None:
        """
        Display sources in a formatted way.
        
        Args:
            sources: List of source dictionaries
            title: Title for the sources section
        """
        if not sources:
            return
        
        st.subheader(title)
        
        # Create a container for better formatting
        with st.container():
            for i, source in enumerate(sources, 1):
                # Handle different possible field names for title
                title_text = source.get('title', source.get('name', source.get('headline', f'Source {i}')))
                
                # Handle different possible field names for URL
                url = source.get('url', source.get('link', source.get('href', '#')))
                
                # Handle source name
                source_name = source.get('source', source.get('publisher', source.get('site_name', 'Unknown')))
                
                # Display the source with better formatting
                if url and url != '#':
                    # Create a clean display with proper spacing
                    st.markdown(f"**{i}.** [{title_text}]({url})")
                    if source_name and source_name != 'Unknown':
                        st.caption(f"   📰 Source: {source_name}")
                    st.markdown("")  # Add spacing between sources
                else:
                    # If no valid URL, just show the title
                    st.markdown(f"**{i}.** {title_text}")
                    if source_name and source_name != 'Unknown':
                        st.caption(f"   📰 Source: {source_name}")
                    st.markdown("")  # Add spacing between sources
    
    @staticmethod
    def display_images(image_urls: List[str], title: str = "🖼️ Generated Images") -> None:
        """
        Display images in a formatted way.
        
        Args:
            image_urls: List of image URLs
            title: Title for the images section
        """
        if image_urls:
            st.subheader(title)
            for i, image_url in enumerate(image_urls):
                st.image(image_url, caption=f"Image {i+1}")
    
    @staticmethod
    def create_content_preview(content: str, max_length: int = 300) -> str:
        """
        Create a preview of content with specified maximum length.
        
        Args:
            content: Content to preview
            max_length: Maximum length of preview
            
        Returns:
            str: Content preview
        """
        if len(content) <= max_length:
            return content
        return content[:max_length] + "..."
    
    @staticmethod
    def display_content_preview(data: Dict[str, Any], 
                              content_field: str = "content",
                              max_length: int = 300) -> None:
        """
        Display a preview of content with expandable full content.
        
        Args:
            data: Dictionary containing content data
            content_field: Field name containing the content
            max_length: Maximum length of preview
        """
        if content_field in data and data[content_field]:
            content = MarkdownProcessor._process_content(data[content_field])
            if content:
                preview = MarkdownProcessor.create_content_preview(content, max_length)
                st.text(preview)
                
                if len(content) > max_length:
                    with st.expander("View Full Content"):
                        st.markdown(content)
