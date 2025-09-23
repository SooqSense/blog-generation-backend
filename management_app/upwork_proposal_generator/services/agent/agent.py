"""
GPT-powered agent for generating Upwork proposals using knowledge base and best practices.
"""

import logging
import re
from typing import Dict, Any, List, Optional
from openai import OpenAI
from django.conf import settings

from management_app.pinecone_integration.service.service import pinecone_service
from ..prompts.prompts import UPWORK_PROPOSAL_SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)


class UpworkProposalAgent:
    """Agent for generating tailored Upwork proposals using GPT-4 and knowledge base."""
    
    def __init__(self):
        self.openai_client = self._initialize_openai()
        self.pinecone_service = pinecone_service
    
    def _initialize_openai(self) -> Optional[OpenAI]:
        """Initialize OpenAI client with API key."""
        try:
            api_key = getattr(settings, 'OPENAI_API_KEY', None)
            if api_key:
                return OpenAI(api_key=api_key)
            else:
                logger.error("❌ OpenAI API key not found in settings")
                return None
        except Exception as e:
            logger.error(f"❌ Failed to initialize OpenAI client: {str(e)}")
            return None
    
    def _search_relevant_projects(self, requirements: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """Search for relevant projects in the knowledge base based on requirements."""
        try:
            if not self.pinecone_service.is_available():
                logger.warning("⚠️ Pinecone service not available, proceeding without project context")
                return []
            
            # Search for relevant projects using the requirements as query
            search_query = f"project experience work {requirements}"
            search_result = self.pinecone_service.search_documents(
                query=search_query,
                user_id=None,  # Search all documents as specified in the service
                top_k=top_k,
                include_metadata=True
            )
            
            if search_result.get('success', False):
                projects = search_result.get('results', [])
                logger.info(f"✅ Found {len(projects)} relevant projects for requirements")
                return projects
            else:
                logger.warning(f"⚠️ Project search failed: {search_result.get('error', 'Unknown error')}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Error searching for relevant projects: {str(e)}")
            return []
    
    def _extract_project_urls(self, content: str) -> List[Dict[str, str]]:
        """Extract actual project URLs with context from content, excluding S3 and storage URLs."""
        # Enhanced pattern to match URLs with better precision
        url_pattern = r'https?://(?![\w-]*\.s3[\w.-]*\.amazonaws\.com|[\w-]*\.s3\.amazonaws\.com)(?:[\w-]+\.)+[\w-]+(?:/[^\s<>"\'\[\]{}|\\^`\n]*)?'
        
        urls = re.findall(url_pattern, content, re.IGNORECASE)
        
        # Filter out common non-project URLs and add more exclusions
        excluded_patterns = [
            r'.*\.s3[\w.-]*\.amazonaws\.com',
            r'.*storage\.googleapis\.com', 
            r'.*blob\.core\.windows\.net',
            r'.*dropbox\.com.*',
            r'.*drive\.google\.com.*',
            r'.*onedrive\.com.*',
            r'.*example\.com.*',
            r'.*localhost.*',
            r'.*127\.0\.0\.1.*',
            r'.*0\.0\.0\.0.*'
        ]
        
        project_urls = []
        for url in urls:
            is_excluded = False
            for pattern in excluded_patterns:
                if re.match(pattern, url, re.IGNORECASE):
                    is_excluded = True
                    break
            
            if not is_excluded:
                # Clean up URL (remove trailing punctuation and normalize)
                clean_url = re.sub(r'[.,:;!?)\]}\s]+$', '', url)
                clean_url = clean_url.lower().strip()
                
                if clean_url and len(clean_url) > 10:  # Must be substantial URL
                    # Validate URL before processing
                    if not self._validate_project_url(clean_url):
                        logger.warning(f"⚠️ Skipping invalid/placeholder URL: {clean_url}")
                        continue
                        
                    # Try to extract project name from URL or surrounding content
                    domain = re.sub(r'https?://', '', clean_url).split('/')[0]
                    project_name = domain.replace('www.', '').replace('.com', '').replace('.ai', '').replace('.io', '')
                    
                    # Look for project name in surrounding context
                    url_context = self._get_url_context(content, url)
                    
                    project_info = {
                        'url': clean_url,
                        'domain': domain,
                        'project_name': project_name,
                        'context': url_context
                    }
                    
                    # Avoid duplicates
                    if not any(p['url'] == clean_url for p in project_urls):
                        project_urls.append(project_info)
        
        # Log all extracted URLs for debugging
        if project_urls:
            logger.info(f"🔍 Extracted {len(project_urls)} project URLs from content:")
            for url_info in project_urls:
                logger.info(f"   - {url_info['project_name']}: {url_info['url']}")
        else:
            logger.warning(f"⚠️ No valid project URLs found in content (length: {len(content)} chars)")
        
        return project_urls

    def _validate_project_url(self, url: str) -> bool:
        """Basic validation for project URLs to avoid broken links."""
        if not url or len(url) < 8:
            return False
            
        # Must start with http/https
        if not url.startswith(('http://', 'https://')):
            return False
            
        # Must have a valid domain structure
        if not re.match(r'https?://[\w.-]+\.[a-z]{2,}', url, re.IGNORECASE):
            return False
            
        # Exclude common placeholder/example domains
        placeholder_domains = [
            'example.com', 'example.org', 'example.net',
            'test.com', 'demo.com', 'sample.com',
            'placeholder.com', 'tempurl.com'
        ]
        
        for placeholder in placeholder_domains:
            if placeholder in url.lower():
                return False
                
        return True

    def _get_url_context(self, content: str, url: str) -> str:
        """Extract context around a URL to better understand the project."""
        # Find the URL in content and get surrounding text
        url_index = content.find(url)
        if url_index == -1:
            return ""
        
        # Get 100 characters before and after the URL
        start = max(0, url_index - 100)
        end = min(len(content), url_index + len(url) + 100)
        context = content[start:end].strip()
        
        # Clean up context
        context = re.sub(r'\s+', ' ', context)  # Remove extra whitespace
        return context

    def _format_contact_information(self, contact_info: str) -> str:
        """Format contact information for proper display in proposal signature with explicit line breaks."""
        if not contact_info or not contact_info.strip():
            return "Email: [Your Email]\nPhone: [Your Phone]"
        
        # Clean up the contact information
        contact_info = contact_info.strip()
        
        # If it already has proper line breaks, format them consistently
        if '\n' in contact_info:
            lines = []
            for line in contact_info.split('\n'):
                line = line.strip()
                if line:
                    # Ensure each line has proper format (Email:, Phone:, etc.)
                    if ':' not in line:
                        # If no colon, try to detect what kind of contact info this is
                        if '@' in line:
                            line = f"Email: {line}"
                        elif any(char.isdigit() for char in line):
                            line = f"Phone: {line}"
                        else:
                            line = f"Contact: {line}"
                    lines.append(line)
            return '\n'.join(lines)
        
        # If it's a single line, try to parse and format it properly
        formatted_lines = []
        
        # Look for email patterns
        import re
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        phone_pattern = r'\+?[\d\s\-\(\)]{10,}'
        
        emails = re.findall(email_pattern, contact_info)
        phones = re.findall(phone_pattern, contact_info)
        
        # Add emails
        for email in emails:
            formatted_lines.append(f"Email: {email}")
        
        # Add phones
        for phone in phones:
            formatted_lines.append(f"Phone: {phone}")
        
        # Look for other patterns like LinkedIn, Website, etc.
        if 'linkedin.com' in contact_info.lower():
            linkedin_match = re.search(r'linkedin\.com/in/[\w\-]+', contact_info, re.IGNORECASE)
            if linkedin_match:
                formatted_lines.append(f"LinkedIn: {linkedin_match.group()}")
        
        # If no patterns found, try to split by common separators
        if not formatted_lines:
            # Try splitting by common patterns
            parts = re.split(r'\s*(?:Email:|Phone:|LinkedIn:|Contact:)\s*', contact_info, flags=re.IGNORECASE)
            if len(parts) > 1:
                # Found structured data
                labels = re.findall(r'(Email:|Phone:|LinkedIn:|Contact:)', contact_info, re.IGNORECASE)
                for i, (label, part) in enumerate(zip(labels, parts[1:])):
                    if part.strip():
                        formatted_lines.append(f"{label.capitalize()} {part.strip()}")
            else:
                # Fallback: just use the original contact info with a generic label
                formatted_lines.append(f"Contact: {contact_info}")
        
        return '\n'.join(formatted_lines) if formatted_lines else contact_info

    def _format_projects_for_prompt(self, projects: List[Dict[str, Any]]) -> str:
        """Format retrieved projects for inclusion in the GPT prompt."""
        if not projects:
            return "No specific project examples available from knowledge base."
        
        formatted_projects = []
        
        # Group by file/project to avoid repetitive chunks
        projects_by_file = {}
        for project in projects:
            file_name = project.get('file_name', 'Unknown Project')
            if file_name not in projects_by_file:
                projects_by_file[file_name] = {
                    'file_name': file_name,
                    'username': project.get('username', ''),
                    'file_url': project.get('file_url', ''),
                    'content_chunks': [],
                    'max_score': project.get('score', 0)
                }
            
            projects_by_file[file_name]['content_chunks'].append({
                'content': project.get('chunk_content', ''),
                'score': project.get('score', 0)
            })
            
            # Track highest relevance score
            if project.get('score', 0) > projects_by_file[file_name]['max_score']:
                projects_by_file[file_name]['max_score'] = project.get('score', 0)
        
        # Sort by relevance and take top 5 most relevant projects
        sorted_projects = sorted(
            projects_by_file.values(), 
            key=lambda x: x['max_score'], 
            reverse=True
        )[:5]
        
        for i, project_data in enumerate(sorted_projects, 1):
            # Combine content chunks for this project
            combined_content = " ".join([
                chunk['content'] for chunk in project_data['content_chunks'][:3]  # Max 3 chunks per project
            ])[:800]  # Limit content length
            
            # Extract actual project URLs from content instead of using S3 file_url
            project_urls = self._extract_project_urls(combined_content)
            
            # Log for debugging
            logger.info(f"🔗 Project {i} ({project_data['file_name']}): Found {len(project_urls)} URLs")
            for url_info in project_urls:
                logger.info(f"   - {url_info['project_name']}: {url_info['url']}")
            
            project_entry = f"\n**Project {i}: {project_data['file_name']}**\n"
            
            # Use extracted URLs from content with project names
            if project_urls:
                url_list = []
                for url_info in project_urls[:2]:  # Max 2 URLs per project
                    # Format: Project Name (exact_url)
                    url_entry = f"{url_info['project_name']} ({url_info['url']})"
                    url_list.append(url_entry)
                project_entry += f"✅ VERIFIED PROJECT URLs: {' | '.join(url_list)}\n"
                project_entry += f"🔒 MANDATORY: Only use these EXACT URLs in your proposal - no modifications allowed\n"
            else:
                project_entry += f"❌ Project URLs: No valid project URLs found in this content\n"
                project_entry += f"🚫 CRITICAL: DO NOT create any clickable links for this project\n"
                project_entry += f"⚠️ MENTION PROJECT WITHOUT BRACKETS: Write 'at [project name]' NOT '[project name](link)'\n"
            
            project_entry += f"Relevance Score: {project_data['max_score']:.3f}\n"
            project_entry += f"Description: {combined_content}\n"
            
            formatted_projects.append(project_entry)
        
        return "\n".join(formatted_projects)
    
    def generate_proposal(
        self,
        client_name: str,
        company_name: str,
        title: str,
        requirements: str,
        company_websites: List[str] = None,
        your_name: str = None,
        upwork_profile_link: str = None,
        contact_information: str = None,
        use_knowledge_base: bool = True
    ) -> Dict[str, Any]:
        """
        Generate a tailored Upwork proposal using GPT-4 and relevant project experience.
        
        Args:
            client_name: Name of the client
            company_name: Company name
            title: Project title
            requirements: Project requirements and description
            company_websites: List of company website URLs
            your_name: Your full name for proposal signature
            upwork_profile_link: Your Upwork profile URL
            contact_information: Your contact details
            use_knowledge_base: Whether to search knowledge base for relevant projects (default: True)
        
        Returns:
            Dict with success status, generated proposal, and metadata
        """
        try:
            if not self.openai_client:
                return {
                    'success': False,
                    'error': 'OpenAI client not available',
                    'proposal': None
                }
            
            # Handle optional client and company names
            client_display = client_name if client_name else "Potential Client"
            company_display = company_name if company_name else "Target Company"
            
            logger.info(f"🚀 Generating proposal for {company_display} - {title[:50]}...")
            
            # Conditionally search for relevant projects based on user preference
            if use_knowledge_base:
                logger.info("🔍 Searching knowledge base for relevant projects...")
                relevant_projects = self._search_relevant_projects(requirements, top_k=15)
                formatted_projects = self._format_projects_for_prompt(relevant_projects)
            else:
                logger.info("⚪ Skipping knowledge base search (disabled by user)")
                relevant_projects = []
                formatted_projects = "Knowledge base search disabled - generating proposal without specific project examples."
            
            # Format company websites
            websites_str = ", ".join(company_websites) if company_websites else "Not provided"
            
            # Format personal information with proper formatting
            personal_info = {
                'your_name': your_name or "[Your Name]",
                'upwork_profile_link': upwork_profile_link or "[Your Upwork Profile Link]", 
                'contact_information': self._format_contact_information(contact_information)
            }
            
            # Create the user prompt with all context (handle optional fields)
            user_prompt = USER_PROMPT_TEMPLATE.format(
                client_name=client_name or "Not specified",
                company_name=company_name or "Not specified",
                company_websites=websites_str,
                title=title,
                requirements=requirements,
                relevant_projects=formatted_projects,
                your_name=personal_info['your_name'],
                upwork_profile_link=personal_info['upwork_profile_link'],
                contact_information=personal_info['contact_information']
            )
            
            # Generate proposal using GPT-4 with optimal settings
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",  # Best available GPT model
                messages=[
                    {"role": "system", "content": UPWORK_PROPOSAL_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,  # Optimal balance of creativity and consistency
                max_tokens=1000,  # Sufficient for 200-400 word proposals
                top_p=0.9,
                frequency_penalty=0.3,  # Reduce repetition
                presence_penalty=0.1   # Encourage topic diversity
            )
            
            generated_proposal = response.choices[0].message.content.strip()
            
            logger.info("✅ Successfully generated Upwork proposal")
            
            return {
                'success': True,
                'proposal': generated_proposal,
                'projects_found': len(relevant_projects),
                'model_used': 'gpt-4o',
                'token_usage': {
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to generate proposal: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'proposal': None
            }


# Create global instance
upwork_proposal_agent = UpworkProposalAgent()
