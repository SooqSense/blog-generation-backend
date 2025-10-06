"""
GPT-powered agent for generating Upwork proposals using knowledge base and best practices.
Enhanced with LangChain framework for better embeddings and project matching.
"""

import logging
import re
from typing import Dict, Any, List, Optional
from openai import OpenAI

# LangChain imports
try:
    from langchain_community.embeddings import OpenAIEmbeddings
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain_community.vectorstores import Pinecone
    from langchain.schema import Document
    from langchain.chains import RetrievalQA
    from langchain_community.llms import OpenAI as LangChainOpenAI
    LANGCHAIN_AVAILABLE = True
except ImportError:
    # Fallback to old imports if new ones are not available
    try:
        from langchain.embeddings import OpenAIEmbeddings
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        from langchain.vectorstores import Pinecone
        from langchain.schema import Document
        from langchain.chains import RetrievalQA
        from langchain.llms import OpenAI as LangChainOpenAI
        LANGCHAIN_AVAILABLE = True
        print("⚠️ Using deprecated LangChain imports - consider upgrading to langchain-community")
    except ImportError:
        LANGCHAIN_AVAILABLE = False
        print("⚠️ LangChain not available, using fallback methods")

from ..prompts.prompts import UPWORK_PROPOSAL_SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

# Initialize module logger BEFORE any logging is used
logger = logging.getLogger(__name__)

# Import Pinecone service from knowledge base
try:
    from management_app.knowledge_base.service.pinecone_indexing.pinecone_indexing import PineconeService
    pinecone_service = PineconeService()
    PINECONE_AVAILABLE = True
    logger.info("✅ Pinecone service imported successfully for Upwork proposals")
except Exception as e:
    logger.error(f"❌ Failed to import Pinecone service: {str(e)}")
    pinecone_service = None
    PINECONE_AVAILABLE = False


class UpworkProposalAgent:
    """Agent for generating tailored Upwork proposals using GPT-4 and knowledge base."""
    
    def __init__(self):
        self.openai_client = self._initialize_openai()
        self.pinecone_service = pinecone_service
        self.pinecone_available = PINECONE_AVAILABLE
        self.langchain_available = LANGCHAIN_AVAILABLE
        
        # Initialize LangChain components if available
        if self.langchain_available:
            self.embeddings = self._initialize_embeddings()
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                length_function=len,
            )
        else:
            self.embeddings = None
            self.text_splitter = None
    
    def _initialize_openai(self) -> Optional[OpenAI]:
        """Initialize OpenAI client with API key."""
        try:
            # Try Django settings first, fallback to environment variable
            api_key = None
            
            try:
                from django.conf import settings
                api_key = getattr(settings, 'OPENAI_API_KEY', None)
            except Exception:
                # Django settings not available, use environment variable
                pass
            
            # Fallback to environment variable
            if not api_key:
                import os
                api_key = os.getenv('OPENAI_API_KEY')
            
            if api_key:
                return OpenAI(api_key=api_key)
            else:
                logger.error("❌ OpenAI API key not found in Django settings or environment variables")
                return None
        except Exception as e:
            logger.error(f"❌ Failed to initialize OpenAI client: {str(e)}")
            return None
    
    def _initialize_embeddings(self) -> Optional[OpenAIEmbeddings]:
        """Initialize LangChain OpenAI embeddings."""
        try:
            if not self.langchain_available:
                return None
                
            # Get API key
            api_key = None
            try:
                from django.conf import settings
                api_key = getattr(settings, 'OPENAI_API_KEY', None)
            except Exception:
                pass
            
            if not api_key:
                import os
                api_key = os.getenv('OPENAI_API_KEY')
            
            if api_key:
                embeddings = OpenAIEmbeddings(
                    openai_api_key=api_key,
                    model="text-embedding-3-small",  # Use latest embedding model
                    chunk_size=1000
                )
                logger.info("✅ LangChain embeddings initialized successfully")
                return embeddings
            else:
                logger.error("❌ OpenAI API key not found for embeddings")
                return None
        except Exception as e:
            logger.error(f"❌ Failed to initialize LangChain embeddings: {str(e)}")
            return None
    
    def _search_relevant_projects(self, requirements: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """Search for relevant projects in the knowledge base based on requirements with enhanced embeddings."""
        try:
            if not self.pinecone_available or not self.pinecone_service or not self.pinecone_service.is_available():
                logger.warning("⚠️ Pinecone service not available, proceeding without project context")
                return []
            
            logger.info(f"🔍 Searching knowledge base for projects related to: {requirements[:100]}...")
            
            # Enhanced query processing for better matching
            enhanced_query = self._enhance_query_for_search(requirements)
            logger.info(f"🔍 Enhanced query: {enhanced_query[:100]}...")
            
            # Search for relevant documents in Pinecone
            search_result = self.pinecone_service.search_documents(
                query=enhanced_query,
                top_k=top_k,
                include_metadata=True
            )
            
            if search_result['success'] and search_result['results']:
                # Filter and rank results based on relevance
                filtered_results = self._filter_and_rank_results(search_result['results'], requirements)
                logger.info(f"✅ Found {len(filtered_results)} relevant project documents after filtering")
                return filtered_results
            else:
                logger.info("ℹ️ No relevant projects found in knowledge base")
                return []
                
        except Exception as e:
            logger.error(f"❌ Error searching for relevant projects: {str(e)}")
            return []
    
    def _enhance_query_for_search(self, requirements: str) -> str:
        """Enhance the search query to improve project matching."""
        try:
            # Extract key terms and concepts
            key_terms = self._extract_key_terms(requirements)
            
            # Add industry-specific terms
            industry_terms = self._identify_industry_terms(requirements)
            
            # Combine original query with enhanced terms
            enhanced_query = f"{requirements}"
            
            if key_terms:
                enhanced_query += f" {' '.join(key_terms)}"
            
            if industry_terms:
                enhanced_query += f" {' '.join(industry_terms)}"
            
            return enhanced_query
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to enhance query: {str(e)}")
            return requirements
    
    def _extract_key_terms(self, text: str) -> List[str]:
        """Extract key technical terms and concepts from requirements."""
        # Common technical terms and concepts
        tech_terms = [
            'web development', 'mobile app', 'API', 'database', 'frontend', 'backend',
            'React', 'Vue', 'Angular', 'Node.js', 'Python', 'JavaScript', 'TypeScript',
            'AWS', 'Azure', 'Google Cloud', 'Docker', 'Kubernetes', 'DevOps',
            'machine learning', 'AI', 'data science', 'analytics', 'blockchain',
            'e-commerce', 'CMS', 'WordPress', 'Shopify', 'Magento',
            'UI/UX', 'design', 'prototype', 'wireframe', 'responsive'
        ]
        
        # Industry-specific terms
        industry_terms = [
            'healthcare', 'fintech', 'edtech', 'saas', 'b2b', 'b2c',
            'startup', 'enterprise', 'scalable', 'microservices',
            'real-time', 'automation', 'integration', 'migration'
        ]
        
        found_terms = []
        text_lower = text.lower()
        
        for term in tech_terms + industry_terms:
            if term in text_lower:
                found_terms.append(term)
        
        return found_terms
    
    def _identify_industry_terms(self, text: str) -> List[str]:
        """Identify industry-specific terms to improve matching."""
        industry_mappings = {
            'healthcare': ['medical', 'patient', 'hospital', 'clinic', 'health', 'diagnosis', 'treatment'],
            'fintech': ['financial', 'payment', 'banking', 'trading', 'investment', 'cryptocurrency'],
            'edtech': ['education', 'learning', 'student', 'course', 'training', 'academic'],
            'ecommerce': ['online store', 'shopping', 'retail', 'inventory', 'checkout', 'payment'],
            'saas': ['software as a service', 'subscription', 'cloud-based', 'platform', 'dashboard']
        }
        
        found_industry_terms = []
        text_lower = text.lower()
        
        for industry, terms in industry_mappings.items():
            if any(term in text_lower for term in terms):
                found_industry_terms.extend(terms)
        
        return found_industry_terms
    
    def _filter_and_rank_results(self, results: List[Dict[str, Any]], requirements: str) -> List[Dict[str, Any]]:
        """Filter and rank search results based on relevance to requirements."""
        try:
            if not results:
                return results
            
            # Extract key terms from requirements
            req_terms = self._extract_key_terms(requirements)
            req_industry = self._identify_industry_terms(requirements)
            
            # Score each result
            scored_results = []
            for result in results:
                score = result.get('score', 0)
                content = result.get('chunk_content', '').lower()
                file_name = result.get('file_name', '').lower()
                
                # Boost score for matching terms
                for term in req_terms:
                    if term in content or term in file_name:
                        score += 0.1
                
                # Boost score for industry relevance
                for term in req_industry:
                    if term in content or term in file_name:
                        score += 0.15
                
                # Boost score for project URLs (indicates real projects)
                if 'http' in content and not any(storage in content for storage in ['s3', 'storage', 'blob']):
                    score += 0.2
                
                result['enhanced_score'] = score
                scored_results.append(result)
            
            # Sort by enhanced score and return top results
            scored_results.sort(key=lambda x: x['enhanced_score'], reverse=True)
            return scored_results[:8]  # Return top 8 most relevant
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to filter and rank results: {str(e)}")
            return results
    
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
            
            # Extract actual project URLs from content and metadata
            project_urls = self._extract_project_urls(combined_content)
            
            # Also check for links stored in Pinecone metadata
            metadata_links = []
            for chunk in project_data['content_chunks']:
                if 'links' in chunk and chunk['links']:
                    metadata_links.extend(chunk['links'])
            
            # Combine URLs from content extraction and metadata
            all_urls = project_urls.copy()
            for link in metadata_links:
                if link and link not in [url_info['url'] for url_info in project_urls]:
                    # Create a simple project info for metadata links
                    domain = re.sub(r'https?://', '', link).split('/')[0]
                    project_name = domain.replace('www.', '').replace('.com', '').replace('.ai', '').replace('.io', '')
                    all_urls.append({
                        'url': link,
                        'domain': domain,
                        'project_name': project_name,
                        'context': f"Project link from {project_data['file_name']}"
                    })
            
            # Log for debugging
            logger.info(f"🔗 Project {i} ({project_data['file_name']}): Found {len(all_urls)} URLs (content: {len(project_urls)}, metadata: {len(metadata_links)})")
            for url_info in all_urls:
                logger.info(f"   - {url_info['project_name']}: {url_info['url']}")
            
            project_entry = f"\n**Project {i}: {project_data['file_name']}**\n"
            
            # Use extracted URLs from content and metadata with project names
            if all_urls:
                url_list = []
                for url_info in all_urls[:2]:  # Max 2 URLs per project
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
