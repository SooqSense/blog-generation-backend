import streamlit as st
import sys
import os
from pathlib import Path
import time
from datetime import datetime
import json

# Add the project root to the path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Import AI tools from Django management app
try:
    from management_app.upwork_proposal_generator.services.agent.agent import upwork_proposal_agent
    from management_app.knowledge_base.service.pinecone_indexing.pinecone_indexing import PineconeService
    
    AI_TOOLS_AVAILABLE = True
    AI_TOOLS_ERROR = None
    print("✅ Upwork Proposal Generator: AI tools imported successfully")
    
except Exception as e:
    AI_TOOLS_AVAILABLE = False
    AI_TOOLS_ERROR = str(e)
    print(f"⚠️ Upwork Proposal Generator: AI tools import failed - {str(e)}")

# Import database connection using Django settings
try:
    import django
    from django.conf import settings
    
    # Setup Django if not already configured
    if not settings.configured:
        # Set the correct Django settings module path
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'management_app.config.settings')
        # Add the project root to Python path
        import sys
        from pathlib import Path
        project_root = Path(__file__).parent.parent.parent.parent
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        django.setup()
    
    from django.db import connection
    
    # Check if database configuration is available
    db_config = settings.DATABASES['default']
    db_host = db_config.get('HOST')
    db_name = db_config.get('NAME')
    db_user = db_config.get('USER')
    db_password = db_config.get('PASSWORD')
    
    if all([db_host, db_name, db_user, db_password]):
        DATABASE_AVAILABLE = True
        print("✅ Upwork Proposal Generator: Database connection available via Django settings")
    else:
        DATABASE_AVAILABLE = False
        print("⚠️ Upwork Proposal Generator: Database configuration incomplete")
        
except Exception as e:
    DATABASE_AVAILABLE = False
    print(f"⚠️ Upwork Proposal Generator: Database connection failed - {str(e)}")

# Create a simple database operations class using Django ORM
class UpworkProposalQueries:
    """Database operations for Upwork proposals using Django ORM"""
    
    def __init__(self):
        self.connection = connection
    
    def save_upwork_proposal(self, proposal_data, user_id=None):
        """Save upwork proposal to database using raw SQL with Django connection"""
        if not DATABASE_AVAILABLE:
            print("⚠️ Database not available - proposal not saved")
            return None
        
        try:
            # Use raw SQL with Django connection to avoid ORM issues
            import json
            from datetime import datetime
            
            with self.connection.cursor() as cursor:
                # Insert the proposal using raw SQL
                cursor.execute("""
                    INSERT INTO upwork_proposals 
                    (client_name, company_name, title, requirements, company_website_links, 
                     proposal_content, contact_information, upwork_profile_link, your_name, 
                     user_id, status, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    proposal_data.get('client_name', ''),
                    proposal_data.get('company_name', ''),
                    proposal_data.get('title', ''),
                    proposal_data.get('requirements', ''),
                    json.dumps(proposal_data.get('company_website_links', [])),
                    proposal_data.get('proposal_content', ''),
                    proposal_data.get('contact_information', ''),
                    proposal_data.get('upwork_profile_link', ''),
                    proposal_data.get('your_name', ''),
                    user_id,
                    'generated',
                    datetime.now(),
                    datetime.now()
                ))
                
                result = cursor.fetchone()
                if result:
                    proposal_id = result[0]
                    print(f"✅ Upwork proposal saved with ID: {proposal_id}")
                    return proposal_id
                else:
                    print("❌ No ID returned from database insert")
                    return None
            
        except Exception as e:
            print(f"❌ Failed to save upwork proposal: {e}")
            return None


class UpworkProposalGeneratorFeature:
    """Upwork Proposal Generator feature for Streamlit UI"""
    
    def __init__(self):
        self.ai_tools_available = AI_TOOLS_AVAILABLE
        self.ai_tools_error = AI_TOOLS_ERROR
        self.database_available = DATABASE_AVAILABLE
        # Initialize pinecone service
        try:
            self.pinecone_service = PineconeService()
        except Exception as e:
            self.pinecone_service = None
            print(f"⚠️ Pinecone service initialization failed: {str(e)}")
    
    def display_feature_header(self):
        """Display the feature header with branding and info."""
        st.markdown("""
        <div style='text-align: center; padding: 2rem 0;'>
            <h1 style='color: #2E86AB; margin-bottom: 0.5rem;'>🎯 AI Upwork Proposal Generator</h1>
            <p style='color: #666; font-size: 1.1rem;'>Create winning proposals using GPT-4 and your project portfolio</p>
        </div>
        """, unsafe_allow_html=True)
    
    def display_service_status(self):
        """Display the status of AI services."""
        with st.expander("🔧 Service Status", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                if self.ai_tools_available:
                    st.success("✅ Proposal Generator Available")
                    if upwork_proposal_agent.openai_client:
                        st.success("✅ GPT-4 Connected")
                    else:
                        st.error("❌ OpenAI API Key Missing")
                else:
                    st.error(f"❌ Proposal Generator Error: {self.ai_tools_error}")
            
            with col2:
                try:
                    if self.pinecone_service and self.pinecone_service.is_available():
                        st.success("✅ Knowledge Base Connected")
                        # Get index stats
                        stats = self.pinecone_service.get_index_stats()
                        if 'total_vectors' in stats:
                            st.info(f"📄 {stats['total_vectors']} documents indexed")
                    else:
                        st.warning("⚠️ Knowledge Base Unavailable")
                except Exception as e:
                    st.error(f"❌ Knowledge Base Error: {str(e)}")
    
    def create_proposal_form(self):
        """Create the main proposal generation form."""
        st.markdown("### 📝 Project Details")
        
        # Template Upload Section
        st.markdown("#### 📄 Template Upload (Optional)")
        uploaded_template = st.file_uploader(
            "Upload your proposal template (PDF, DOCX, TXT, MD)",
            type=['pdf', 'docx', 'txt', 'md'],
            help="Upload a template document to fill instead of generating a new proposal",
            key="template_upload"
        )
        
        # Store template content in session state
        template_content = None
        if uploaded_template:
            template_content = self._extract_template_content(uploaded_template)
            if template_content:
                st.success(f"✅ Template uploaded: {uploaded_template.name}")
                st.session_state['template_content'] = template_content
                st.session_state['template_name'] = uploaded_template.name
            else:
                st.error("❌ Failed to extract content from template")
                st.session_state['template_content'] = None
        else:
            st.session_state['template_content'] = None
        
        with st.form("proposal_form"):
            # Client Information Section
            st.markdown("#### 👤 Client Information")
            col1, col2 = st.columns(2)
            
            with col1:
                client_name = st.text_input(
                    "Client Name (Optional)", 
                    placeholder="e.g., Roberto Martinez",
                    help="Name of the client contact person (optional)"
                )
            
            with col2:
                company_name = st.text_input(
                    "Company Name (Optional)",
                    placeholder="e.g., Advanced AI Solutions",
                    help="Client's company name (optional)"
                )
            
            # Company websites
            company_websites = st.text_area(
                "Company Website Links (Optional)",
                placeholder="https://company.com\nhttps://company.com/portfolio",
                help="One URL per line. These help understand the company better.",
                height=80
            )
            
            # Personal Information Section
            st.markdown("#### ✍️ Your Information")
            
            col1, col2 = st.columns(2)
            
            with col1:
                your_name = st.text_input(
                    "Your Name (Optional)",
                    placeholder="e.g., Sarah Johnson",
                    help="Your full name for the proposal signature"
                )
                upwork_profile_link = st.text_input(
                    "Your Upwork Profile Link (Optional)",
                    placeholder="https://www.upwork.com/freelancers/~your-profile",
                    help="Your Upwork profile URL"
                )
            
            with col2:
                contact_information = st.text_area(
                    "Your Contact Information (Optional)",
                    placeholder="Email: sarah@example.com\nPhone: +1 (555) 987-6543\nLinkedIn: linkedin.com/in/sarahjohnson",
                    help="Your contact details for the proposal signature. Put each contact method on a new line for best formatting. The system will automatically format it properly in the signature.",
                    height=80
                )
            
            # Project Information Section
            st.markdown("#### 🎯 Project Information")
            
            title = st.text_input(
                "Project Title *",
                placeholder="e.g., AI Automation & Agent Expert (Make.com / N8N)",
                help="The exact title from the Upwork job posting"
            )
            
            requirements = st.text_area(
                "Project Requirements *",
                placeholder="Paste the full job description here...\n\nWhat You'll Do:\n- Build automation workflows\n- Develop AI agents\n- Integrate with APIs\n...",
                help="Complete project description and requirements from Upwork",
                height=200
            )
            
            # Generation Options
            st.markdown("#### ⚙️ Generation Options")
            
            col1, col2 = st.columns(2)
            with col1:
                use_knowledge_base = st.checkbox(
                    "Use Knowledge Base", 
                    value=True,
                    help="Include relevant projects from your portfolio. Uncheck to generate proposals without specific project examples."
                )
            
            with col2:
                show_metadata = st.checkbox(
                    "Show Generation Details", 
                    value=False,
                    help="Display token usage and project matches"
                )
            
            # Submit button
            submit_button = st.form_submit_button(
                "🚀 Generate Proposal",
                type="primary",
                use_container_width=True
            )
            
            return {
                'submit': submit_button,
                'client_name': client_name,
                'company_name': company_name,
                'company_websites': company_websites,
                'your_name': your_name,
                'upwork_profile_link': upwork_profile_link,
                'contact_information': contact_information,
                'title': title,
                'requirements': requirements,
                'use_knowledge_base': use_knowledge_base,
                'show_metadata': show_metadata
            }
    
    def validate_form_data(self, form_data):
        """Validate the form input data."""
        errors = []
        
        # Client name and company name are now optional - no validation needed
        
        if not form_data['title'].strip():
            errors.append("Project title is required")
        
        if not form_data['requirements'].strip():
            errors.append("Project requirements are required")
        elif len(form_data['requirements'].strip()) < 20:
            errors.append("Project requirements should be at least 20 characters long")
        
        return errors
    
    def parse_company_websites(self, websites_text):
        """Parse company websites from textarea input."""
        if not websites_text.strip():
            return []
        
        # Split by newlines and clean up URLs
        urls = []
        for line in websites_text.strip().split('\n'):
            url = line.strip()
            if url:
                # Add https:// if missing
                if not url.startswith(('http://', 'https://')):
                    url = f'https://{url}'
                urls.append(url)
        
        return urls
    
    def _extract_template_content(self, uploaded_file):
        """Extract content from uploaded template file."""
        try:
            # Import document extractor
            from management_app.knowledge_base.service.pdf_extractor.pdf_extractor import DocumentExtractor
            document_extractor = DocumentExtractor()
            
            # Read file content
            file_content = uploaded_file.read()
            
            # Extract content using document extractor
            extraction_result = document_extractor.extract_content(file_content, uploaded_file.name)
            
            if extraction_result['success']:
                return extraction_result['content']
            else:
                st.error(f"❌ Failed to extract content: {extraction_result.get('error', 'Unknown error')}")
                return None
                
        except Exception as e:
            st.error(f"❌ Error extracting template content: {str(e)}")
            return None
    
    def _convert_user_id_to_numeric(self, user_id):
        """Convert user ID to numeric format for database storage."""
        try:
            # If it's already an integer, return it
            if isinstance(user_id, int):
                return user_id
            
            # If it's a string, try to convert to int
            if isinstance(user_id, str):
                # Handle Clerk user IDs (e.g., "user_333qjM1Dv7YGwzJgZMyUNHPgN30")
                if user_id.startswith('user_'):
                    # For Clerk IDs, try to find or create a Django user
                    django_user_id = self._get_or_create_django_user(user_id)
                    if django_user_id:
                        print(f"✅ Clerk user ID {user_id} mapped to Django user ID {django_user_id}")
                        return django_user_id
                    else:
                        print(f"⚠️ Could not create Django user for Clerk ID: {user_id}")
                        return None
                
                # Try to convert string to int
                try:
                    return int(user_id)
                except ValueError:
                    print(f"⚠️ Cannot convert user ID to integer: {user_id}")
                    return None
            
            return None
            
        except Exception as e:
            print(f"⚠️ Error converting user ID: {str(e)}")
            return None
    
    def _get_or_create_django_user(self, clerk_user_id):
        """Get or create a Django user for a Clerk user ID."""
        try:
            if not self.database_available:
                return None
                
            # Try to find existing user by clerk_user_id
            existing_user_id = self._find_user_by_clerk_id(clerk_user_id)
            if existing_user_id:
                return existing_user_id
            
            # Create a new Django user for this Clerk ID
            new_user_id = self._create_django_user_for_clerk(clerk_user_id)
            return new_user_id
            
        except Exception as e:
            print(f"⚠️ Error getting/creating Django user: {str(e)}")
            return None
    
    def _find_user_by_clerk_id(self, clerk_user_id):
        """Find existing Django user by Clerk user ID."""
        try:
            if not self.database_available:
                return None
                
            # Query the database to find existing user by clerk_user_id
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT id FROM users WHERE clerk_user_id = %s
                """, [clerk_user_id])
                
                result = cursor.fetchone()
                if result:
                    return result[0]
                return None
                
        except Exception as e:
            print(f"⚠️ Error finding user by Clerk ID: {str(e)}")
            return None
    
    def _create_django_user_for_clerk(self, clerk_user_id):
        """Create a new Django user for a Clerk user ID."""
        try:
            # Create a basic user record
            # This is a simplified approach - you may want to enhance this
            import hashlib
            import time
            
            # Generate a username from the Clerk ID
            username = f"clerk_user_{hashlib.md5(clerk_user_id.encode()).hexdigest()[:8]}"
            email = f"{username}@clerk.local"  # Placeholder email
            
            # Use the database service to create user
            if hasattr(UpworkProposalQueries, 'create_user'):
                user_id = UpworkProposalQueries.create_user(
                    username=username,
                    email=email,
                    clerk_user_id=clerk_user_id
                )
                return user_id
            else:
                # Fallback: return None to skip saving
                print(f"⚠️ Cannot create user - database service doesn't support user creation")
                return None
                
        except Exception as e:
            print(f"⚠️ Error creating Django user: {str(e)}")
            return None
    
    def _generate_template_proposal(self, template_content, client_name, company_name, title, requirements, company_websites, your_name, upwork_profile_link, contact_information, use_knowledge_base):
        """Generate a filled template using the same logic as regular proposal generation."""
        try:
            # Use the same knowledge base search as regular proposals
            if use_knowledge_base and self.pinecone_service and self.pinecone_service.is_available():
                # Search for relevant projects using the same logic
                search_result = self.pinecone_service.search_documents(
                    query=requirements,
                    top_k=15,
                    include_metadata=True
                )
                
                if search_result['success'] and search_result['results']:
                    # Format projects the same way as regular proposals
                    formatted_projects = self._format_projects_for_template(search_result['results'])
                else:
                    formatted_projects = "No relevant projects found in knowledge base."
            else:
                formatted_projects = "Knowledge base search disabled."
            
            # Create template filling prompt focused on document structure preservation
            template_filling_prompt = f"""
TEMPLATE DOCUMENT TO FILL:
{template_content}

INFORMATION TO FILL THE TEMPLATE WITH:

CLIENT INFORMATION:
- Client Name: {client_name or "Not specified"}
- Company: {company_name or "Not specified"}
- Company Websites: {', '.join(company_websites) if company_websites else "Not provided"}

PROJECT DETAILS:
- Title: {title}
- Requirements: {requirements}

YOUR PERSONAL INFORMATION:
- Your Name: {your_name or "Not provided"}
- Upwork Profile: {upwork_profile_link or "Not provided"}
- Contact Information: {self._format_contact_information(contact_information)}

RELEVANT PROJECTS FROM KNOWLEDGE BASE:
{formatted_projects}

TASK: Fill out the template document above with the provided information while preserving its exact structure and formatting.

CRITICAL REQUIREMENTS:
1. PRESERVE EXACT STRUCTURE: Keep the original document's sections, formatting, bullet points, numbering, and layout exactly as they are
2. FILL PLACEHOLDERS: Replace any placeholder text like [Name], [Company], [Date], [Your Name], etc. with the actual information provided
3. MAINTAIN ORIGINAL TONE: Keep the same writing style and professional tone as the original template
4. NO STRUCTURAL CHANGES: Don't add new sections, change the organization, or modify the document's structure
5. SMART CONTENT INTEGRATION: Use the provided information to enhance the template content where appropriate
6. URL INCLUSION: When relevant projects are provided with URLs, include them in the format "Project Name: Description. (Link: URL)"
7. REMOVE ALL PLACEHOLDERS: Don't leave any placeholder text like [Your Name], [Your Email], etc. in the final output
8. PROFESSIONAL OUTPUT: Ensure the filled document is ready for professional use

The goal is to make the template look exactly like the original but with all the placeholder information filled in with real data.
"""
            
            # Use a specialized template filling system prompt
            template_system_prompt = """
You are a professional document template filler. Your job is to fill out document templates while preserving their exact structure, formatting, and layout.

CRITICAL INSTRUCTIONS:
1. PRESERVE THE EXACT STRUCTURE: Keep the original document's formatting, sections, bullet points, numbering, and layout
2. FILL PLACEHOLDERS ONLY: Replace placeholder text like [Name], [Company], [Date] with actual information
3. MAINTAIN ORIGINAL TONE: Keep the same writing style and tone as the original template
4. NO STRUCTURAL CHANGES: Don't add new sections or change the document's organization
5. PRESERVE FORMATTING: Keep original spacing, indentation, and visual structure
6. SMART CONTENT INTEGRATION: Use the provided information to enhance the template content intelligently
7. URL INCLUSION: When relevant projects are provided with URLs, include them in the format "Project Name: Description. (Link: URL)"
8. REMOVE PLACEHOLDERS: Don't leave any placeholder text in the final output
9. PROFESSIONAL OUTPUT: Ensure the filled document is ready for professional use

Your task is to take the template document and fill it with the provided information while keeping it looking exactly like the original template structure.
"""
            
            response = upwork_proposal_agent.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": template_system_prompt},
                    {"role": "user", "content": template_filling_prompt}
                ],
                temperature=0.7,
                max_tokens=2000,
                top_p=0.9,
                frequency_penalty=0.3,
                presence_penalty=0.1
            )
            
            filled_document = response.choices[0].message.content.strip()
            
            return {
                'success': True,
                'proposal': filled_document,
                'projects_found': len(search_result.get('results', [])) if use_knowledge_base else 0,
                'model_used': 'gpt-4o',
                'token_usage': {
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Template filling failed: {str(e)}",
                'proposal': None
            }
    
    def _format_projects_for_template(self, projects):
        """Format projects for template filling with URLs (same as normal proposal generation)."""
        if not projects:
            return "No relevant projects found."
        
        formatted_projects = []
        for i, project in enumerate(projects[:3], 1):  # Limit to 3 projects
            project_data = project
            file_name = project_data.get('file_name', 'Unknown')
            
            # Extract URLs from both content and metadata
            all_urls = []
            
            # Get URLs from content
            content_urls = project_data.get('urls', [])
            if content_urls:
                for url in content_urls:
                    all_urls.append({
                        'url': url,
                        'project_name': file_name
                    })
            
            # Get URLs from metadata (both document_links and links fields)
            metadata_urls = project_data.get('document_links', [])
            if metadata_urls:
                for url in metadata_urls:
                    all_urls.append({
                        'url': url,
                        'project_name': file_name
                    })
            
            # Also check for links field from search results
            links_urls = project_data.get('links', [])
            if links_urls:
                for url in links_urls:
                    all_urls.append({
                        'url': url,
                        'project_name': file_name
                    })
            
            # Extract URLs from content text (like normal proposal generation)
            chunk_content = project_data.get('chunk_content', '')
            if chunk_content:
                extracted_urls = self._extract_urls_from_content(chunk_content)
                for url_info in extracted_urls:
                    all_urls.append({
                        'url': url_info['url'],
                        'project_name': url_info.get('project_name', file_name)
                    })
            
            project_entry = f"\n**Project {i}: {file_name}**\n"
            
            # Use extracted URLs from content and metadata with project names
            if all_urls:
                url_list = []
                for url_info in all_urls[:2]:  # Max 2 URLs per project
                    # Format: Project Name (exact_url)
                    url_entry = f"{url_info['project_name']} ({url_info['url']})"
                    url_list.append(url_entry)
                project_entry += f"✅ VERIFIED PROJECT URLs: {' | '.join(url_list)}\n"
                project_entry += f"🔒 MANDATORY: Only use these EXACT URLs in your proposal - no modifications allowed\n"
                print(f"🔍 Template: Found URLs for {file_name}: {url_list}")
            else:
                project_entry += f"❌ Project URLs: No valid project URLs found in this content\n"
                project_entry += f"🚫 CRITICAL: DO NOT create any clickable links for this project\n"
                project_entry += f"⚠️ MENTION PROJECT WITHOUT BRACKETS: Write 'at [project name]' NOT '[project name](link)'\n"
                print(f"🔍 Template: No URLs found for {file_name}")
            
            # Add description
            chunk_content = project_data.get('chunk_content', '')
            if chunk_content:
                project_entry += f"Description: {chunk_content[:200]}...\n"
            
            formatted_projects.append(project_entry)
        
        final_formatted = "\n".join(formatted_projects)
        print(f"🔍 Template: Final formatted projects:\n{final_formatted}")
        return final_formatted
    
    def _format_contact_information(self, contact_info):
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
    

    def _extract_urls_from_content(self, content: str):
        """Extract URLs from content text (same logic as normal proposal generation)."""
        import re
        
        # URL regex pattern
        url_pattern = r'https?://(?:[\w-]+\.)+[\w-]+(?:/[^\s<>"\'\[\]{}|\\^`\n]*)?'
        urls = re.findall(url_pattern, content, re.IGNORECASE)
        
        # Excluded patterns (storage URLs, etc.)
        excluded_patterns = [
            r'.*\.s3[\w.-]*\.amazonaws\.com',
            r'.*storage\.googleapis\.com',
            r'.*blob\.core\.windows\.net',
            r'.*dropbox\.com.*',
            r'.*drive\.google\.com.*',
            r'.*onedrive\.com.*',
            r'.*example\.(?:com|org|net).*',
            r'.*localhost.*',
            r'.*0\.0\.0\.0.*',
        ]
        
        extracted_urls = []
        for url in urls:
            # Check if URL should be excluded
            is_excluded = False
            for pattern in excluded_patterns:
                if re.match(pattern, url, re.IGNORECASE):
                    is_excluded = True
                    break
            
            if not is_excluded:
                # Clean up URL
                clean_url = re.sub(r'[.,:;!?)\]}\s]+$', '', url)
                clean_url = clean_url.lower().strip()
                
                if clean_url and len(clean_url) > 10:
                    # Extract project name from URL
                    domain = re.sub(r'https?://', '', clean_url).split('/')[0]
                    project_name = domain.replace('www.', '').replace('.com', '').replace('.ai', '').replace('.io', '')
                    
                    extracted_urls.append({
                        'url': clean_url,
                        'project_name': project_name
                    })
        
        return extracted_urls
    
    def generate_proposal(self, form_data, user_id=None):
        """Generate the proposal using the AI agent and save to database."""
        if not self.ai_tools_available:
            return {
                'success': False,
                'error': f"AI tools not available: {self.ai_tools_error}"
            }
        
        try:
            # Parse company websites
            company_websites = self.parse_company_websites(form_data['company_websites'])
            
            # Check if template is uploaded
            template_content = st.session_state.get('template_content')
            
            if template_content:
                print(f"🔍 Using template filling for proposal generation")
                # Use template filling instead of regular proposal generation
                result = self._generate_template_proposal(
                    template_content=template_content,
                    client_name=form_data['client_name'].strip(),
                    company_name=form_data['company_name'].strip(),
                    title=form_data['title'].strip(),
                    requirements=form_data['requirements'].strip(),
                    company_websites=company_websites,
                    your_name=form_data.get('your_name', '').strip() if form_data.get('your_name') else None,
                    upwork_profile_link=form_data.get('upwork_profile_link', '').strip() if form_data.get('upwork_profile_link') else None,
                    contact_information=form_data.get('contact_information', '').strip() if form_data.get('contact_information') else None,
                    use_knowledge_base=form_data.get('use_knowledge_base', False)
                )
            else:
                # Generate regular proposal
                result = upwork_proposal_agent.generate_proposal(
                    client_name=form_data['client_name'].strip(),
                    company_name=form_data['company_name'].strip(),
                    title=form_data['title'].strip(),
                    requirements=form_data['requirements'].strip(),
                    company_websites=company_websites,
                    your_name=form_data.get('your_name', '').strip() if form_data.get('your_name') else None,
                    upwork_profile_link=form_data.get('upwork_profile_link', '').strip() if form_data.get('upwork_profile_link') else None,
                    contact_information=form_data.get('contact_information', '').strip() if form_data.get('contact_information') else None,
                    use_knowledge_base=form_data.get('use_knowledge_base', False)
                )
            
            # Save to database if generation was successful and user_id is provided
            if result.get('success') and user_id and self.database_available:
                try:
                    # Convert user_id to integer if it's a string (Clerk user ID)
                    numeric_user_id = self._convert_user_id_to_numeric(user_id)
                    
                    if numeric_user_id:
                        # Prepare proposal data as dictionary
                        proposal_data = {
                            'client_name': form_data['client_name'].strip() or None,
                            'company_name': form_data['company_name'].strip() or None,
                            'title': form_data['title'].strip(),
                            'requirements': form_data['requirements'].strip(),
                            'company_website_links': company_websites,
                            'your_name': form_data.get('your_name', '').strip() if form_data.get('your_name') else None,
                            'upwork_profile_link': form_data.get('upwork_profile_link', '').strip() if form_data.get('upwork_profile_link') else None,
                            'contact_information': form_data.get('contact_information', '').strip() if form_data.get('contact_information') else None,
                            'proposal_content': result.get('proposal', ''),
                            'status': 'completed' if result.get('success') else 'failed',
                            'error_message': result.get('error') if not result.get('success') else None
                        }
                        
                        # Create instance of UpworkProposalQueries
                        upwork_queries = UpworkProposalQueries()
                        proposal_id = upwork_queries.save_upwork_proposal(
                            proposal_data=proposal_data,
                            user_id=numeric_user_id
                        )
                        result['proposal_id'] = proposal_id
                        result['saved_to_database'] = True
                        print(f"✅ Proposal saved to database with ID: {proposal_id}")
                    else:
                        result['saved_to_database'] = False
                        result['database_error'] = f"Invalid user ID format: {user_id}"
                        print(f"⚠️ Invalid user ID format: {user_id}")
                        
                except Exception as db_error:
                    print(f"⚠️ Failed to save proposal to database: {str(db_error)}")
                    result['saved_to_database'] = False
                    result['database_error'] = str(db_error)
            else:
                result['saved_to_database'] = False
                if not self.database_available:
                    result['database_error'] = "Database service not available"
                elif not user_id:
                    result['database_error'] = "User ID not provided"
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Generation failed: {str(e)}"
            }
    
    def display_proposal_result(self, result, form_data, show_metadata=False):
        """Display the generated proposal result."""
        if result.get('success'):
            # Check if this is a template result
            template_content = st.session_state.get('template_content')
            if template_content:
                st.markdown("### ✅ Filled Template")
            else:
                st.markdown("### ✅ Generated Proposal")
            
            # Show database save status
            if result.get('saved_to_database'):
                st.success(f"💾 Proposal saved to database (ID: {result.get('proposal_id')})")
            elif result.get('database_error'):
                st.warning(f"⚠️ Database save failed: {result.get('database_error')}")
            else:
                st.info("ℹ️ Proposal not saved to database (user not authenticated)")
            
            # Display the proposal in a styled container
            proposal_content = result.get('proposal', '')
            
            # Use st.container with border for clean display
            with st.container(border=True):
                st.markdown(proposal_content)
            
            # Action buttons
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                if st.button("📋 Copy to Clipboard", use_container_width=True):
                    st.write("Copy this proposal manually from above")
                    st.success("Ready to copy!")
            
            with col2:
                # Download as text file
                template_content = st.session_state.get('template_content')
                if template_content:
                    template_name = st.session_state.get('template_name', 'template').replace(' ', '_').lower()
                    st.download_button(
                        label="📄 Download Filled Template",
                        data=proposal_content,
                        file_name=f"filled_{template_name}_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                        mime="text/plain",
                        use_container_width=True
                    )
                else:
                    company_name_clean = form_data.get('company_name', 'proposal').replace(' ', '_').lower()
                    st.download_button(
                        label="📄 Download Proposal",
                        data=proposal_content,
                        file_name=f"proposal_{company_name_clean}_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                        mime="text/plain",
                        use_container_width=True
                    )
            
            # Show metadata if requested
            if show_metadata:
                st.markdown("### 📊 Generation Details")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    projects_found = result.get('projects_found', 0)
                    st.metric("Projects Found", projects_found)
                
                with col2:
                    model_used = result.get('model_used', 'Unknown')
                    st.metric("AI Model", model_used)
                
                with col3:
                    knowledge_base_used = form_data.get('use_knowledge_base', False)
                    st.metric("Knowledge Base", "✅ Used" if knowledge_base_used else "⚪ Disabled")
                
                # Second row for additional metrics
                col4, col5, col6 = st.columns(3)
                
                with col4:
                    token_usage = result.get('token_usage', {})
                    total_tokens = token_usage.get('total_tokens', 0)
                    st.metric("Tokens Used", total_tokens)
                
                if token_usage:
                    with st.expander("Token Usage Details"):
                        st.json(token_usage)
        
        else:
            st.markdown("### ❌ Generation Failed")
            error = result.get('error', 'Unknown error occurred')
            st.error(f"Error: {error}")
            
            # Troubleshooting tips
            with st.expander("💡 Troubleshooting Tips"):
                st.markdown("""
                - **OpenAI API Key**: Ensure your OpenAI API key is properly configured
                - **Requirements Length**: Make sure project requirements are detailed enough
                - **Knowledge Base**: Check if your Pinecone knowledge base is accessible
                - **Network**: Verify your internet connection for API calls
                """)
    
    def display_examples_section(self):
        """Display example inputs to help users."""
        with st.expander("💡 Example Input", expanded=False):
            st.markdown("""
            **Example Client Information (Optional):**
            - Client Name: `Sarah Johnson` *(optional)*
            - Company: `Digital Health Solutions` *(optional)*
            - Website: `https://digitalhealthsolutions.com` *(optional)*
            
            **Example Your Information:**
            - Your Name: `Alex Rodriguez`
            - Upwork Profile: `https://www.upwork.com/freelancers/~alexrodriguez`
            - Contact Information (each on new line):
            ```
            Email: alex@freelance.com
            Phone: +1 (555) 123-4567
            LinkedIn: linkedin.com/in/alexrodriguez
            ```
            
            **Example Project Title:**
            `Healthcare Mobile App Development - React Native & FHIR Integration`
            
            **Example Requirements:**
            ```
            We're looking for an experienced mobile app developer to create a patient portal mobile application. The project requirements include:
            
            - React Native development for iOS and Android
            - FHIR API integration for health records
            - User authentication and security compliance
            - Push notifications for appointments
            - Offline data synchronization
            - HIPAA compliance implementation
            
            Timeline: 8-12 weeks
            Budget: $15,000 - $25,000
            ```
            """)
    
    def run(self):
        """Main entry point for the Upwork Proposal Generator feature."""
        # Display header
        self.display_feature_header()
        
        # Service status
        self.display_service_status()
        
        # Main content
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Main form
            form_data = self.create_proposal_form()
            
            # Process form submission
            if form_data['submit']:
                # Validate form
                validation_errors = self.validate_form_data(form_data)
                
                if validation_errors:
                    st.error("Please fix the following errors:")
                    for error in validation_errors:
                        st.error(f"• {error}")
                else:
                    # Generate proposal
                    with st.spinner("🤖 Generating your winning proposal..."):
                        # Get user_id from session state (if available)
                        user_id = st.session_state.get('user_id', None)
                        result = self.generate_proposal(form_data, user_id)
                    
                    # Display result
                    self.display_proposal_result(result, form_data, form_data['show_metadata'])
        
        with col2:
            # Side panel with tips and examples
            self.display_examples_section()
            
            # Tips section
            st.markdown("### 💡 Pro Tips")
            st.markdown("""
            - **Be Specific**: Include exact technologies and requirements
            - **Show Understanding**: Mention the client's industry or challenges  
            - **Relevant Experience**: The AI will match your portfolio projects automatically
            - **Professional Tone**: Keep it professional but personable
            - **Clear Timeline**: Mention your availability and project timeline
            """)
            
            # Knowledge Base info
            st.markdown("### 📚 Knowledge Base")
            if self.pinecone_service and self.pinecone_service.is_available():
                stats = self.pinecone_service.get_index_stats()
                if 'total_vectors' in stats:
                    st.info(f"✅ {stats['total_vectors']} documents available for project matching")
                    st.caption("💡 Uncheck 'Use Knowledge Base' to generate proposals without project examples")
                else:
                    st.info("✅ Knowledge base connected")
                    st.caption("💡 You can disable knowledge base usage in Generation Options")
            else:
                st.warning("⚠️ Knowledge base not available")
                st.caption("Proposals will be generated without project examples until knowledge base is configured")


def main():
    """Main function to run the Upwork Proposal Generator feature"""
    
    # Page configuration
    st.set_page_config(
        page_title="AI Upwork Proposal Generator",
        page_icon="🎯",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # Custom CSS for better styling
    st.markdown("""
    <style>
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        max-width: 1200px;
    }
    .stButton > button {
        border-radius: 5px;
    }
    .stTextInput > div > div > input {
        border-radius: 5px;
    }
    .stTextArea > div > div > textarea {
        border-radius: 5px;
    }
    .stForm {
        border: 1px solid #ddd;
        padding: 1rem;
        border-radius: 10px;
        background-color: #fafafa;
    }
    div[data-testid="metric-container"] {
        background-color: #f0f2f6;
        border: 1px solid #cccccc;
        padding: 5% 5% 5% 10%;
        border-radius: 5px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Create and run the feature
    feature = UpworkProposalGeneratorFeature()
    feature.run()


if __name__ == "__main__":
    main()
