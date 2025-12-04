"""
Markdown Parser Module
Parses markdown content into structured elements for PDF generation
"""

import re
from typing import Dict, Any, List


class MarkdownParser:
    """Parses markdown content into structured elements"""
    
    @staticmethod
    def parse(content: str) -> List[Dict[str, Any]]:
        """Parse markdown content into structured elements"""
        elements = []
        lines = content.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            if not line:
                i += 1
                continue
            
            # Handle headings
            if line.startswith('#'):
                level = len(line) - len(line.lstrip('#'))
                heading_text = line.lstrip('#').strip()
                elements.append({
                    'type': 'heading',
                    'level': level,
                    'content': heading_text
                })
            
            # Handle images
            elif line.startswith('![') and '](' in line:
                match = re.match(r'!\[([^\]]*)\]\(([^)]+)\)', line)
                if match:
                    alt_text = match.group(1)
                    image_url = match.group(2)
                    elements.append({
                        'type': 'image',
                        'alt_text': alt_text,
                        'url': image_url
                    })
            
            # Handle lists
            elif re.match(r'^\d+\.\s', line):
                # Ordered list
                list_items = [line]
                i += 1
                while i < len(lines) and (lines[i].strip().startswith(('  ', '\t')) or re.match(r'^\d+\.\s', lines[i].strip())):
                    if lines[i].strip():
                        list_items.append(lines[i].strip())
                    i += 1
                i -= 1  # Back up one since we went too far
                
                elements.append({
                    'type': 'ordered_list',
                    'items': list_items
                })
            
            elif line.startswith('- ') or line.startswith('* '):
                # Unordered list
                list_items = [line]
                i += 1
                while i < len(lines) and (lines[i].strip().startswith(('  ', '\t')) or lines[i].strip().startswith(('- ', '* '))):
                    if lines[i].strip():
                        list_items.append(lines[i].strip())
                    i += 1
                i -= 1  # Back up one since we went too far
                
                elements.append({
                    'type': 'unordered_list',
                    'items': list_items
                })
            
            # Handle paragraphs
            else:
                paragraph_lines = [line]
                i += 1
                while i < len(lines) and lines[i].strip() and not lines[i].startswith('#') and not lines[i].startswith('![') and not re.match(r'^\d+\.\s', lines[i].strip()) and not lines[i].strip().startswith(('- ', '* ')):
                    paragraph_lines.append(lines[i].strip())
                    i += 1
                i -= 1  # Back up one since we went too far
                
                elements.append({
                    'type': 'paragraph',
                    'content': ' '.join(paragraph_lines)
                })
            
            i += 1
        
        return elements

