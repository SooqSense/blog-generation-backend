import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse
import logging
from typing import Dict, List, Optional, Tuple
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class BlogAnalyzer:
    """
    Analyzes blog content from URLs to extract structure, style, and patterns
    for replicating similar blog posts without plagiarism
    """
    
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.3)
    
    def scrape_blog_content(self, url: str) -> Dict[str, str]:
        """
        Scrape blog content from a given URL
        
        Args:
            url (str): The URL of the blog to analyze
            
        Returns:
            Dict containing scraped content and metadata
        """
        try:
            # Validate URL
            parsed_url = urlparse(url)
            if not parsed_url.scheme or not parsed_url.netloc:
                raise ValueError("Invalid URL provided")
            
            # Set headers to mimic a real browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            }
            
            # Make request with timeout
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Parse HTML content
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract title
            title = ""
            title_tag = soup.find('title')
            if title_tag:
                title = title_tag.get_text().strip()
            
            # Try to find the main content area
            content = self._extract_main_content(soup)
            
            # Extract meta description
            meta_description = ""
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc:
                meta_description = meta_desc.get('content', '').strip()
            
            # Extract headings structure
            headings = self._extract_headings(soup)
            
            # Clean and format content
            cleaned_content = self._clean_content(content)
            
            return {
                'url': url,
                'title': title,
                'meta_description': meta_description,
                'content': cleaned_content,
                'headings': headings,
                'word_count': len(cleaned_content.split()),
                'status': 'success'
            }
            
        except requests.RequestException as e:
            logger.error(f"Error fetching URL {url}: {str(e)}")
            return {
                'url': url,
                'error': f"Failed to fetch content: {str(e)}",
                'status': 'error'
            }
        except Exception as e:
            logger.error(f"Error analyzing blog from {url}: {str(e)}")
            return {
                'url': url,
                'error': f"Analysis failed: {str(e)}",
                'status': 'error'
            }
    
    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """Extract the main content from the webpage"""
        # Common content selectors (in order of preference)
        content_selectors = [
            'article',
            '[role="main"]',
            '.post-content',
            '.entry-content',
            '.content',
            '.post-body',
            '.article-content',
            '.blog-content',
            'main',
            '.main-content'
        ]
        
        content = ""
        
        # Try each selector
        for selector in content_selectors:
            elements = soup.select(selector)
            if elements:
                # Get the largest element (most likely to be main content)
                main_element = max(elements, key=lambda x: len(x.get_text()))
                content = main_element.get_text()
                break
        
        # Fallback: get body content if no specific content area found
        if not content:
            body = soup.find('body')
            if body:
                content = body.get_text()
        
        return content
    
    def _extract_headings(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract heading structure from the webpage"""
        headings = []
        
        for level in range(1, 7):  # h1 to h6
            heading_tags = soup.find_all(f'h{level}')
            for tag in heading_tags:
                headings.append({
                    'level': level,
                    'text': tag.get_text().strip(),
                    'tag': f'h{level}'
                })
        
        return headings
    
    def _clean_content(self, content: str) -> str:
        """Clean and format the extracted content"""
        # Remove extra whitespace and newlines
        content = re.sub(r'\s+', ' ', content)
        
        # Remove common navigation and footer text
        unwanted_patterns = [
            r'Home\s+About\s+Contact',
            r'Privacy Policy',
            r'Terms of Service',
            r'Copyright.*\d{4}',
            r'All rights reserved',
            r'Subscribe to.*newsletter',
            r'Follow us on',
            r'Share this.*',
            r'Related Posts?',
            r'Comments?.*'
        ]
        
        for pattern in unwanted_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE)
        
        return content.strip()
    
    def analyze_blog_structure(self, scraped_data: Dict) -> Dict[str, any]:
        """
        Analyze the blog structure and extract patterns using AI
        
        Args:
            scraped_data (Dict): The scraped blog data
            
        Returns:
            Dict containing analysis results and style patterns
        """
        if scraped_data.get('status') != 'success':
            return {
                'error': scraped_data.get('error', 'Failed to analyze blog structure'),
                'status': 'error'
            }
        
        try:
            # Prepare content for analysis
            content = scraped_data.get('content', '')
            headings = scraped_data.get('headings', [])
            title = scraped_data.get('title', '')
            
            # Create analysis prompt
            analysis_prompt = f"""
Analyze this blog post and extract its structural and stylistic patterns:

Title: {title}
Content Length: {len(content.split())} words

Headings Structure:
{self._format_headings_for_analysis(headings)}

Content Sample (first 1000 characters):
{content[:1000]}...

Please analyze and provide:
1. Writing tone and style (professional, casual, conversational, etc.)
2. Content structure pattern (introduction style, main sections, conclusion approach)
3. Heading hierarchy and organization
4. Paragraph length and style
5. Use of lists, examples, or special formatting
6. Call-to-action patterns
7. Overall content flow and organization

Provide your analysis in a structured format that can be used to replicate the style without copying content.
"""

            # Get AI analysis
            response = self.llm.invoke(analysis_prompt)
            analysis_text = response.content
            
            # Extract specific patterns
            patterns = self._extract_patterns_from_analysis(analysis_text, scraped_data)
            
            return {
                'url': scraped_data['url'],
                'analysis': analysis_text,
                'patterns': patterns,
                'original_structure': {
                    'title': title,
                    'headings': headings,
                    'word_count': scraped_data.get('word_count', 0),
                    'meta_description': scraped_data.get('meta_description', '')
                },
                'status': 'success'
            }
            
        except Exception as e:
            logger.error(f"Error in blog structure analysis: {str(e)}")
            return {
                'error': f"Analysis failed: {str(e)}",
                'status': 'error'
            }
    
    def _format_headings_for_analysis(self, headings: List[Dict]) -> str:
        """Format headings for AI analysis"""
        if not headings:
            return "No clear heading structure found"
        
        formatted = []
        for heading in headings:
            level_indicator = "#" * heading['level']
            formatted.append(f"{level_indicator} {heading['text']}")
        
        return "\n".join(formatted)
    
    def _extract_patterns_from_analysis(self, analysis_text: str, scraped_data: Dict) -> Dict:
        """Extract actionable patterns from the AI analysis"""
        patterns = {
            'tone': 'professional',  # default
            'structure_type': 'standard',
            'avg_paragraph_length': 'medium',
            'uses_lists': False,
            'uses_examples': False,
            'has_introduction': True,
            'has_conclusion': True,
            'has_cta': False,
            'heading_style': 'descriptive'
        }
        
        # Simple pattern extraction based on analysis text
        analysis_lower = analysis_text.lower()
        
        # Detect tone
        if any(word in analysis_lower for word in ['casual', 'informal', 'conversational']):
            patterns['tone'] = 'casual'
        elif any(word in analysis_lower for word in ['creative', 'engaging', 'storytelling']):
            patterns['tone'] = 'creative'
        elif any(word in analysis_lower for word in ['informative', 'educational']):
            patterns['tone'] = 'informative'
        
        # Detect structure elements
        if any(phrase in analysis_lower for phrase in ['bullet points', 'numbered list', 'list format']):
            patterns['uses_lists'] = True
        
        if any(phrase in analysis_lower for phrase in ['examples', 'case studies', 'illustrations']):
            patterns['uses_examples'] = True
        
        if any(phrase in analysis_lower for phrase in ['call to action', 'cta', 'subscribe', 'contact']):
            patterns['has_cta'] = True
        
        # Analyze heading count and structure
        headings = scraped_data.get('headings', [])
        if len(headings) > 5:
            patterns['structure_type'] = 'detailed'
        elif len(headings) < 3:
            patterns['structure_type'] = 'simple'
        
        return patterns
    
    def generate_style_instructions(self, analysis_result: Dict) -> str:
        """
        Generate instructions for replicating the blog style
        
        Args:
            analysis_result (Dict): The blog analysis result
            
        Returns:
            str: Detailed instructions for style replication
        """
        if analysis_result.get('status') != 'success':
            return "Unable to generate style instructions due to analysis failure."
        
        patterns = analysis_result.get('patterns', {})
        original_structure = analysis_result.get('original_structure', {})
        
        instructions = []
        
        # Tone instructions
        tone = patterns.get('tone', 'professional')
        instructions.append(f"- Use a {tone} tone throughout the blog post")
        
        # Structure instructions
        structure_type = patterns.get('structure_type', 'standard')
        if structure_type == 'detailed':
            instructions.append("- Create a detailed structure with multiple subsections")
        elif structure_type == 'simple':
            instructions.append("- Keep the structure simple with fewer main sections")
        
        # Content formatting
        if patterns.get('uses_lists'):
            instructions.append("- Include bullet points or numbered lists where appropriate")
        
        if patterns.get('uses_examples'):
            instructions.append("- Provide concrete examples and illustrations")
        
        if patterns.get('has_cta'):
            instructions.append("- Include a clear call-to-action section")
        
        # Length guidance
        word_count = original_structure.get('word_count', 0)
        if word_count > 0:
            instructions.append(f"- Target approximately {word_count} words (±200 words)")
        
        # Heading structure
        headings = original_structure.get('headings', [])
        if headings:
            instructions.append(f"- Use {len(headings)} main sections similar to the reference structure")
        
        return "\n".join(instructions)

def analyze_sample_blog(url: str) -> Tuple[Optional[Dict], Optional[str]]:
    """
    Main function to analyze a sample blog and return style instructions
    
    Args:
        url (str): URL of the blog to analyze
        
    Returns:
        Tuple of (analysis_result, style_instructions)
    """
    try:
        analyzer = BlogAnalyzer()
        
        # Scrape the blog content
        scraped_data = analyzer.scrape_blog_content(url)
        
        if scraped_data.get('status') != 'success':
            return None, f"Failed to scrape blog: {scraped_data.get('error', 'Unknown error')}"
        
        # Analyze the structure
        analysis_result = analyzer.analyze_blog_structure(scraped_data)
        
        if analysis_result.get('status') != 'success':
            return None, f"Failed to analyze blog: {analysis_result.get('error', 'Unknown error')}"
        
        # Generate style instructions
        style_instructions = analyzer.generate_style_instructions(analysis_result)
        
        return analysis_result, style_instructions
        
    except Exception as e:
        logger.error(f"Error in analyze_sample_blog: {str(e)}")
        return None, f"Analysis failed: {str(e)}" 