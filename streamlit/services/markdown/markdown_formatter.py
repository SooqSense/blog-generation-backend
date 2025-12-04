"""
Markdown Formatter Module
Processes inline markdown formatting for PDF generation
"""

import re


class MarkdownFormatter:
    """Formats markdown text for PDF generation"""
    
    @staticmethod
    def process_inline_formatting(text: str) -> str:
        """Process inline markdown formatting and convert to HTML-like tags for ReportLab"""
        # Process links: [text](url) -> <link href="url">text</link>
        text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<link href="\2">\1</link>', text)
        
        # Process bold: **text** -> <b>text</b>
        text = re.sub(r'\*\*([^*]+?)\*\*', r'<b>\1</b>', text)
        text = re.sub(r'__([^_]+?)__', r'<b>\1</b>', text)
        
        # Process italic: *text* -> <i>text</i>
        text = re.sub(r'(?<!\*)\*([^*]+?)\*(?!\*)', r'<i>\1</i>', text)
        text = re.sub(r'(?<!_)_([^_]+?)_(?!_)', r'<i>\1</i>', text)
        
        return text
    
    @staticmethod
    def clean_list_item(item: str, list_type: str = 'ordered') -> str:
        """Remove list markers from list items"""
        if list_type == 'ordered':
            return re.sub(r'^\d+\.\s*', '', item)
        else:
            return re.sub(r'^[-*]\s*', '', item)

