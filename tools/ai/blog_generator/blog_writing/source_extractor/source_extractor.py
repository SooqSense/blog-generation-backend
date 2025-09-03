import re
from urllib.parse import urlparse


class SourceExtractor:
    """Handles extraction of sources and image prompts from CrewAI results with LLM SEO optimization"""
    
    def __init__(self, generate_image_prompts=True, max_image_prompts=5):
        self.generate_image_prompts = generate_image_prompts
        self.max_image_prompts = max_image_prompts
        self.source_quality_indicators = [
            'study', 'research', 'report', 'analysis', 'survey', 'data',
            'statistics', 'findings', 'results', 'methodology'
        ]
    
    def extract_sources_from_result(self, crew_result):
        """
        Extract sources from the crew result
        
        Args:
            crew_result: The result from CrewAI execution
            
        Returns:
            list: List of extracted sources
        """
        sources = []
        try:
            # Get the research task result (first task)
            if hasattr(crew_result, 'tasks_output') and crew_result.tasks_output:
                research_result = crew_result.tasks_output[0]
                if hasattr(research_result, 'raw'):
                    research_content = research_result.raw
                elif hasattr(research_result, 'result'):
                    research_content = research_result.result
                else:
                    research_content = str(research_result)
                
                # Parse sources from research content
                sources = self._parse_sources_from_content(research_content)
                
        except Exception as e:
            print(f"Error extracting sources: {str(e)}")
            
        return sources
    
    def _parse_sources_from_content(self, content):
        """
        Parse sources from research content with enhanced LLM SEO metadata
        
        Args:
            content (str): The research content containing sources
            
        Returns:
            list: List of enhanced source dictionaries with LLM SEO metadata
        """
        sources = []
        
        # Look for URLs in the content
        url_pattern = r'https?://[^\s\)>\]]+[^\s\.\)>\]]*'
        urls = re.findall(url_pattern, content)
        
        # Clean and deduplicate URLs
        seen_urls = set()
        for url in urls:
            # Clean URL
            url = url.strip('.,;:')
            if url not in seen_urls and len(url) > 10:
                source_data = self._analyze_source_quality(url, content)
                sources.append(source_data)
                seen_urls.add(url)
        
        # Sort by reliability score and return top sources
        sources.sort(key=lambda x: x.get('reliability_score', 0), reverse=True)
        return sources[:15]  # Increased limit for LLM SEO
    
    def _analyze_source_quality(self, url, content):
        """
        Analyze source quality and reliability for LLM SEO optimization
        
        Args:
            url (str): The source URL
            content (str): The research content containing the URL
            
        Returns:
            dict: Enhanced source data with reliability metrics
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.replace('www.', '').lower()
            
            # Base source data
            source_data = {
                'url': url,
                'title': self._extract_domain_name(url),
                'type': 'research_source',
                'domain': domain,
                'reliability_score': 0
            }
            
            # Authority scoring based on domain
            authority_domains = {
                'gov': 10, 'edu': 9, 'org': 7,
                'reuters.com': 9, 'bbc.com': 9, 'cnn.com': 8,
                'nytimes.com': 8, 'wsj.com': 8, 'forbes.com': 7,
                'harvard.edu': 10, 'mit.edu': 10, 'stanford.edu': 10,
                'nature.com': 10, 'science.org': 10, 'pubmed.ncbi.nlm.nih.gov': 10,
                'who.int': 10, 'cdc.gov': 10, 'fda.gov': 10,
                'statista.com': 8, 'pewresearch.org': 9, 'gallup.com': 8
            }
            
            # Check for authority domain patterns
            for auth_domain, score in authority_domains.items():
                if auth_domain in domain:
                    source_data['reliability_score'] += score
                    source_data['authority_type'] = self._get_authority_type(auth_domain)
                    break
            
            # Content context scoring
            context_score = self._analyze_source_context(url, content)
            source_data['reliability_score'] += context_score
            
            # Extract source description from context
            source_data['description'] = self._extract_source_description(url, content)
            
            # Add publication indicators
            source_data['quality_indicators'] = self._identify_quality_indicators(content, url)
            
            # Date extraction if available in content
            source_data['publication_date'] = self._extract_publication_date(content, url)
            
            return source_data
            
        except Exception as e:
            print(f"Error analyzing source quality for {url}: {str(e)}")
            return {
                'url': url,
                'title': self._extract_domain_name(url),
                'type': 'research_source',
                'reliability_score': 1
            }
    
    def _get_authority_type(self, domain):
        """Get the type of authority based on domain"""
        if '.gov' in domain or domain in ['cdc.gov', 'fda.gov', 'who.int']:
            return 'Government/Official'
        elif '.edu' in domain or domain in ['harvard.edu', 'mit.edu', 'stanford.edu']:
            return 'Academic/Educational'
        elif domain in ['nature.com', 'science.org', 'pubmed.ncbi.nlm.nih.gov']:
            return 'Scientific Journal'
        elif domain in ['reuters.com', 'bbc.com', 'nytimes.com', 'wsj.com']:
            return 'Established Media'
        elif domain in ['statista.com', 'pewresearch.org', 'gallup.com']:
            return 'Research/Analytics'
        else:
            return 'General Source'
    
    def _analyze_source_context(self, url, content):
        """Analyze how the source is referenced in content for quality scoring"""
        score = 0
        url_context = self._extract_url_context(url, content)
        
        # Check for quality indicators around the URL
        for indicator in self.source_quality_indicators:
            if indicator in url_context.lower():
                score += 1
        
        # Check for specific data mentions
        if any(word in url_context.lower() for word in ['according to', 'study shows', 'research indicates', 'data from']):
            score += 2
        
        # Check for numerical data near the URL
        if re.search(r'\d+%|\d+\.\d+%|\$\d+|\d+ million|\d+ billion', url_context):
            score += 2
            
        return min(score, 5)  # Cap context score at 5
    
    def _extract_url_context(self, url, content):
        """Extract text context around the URL mention"""
        try:
            url_index = content.find(url)
            if url_index == -1:
                return ""
            
            # Extract 200 characters before and after the URL
            start = max(0, url_index - 200)
            end = min(len(content), url_index + len(url) + 200)
            return content[start:end]
        except:
            return ""
    
    def _extract_source_description(self, url, content):
        """Extract a description of what the source provides"""
        context = self._extract_url_context(url, content)
        
        # Look for descriptive phrases near the URL
        description_patterns = [
            r'according to ([^,\.]+)',
            r'data from ([^,\.]+)',
            r'study by ([^,\.]+)',
            r'research from ([^,\.]+)',
            r'report by ([^,\.]+)'
        ]
        
        for pattern in description_patterns:
            match = re.search(pattern, context, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        # Fallback to domain-based description
        domain = self._extract_domain_name(url)
        return f"Research data and analysis from {domain}"
    
    def _identify_quality_indicators(self, content, url):
        """Identify quality indicators for the source"""
        context = self._extract_url_context(url, content)
        indicators = []
        
        if any(word in context.lower() for word in ['peer-reviewed', 'peer reviewed']):
            indicators.append('Peer-reviewed')
        if any(word in context.lower() for word in ['study', 'research']):
            indicators.append('Research-based')
        if any(word in context.lower() for word in ['statistics', 'statistical', 'data']):
            indicators.append('Statistical data')
        if any(word in context.lower() for word in ['survey', 'poll']):
            indicators.append('Survey data')
        if any(word in context.lower() for word in ['meta-analysis', 'systematic review']):
            indicators.append('Meta-analysis')
            
        return indicators
    
    def _extract_publication_date(self, content, url):
        """Try to extract publication date from content context"""
        context = self._extract_url_context(url, content)
        
        # Look for date patterns
        date_patterns = [
            r'(\d{4})', r'(\w+ \d{1,2}, \d{4})', 
            r'(\d{1,2}/\d{1,2}/\d{4})', r'(\d{4}-\d{2}-\d{2})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, context)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_domain_name(self, url):
        """Extract a clean domain name from URL for title"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.replace('www.', '')
            return domain.title()
        except:
            return "External Source"
    
    def extract_image_prompts(self, crew_result):
        """
        Extract image prompts from the crew result
        
        Args:
            crew_result: The result from CrewAI execution
            
        Returns:
            list: List of extracted image prompts
        """
        if not self.generate_image_prompts:
            return []
        
        try:
            # Get the last task result which should be the image prompt generation
            if hasattr(crew_result, 'tasks_output') and crew_result.tasks_output:
                # Get the last task output (image prompt generation)
                last_task_output = crew_result.tasks_output[-1]
                if hasattr(last_task_output, 'raw'):
                    prompt_content = last_task_output.raw
                elif hasattr(last_task_output, 'result'):
                    prompt_content = last_task_output.result
                else:
                    prompt_content = str(last_task_output)
                
                # Debug logging
                print(f"DEBUG: Raw image prompt content length: {len(prompt_content)}")
                print(f"DEBUG: First 200 chars of prompt content: {prompt_content[:200]}...")
                
                # Parse the prompts from the content
                prompts = self._parse_prompts_from_content(prompt_content)
                
                print(f"DEBUG: Parsed {len(prompts)} image prompts")
                for i, prompt in enumerate(prompts[:3]):  # Show first 3 for debugging
                    print(f"DEBUG: Prompt {i+1} length: {len(prompt)}, content: {prompt[:100]}...")
                
                return prompts[:self.max_image_prompts]  # Ensure we don't exceed the limit
            
            return []
        except Exception as e:
            print(f"Error extracting image prompts: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
    
    def _parse_prompts_from_content(self, content):
        """
        Parse individual prompts from the generated content
        
        Args:
            content (str): The raw content containing prompts
            
        Returns:
            list: List of individual prompts
        """
        prompts = []
        
        # Clean the content first
        content = content.strip()
        
        # Try different parsing strategies
        
        # Strategy 1: Look for numbered prompts (1., 2., 3., etc.)
        numbered_pattern = r'(\d+\.)\s*(.+?)(?=\d+\.|$)'
        numbered_matches = re.findall(numbered_pattern, content, re.DOTALL)
        
        print(f"DEBUG: Found {len(numbered_matches)} numbered matches")
        
        if numbered_matches:
            for i, (number, prompt_text) in enumerate(numbered_matches):
                print(f"DEBUG: Processing numbered match {i+1}: {prompt_text[:100]}...")
                cleaned_prompt = self._clean_prompt_text(prompt_text.strip())
                print(f"DEBUG: Cleaned prompt length: {len(cleaned_prompt)}")
                if len(cleaned_prompt) > 30:  # Reduced minimum threshold
                    prompts.append(cleaned_prompt)
                    print(f"DEBUG: Added prompt {len(prompts)}")
                else:
                    print(f"DEBUG: Rejected prompt due to length: {len(cleaned_prompt)}")
        
        # Strategy 2: If numbered parsing failed, try line-by-line parsing
        if not prompts:
            lines = content.split('\n')
            current_prompt = ""
            
            for line in lines:
                line = line.strip()
                
                # Skip headers, empty lines, and metadata
                if (not line or 
                    line.startswith('#') or 
                    line.startswith('**') or
                    line.startswith('•') or
                    line.lower().startswith(('note:', 'example:', 'output:', 'format:')) or
                    len(line) < 10):
                    
                    # If we have accumulated a prompt, save it
                    if current_prompt.strip() and len(current_prompt.strip()) > 50:
                        cleaned_prompt = self._clean_prompt_text(current_prompt.strip())
                        if cleaned_prompt:
                            prompts.append(cleaned_prompt)
                        current_prompt = ""
                    continue
                
                # Check if this line starts a new numbered prompt
                if re.match(r'^\d+\.', line):
                    # Save previous prompt if exists
                    if current_prompt.strip() and len(current_prompt.strip()) > 50:
                        cleaned_prompt = self._clean_prompt_text(current_prompt.strip())
                        if cleaned_prompt:
                            prompts.append(cleaned_prompt)
                    
                    # Start new prompt (remove the number)
                    current_prompt = re.sub(r'^\d+\.\s*', '', line)
                else:
                    # Continue building current prompt
                    if current_prompt:
                        current_prompt += " " + line
                    else:
                        current_prompt = line
            
            # Add the last prompt if exists
            if current_prompt.strip() and len(current_prompt.strip()) > 50:
                cleaned_prompt = self._clean_prompt_text(current_prompt.strip())
                if cleaned_prompt:
                    prompts.append(cleaned_prompt)
        
        # Strategy 3: If still no prompts, try to extract meaningful content blocks
        if not prompts:
            print("DEBUG: Strategy 3 - Trying content blocks")
            # Split by double newlines and filter for substantial content
            blocks = content.split('\n\n')
            for i, block in enumerate(blocks):
                block = block.strip()
                print(f"DEBUG: Block {i}: {len(block)} chars, starts with: {block[:50]}...")
                if (len(block) > 50 and 
                    not block.startswith('#') and 
                    not block.lower().startswith(('requirements:', 'output:', 'format:', 'note:'))):
                    
                    cleaned_prompt = self._clean_prompt_text(block)
                    if cleaned_prompt:
                        prompts.append(cleaned_prompt)
                        print(f"DEBUG: Added block as prompt")
        
        # Strategy 4: If we still have no prompts but have substantial content, use the whole content
        if not prompts and len(content.strip()) > 100:
            print("DEBUG: Strategy 4 - Using entire content as single prompt")
            cleaned_prompt = self._clean_prompt_text(content.strip())
            if cleaned_prompt:
                prompts.append(cleaned_prompt)
                print("DEBUG: Added entire content as single prompt")
        
        # Limit to max_image_prompts and ensure quality
        final_prompts = []
        for prompt in prompts[:self.max_image_prompts]:
            if len(prompt) >= 30 and len(prompt) <= 800:  # Adjusted length for image prompts
                final_prompts.append(prompt)
                print(f"DEBUG: Final prompt added: {prompt[:100]}...")
        
        print(f"DEBUG: Returning {len(final_prompts)} final prompts")
        return final_prompts
    
    def _clean_prompt_text(self, text):
        """
        Clean and format prompt text
        
        Args:
            text (str): Raw prompt text
            
        Returns:
            str: Cleaned prompt text or empty string if not a valid prompt
        """
        if not text:
            print("DEBUG: Empty text provided to _clean_prompt_text")
            return ""
        
        original_text = text
        print(f"DEBUG: Cleaning prompt text of length {len(text)}: {text[:100]}...")
        
        # Remove markdown formatting
        text = text.replace('**', '').replace('*', '').replace('_', '')
        
        # Remove quotes if they wrap the entire text
        if text.startswith('"') and text.endswith('"'):
            text = text[1:-1]
        
        # Remove leading numbers and dots (1., 2., etc.)
        text = re.sub(r'^\d+\.\s*', '', text)
        
        # Remove common prefixes
        prefixes_to_remove = [
            'prompt:', 'image prompt:', 'generate:', 'create:', 
            'image:', 'description:', 'visual:', 'picture:'
        ]
        
        text_lower = text.lower()
        for prefix in prefixes_to_remove:
            if text_lower.startswith(prefix):
                text = text[len(prefix):].strip()
                break
        
        # Clean up whitespace
        text = ' '.join(text.split())
        
        # Check if this is likely a blog title or header rather than an image prompt
        title_indicators = [
            text.startswith('#'),  # Markdown header
            len(text.split()) < 8,  # Very short (likely a title)
            text.isupper(),  # All caps (likely a header)
            any(phrase in text.lower() for phrase in [
                'breaking news', 'analysis:', 'comparison:', 'vs', 'versus',
                'report:', 'study:', 'complete guide', 'ultimate guide'
            ]) and len(text.split()) < 12
        ]
        
        if any(title_indicators):
            print(f"DEBUG: Rejected as title/header: {text[:50]}...")
            return ""
        
        # Ensure it looks like an image prompt (contains visual descriptors)
        visual_keywords = [
            'image', 'photo', 'illustration', 'design', 'visual', 'graphic',
            'create', 'show', 'display', 'featuring', 'with', 'background',
            'style', 'color', 'lighting', 'composition', 'professional',
            'scene', 'setting', 'workspace', 'environment', 'shot'
        ]
        
        has_visual_keywords = any(keyword in text.lower() for keyword in visual_keywords)
        
        # Additional visual context words
        descriptive_words = [
            'bright', 'dark', 'clean', 'modern', 'sleek', 'futuristic',
            'detailed', 'high-resolution', 'dramatic', 'soft', 'natural',
            'corporate', 'business', 'technical', 'artistic'
        ]
        
        has_descriptive_words = any(word in text.lower() for word in descriptive_words)
        
        if not has_visual_keywords and not has_descriptive_words:
            # If it doesn't look like an image prompt and is substantial content, enhance it
            if len(text) > 20 and len(text) < 200:
                text = f"Create a professional, high-quality image showing {text}, with clean composition, modern style, and appropriate lighting"
            else:
                print(f"DEBUG: Rejected as non-visual content: {text[:50]}...")
                return ""
        
        # Final validation - should be substantial but not too long
        # Increased max length to accommodate detailed image prompts
        if len(text) < 30 or len(text) > 800:
            print(f"DEBUG: Rejected due to length ({len(text)}): {text[:50]}...")
            return ""
        
        return text.strip()
