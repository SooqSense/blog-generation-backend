import os
import re
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from typing import Dict, List, Optional, Tuple
from langchain_openai import ChatOpenAI
from django.conf import settings

logger = logging.getLogger(__name__)

class BlogAnalyzer:
    """
    Analyzes blog content from URLs to extract structure, tone, and writing patterns
    for replicating similar posts without plagiarism.
    """

    def __init__(self):
        """Initialize the OpenAI language model using Django settings"""
        openai_api_key = getattr(settings, "OPENAI_API_KEY", None)
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY not found in Django settings")

        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.3,
            api_key=openai_api_key
        )

    # ---------------------------------------------------------------------- #
    # SCRAPING LOGIC
    # ---------------------------------------------------------------------- #
    def scrape_blog_content(self, url: str) -> Dict[str, str]:
        """
        Scrape blog content from a given URL.
        Returns cleaned text, title, metadata, and heading structure.
        """
        try:
            parsed_url = urlparse(url)
            if not parsed_url.scheme or not parsed_url.netloc:
                raise ValueError("Invalid URL provided")

            headers = {
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/91.0.4472.124 Safari/537.36'
                ),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5'
            }

            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract title and metadata
            title = soup.title.get_text().strip() if soup.title else ""
            meta_description = ""
            meta_tag = soup.find('meta', attrs={'name': 'description'})
            if meta_tag:
                meta_description = meta_tag.get('content', '').strip()

            # Extract content and structure
            content = self._extract_main_content(soup)
            cleaned_content = self._clean_content(content)
            headings = self._extract_headings(soup)

            return {
                'url': url,
                'title': title,
                'meta_description': meta_description,
                'content': cleaned_content,
                'headings': headings,
                'word_count': len(cleaned_content.split()),
                'status': 'success'
            }

        except Exception as e:
            logger.error(f"Error scraping blog {url}: {str(e)}")
            return {'url': url, 'error': str(e), 'status': 'error'}

    # ---------------------------------------------------------------------- #
    # CONTENT EXTRACTION UTILITIES
    # ---------------------------------------------------------------------- #
    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """Extract the main textual content from a webpage"""
        selectors = [
            'article', '[role="main"]', '.post-content', '.entry-content',
            '.content', '.post-body', '.article-content', '.blog-content',
            'main', '.main-content'
        ]
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                largest = max(elements, key=lambda x: len(x.get_text()))
                return largest.get_text()

        body = soup.find('body')
        return body.get_text() if body else ""

    def _extract_headings(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract headings (h1–h6) structure"""
        return [
            {'level': i, 'text': tag.get_text(strip=True), 'tag': f'h{i}'}
            for i in range(1, 7)
            for tag in soup.find_all(f'h{i}')
        ]

    def _clean_content(self, content: str) -> str:
        """Remove noise, whitespace, and repetitive site text"""
        content = re.sub(r'\s+', ' ', content)

        unwanted_patterns = [
            r'Privacy Policy', r'Terms of Service', r'All rights reserved',
            r'Copyright.*\d{4}', r'Subscribe to.*newsletter', r'Follow us on',
            r'Share this.*', r'Related Posts?', r'Comments?.*'
        ]
        for pattern in unwanted_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE)

        return content.strip()

    # ---------------------------------------------------------------------- #
    # ANALYSIS USING LLM
    # ---------------------------------------------------------------------- #
    def analyze_blog_structure(self, scraped_data: Dict) -> Dict[str, any]:
        """
        Analyze a scraped blog using LLM to extract structural and stylistic patterns.
        """
        if scraped_data.get('status') != 'success':
            return {'status': 'error', 'error': scraped_data.get('error', 'Invalid data')}

        try:
            title = scraped_data.get('title', '')
            content = scraped_data.get('content', '')
            headings = scraped_data.get('headings', [])

            analysis_prompt = f"""
Analyze the following blog for structural and stylistic patterns.

Title: {title}
Word Count: {len(content.split())}

Headings:
{self._format_headings(headings)}

Excerpt (first 1000 characters):
{content[:1000]}...

Provide:
1. Writing tone (e.g., professional, conversational)
2. Structure pattern (intro, body, conclusion)
3. Heading organization
4. Paragraph style (length, transitions)
5. Use of lists or examples
6. Presence of CTAs (call-to-actions)
7. General flow and readability characteristics

Output as clear bullet points for reuse.
"""

            response = self.llm.invoke(analysis_prompt)
            analysis_text = response.content.strip()
            patterns = self._extract_patterns(analysis_text, scraped_data)

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
            logger.error(f"Blog analysis failed: {str(e)}")
            return {'status': 'error', 'error': str(e)}

    def _format_headings(self, headings: List[Dict]) -> str:
        """Format headings nicely for AI analysis"""
        if not headings:
            return "No headings found"
        return "\n".join(f"{'#' * h['level']} {h['text']}" for h in headings)

    def _extract_patterns(self, analysis_text: str, scraped_data: Dict) -> Dict:
        """Parse patterns from AI output into structured metadata"""
        text = analysis_text.lower()
        patterns = {
            'tone': 'professional',
            'structure_type': 'standard',
            'uses_lists': any(w in text for w in ['list', 'bullet', 'numbered']),
            'uses_examples': any(w in text for w in ['example', 'case study']),
            'has_cta': any(w in text for w in ['call to action', 'subscribe', 'contact']),
            'heading_style': 'descriptive'
        }

        if 'casual' in text or 'conversational' in text:
            patterns['tone'] = 'casual'
        elif 'creative' in text:
            patterns['tone'] = 'creative'
        elif 'educational' in text:
            patterns['tone'] = 'informative'

        headings_count = len(scraped_data.get('headings', []))
        if headings_count > 6:
            patterns['structure_type'] = 'detailed'
        elif headings_count < 3:
            patterns['structure_type'] = 'simple'

        return patterns

    # ---------------------------------------------------------------------- #
    # STYLE REPLICATION INSTRUCTIONS
    # ---------------------------------------------------------------------- #
    def generate_style_instructions(self, analysis_result: Dict) -> str:
        """Generate clear, actionable style guidelines from analysis."""
        if analysis_result.get('status') != 'success':
            return "Unable to generate style instructions due to analysis failure."

        p = analysis_result['patterns']
        s = analysis_result['original_structure']
        instructions = [f"- Write in a {p.get('tone', 'professional')} tone"]

        if p['structure_type'] == 'detailed':
            instructions.append("- Use multiple structured sections with descriptive subheadings")
        elif p['structure_type'] == 'simple':
            instructions.append("- Keep structure minimal with concise main sections")

        if p.get('uses_lists'):
            instructions.append("- Include bullet points or numbered lists where appropriate")
        if p.get('uses_examples'):
            instructions.append("- Use examples or case studies to illustrate key ideas")
        if p.get('has_cta'):
            instructions.append("- End with a strong call-to-action")

        if s.get('word_count'):
            instructions.append(f"- Aim for around {s['word_count']} words (+/- 200)")

        if len(s.get('headings', [])) > 0:
            instructions.append(f"- Use about {len(s['headings'])} key sections following a similar hierarchy")

        return "\n".join(instructions)


# ---------------------------------------------------------------------- #
# HIGH-LEVEL UTILITY FUNCTION
# ---------------------------------------------------------------------- #
def analyze_sample_blog(url: str) -> Tuple[Optional[Dict], Optional[str]]:
    """
    Convenience function: scrape → analyze → generate style guide
    """
    try:
        analyzer = BlogAnalyzer()
        scraped = analyzer.scrape_blog_content(url)
        if scraped.get('status') != 'success':
            return None, f"Scraping failed: {scraped.get('error')}"

        analyzed = analyzer.analyze_blog_structure(scraped)
        if analyzed.get('status') != 'success':
            return None, f"Analysis failed: {analyzed.get('error')}"

        style_guide = analyzer.generate_style_instructions(analyzed)
        return analyzed, style_guide

    except Exception as e:
        logger.error(f"Fatal error in analyze_sample_blog: {str(e)}")
        return None, f"Analysis failed: {str(e)}"
