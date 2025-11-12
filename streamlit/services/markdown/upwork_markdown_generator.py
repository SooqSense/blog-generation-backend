"""
Upwork Markdown Generator Module
Generates markdown content for Upwork proposals
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class UpworkMarkdownGenerator:
    """Generates markdown content for Upwork proposals"""
    
    @staticmethod
    def generate(proposal_data: Dict[str, Any]) -> str:
        """Generate Markdown content for Upwork proposal - returns raw MD content from database"""
        try:
            # Get the raw proposal content from the database
            proposal_content = proposal_data.get('proposal_content', '')
            
            if not proposal_content:
                # If no proposal content, create a basic structure
                proposal_content = f"""# Upwork Proposal

**Project:** {proposal_data.get('title', 'Unknown Project')}
**Company:** {proposal_data.get('company_name', 'Unknown Company')}
**Client:** {proposal_data.get('client_name', 'Unknown Client')}
**Author:** {proposal_data.get('username', 'Unknown')}
**Created:** {proposal_data.get('created_at', 'Unknown')}

## Project Requirements
{proposal_data.get('requirements', 'No requirements provided')}

## Proposal Content
No proposal content available yet. Please wait for the AI to generate the proposal.

## Contact Information
{proposal_data.get('contact_information', 'No contact information provided')}
"""
            
            return proposal_content
            
        except Exception as e:
            logger.error(f"Error generating Upwork proposal MD: {str(e)}")
            raise

