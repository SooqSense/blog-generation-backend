"""
Serializers for Upwork Proposal Generator API.
"""

from rest_framework import serializers
from .models import UpworkProposal


class UpworkProposalCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new Upwork proposal requests."""
    
    client_name = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        help_text="Name of the client contact person (optional)",
        style={'placeholder': 'Sarah Johnson'}
    )
    company_name = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        help_text="Name of the client's company (optional)",
        style={'placeholder': 'Digital Solutions LLC'}
    )
    title = serializers.CharField(
        max_length=500,
        help_text="Project title from Upwork job posting",
        style={'placeholder': 'Healthcare App Development - React Native & Node.js'}
    )
    requirements = serializers.CharField(
        help_text="Full project requirements and job description",
        style={'base_template': 'textarea.html', 'placeholder': 'Looking for an experienced mobile app developer to create a healthcare patient management app. Requirements include: user authentication, appointment booking, medical records, push notifications, HIPAA compliance...'}
    )
    company_website_links = serializers.ListField(
        child=serializers.URLField(),
        required=False,
        allow_empty=True,
        help_text="List of company website URLs (optional)",
        style={'placeholder': '["https://company.com", "https://company.com/portfolio"]'}
    )
    
    # Personal information fields
    your_name = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        help_text="Your full name for proposal signature",
        style={'placeholder': 'John Smith'}
    )
    upwork_profile_link = serializers.URLField(
        required=False,
        allow_blank=True,
        help_text="Your Upwork profile URL",
        style={'placeholder': 'https://www.upwork.com/freelancers/~your-profile'}
    )
    contact_information = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Your contact details (email, phone, etc.)",
        style={'base_template': 'textarea.html', 'placeholder': 'Email: john@example.com\nPhone: +1 (555) 123-4567\nLinkedIn: linkedin.com/in/johnsmith'}
    )
    
    class Meta:
        model = UpworkProposal
        fields = [
            'client_name',
            'company_name', 
            'title',
            'requirements',
            'company_website_links',
            'your_name',
            'upwork_profile_link',
            'contact_information'
        ]
    
    def validate_requirements(self, value):
        """Validate requirements field."""
        if not value or len(value.strip()) < 10:
            raise serializers.ValidationError(
                "Requirements must be at least 10 characters long and provide meaningful details."
            )
        return value.strip()
    
    def validate_title(self, value):
        """Validate title field."""
        if not value or len(value.strip()) < 5:
            raise serializers.ValidationError(
                "Title must be at least 5 characters long."
            )
        return value.strip()
    
    def validate_company_website_links(self, value):
        """Validate company website links."""
        if value:
            # Filter out empty strings and validate URLs
            valid_links = []
            for link in value:
                if isinstance(link, str) and link.strip():
                    link = link.strip()
                    if not link.startswith(('http://', 'https://')):
                        link = f'https://{link}'
                    valid_links.append(link)
            return valid_links
        return []


class UpworkProposalResponseSerializer(serializers.ModelSerializer):
    """Serializer for Upwork proposal responses."""
    
    company_website_links = serializers.ListField(
        child=serializers.URLField(),
        read_only=True
    )
    
    class Meta:
        model = UpworkProposal
        fields = [
            'id',
            'client_name',
            'company_name',
            'title', 
            'requirements',
            'company_website_links',
            'your_name',
            'upwork_profile_link',
            'contact_information',
            'proposal_content',
            'status',
            'error_message',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'id',
            'proposal_content', 
            'status',
            'error_message',
            'created_at',
            'updated_at'
        ]


class UpworkProposalListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing proposals."""
    
    class Meta:
        model = UpworkProposal
        fields = [
            'id',
            'company_name',
            'title',
            'status',
            'created_at'
        ]


class ProposalGenerationStatusSerializer(serializers.Serializer):
    """Serializer for proposal generation status responses."""
    
    success = serializers.BooleanField()
    message = serializers.CharField()
    proposal_id = serializers.IntegerField(required=False)
    status = serializers.CharField(required=False)
    proposal_content = serializers.CharField(required=False)
    error = serializers.CharField(required=False)
    metadata = serializers.DictField(required=False)


# Input validation serializers for direct API calls
class GenerateProposalDirectSerializer(serializers.Serializer):
    """Serializer for direct proposal generation without saving to database."""
    
    client_name = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        help_text="Name of the client contact person (optional)",
        style={'placeholder': 'John Smith'}
    )
    company_name = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        help_text="Name of the client's company (optional)",
        style={'placeholder': 'TechCorp Inc.'}
    )
    title = serializers.CharField(
        max_length=500,
        help_text="Project title or job description",
        style={'placeholder': 'Need a Full-Stack Developer for E-commerce Platform'}
    )
    requirements = serializers.CharField(
        min_length=10,
        help_text="Detailed project requirements and description",
        style={'base_template': 'textarea.html', 'placeholder': 'We need a developer to build a modern e-commerce platform with React frontend and Django backend. Must have experience with payment integrations and responsive design...'}
    )
    company_website_links = serializers.ListField(
        child=serializers.URLField(),
        required=False,
        allow_empty=True,
        default=list,
        help_text="List of company website URLs (optional)",
        style={'placeholder': '["https://techcorp.com", "https://techcorp.com/about"]'}
    )
    
    # Personal information fields
    your_name = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        help_text="Your full name for proposal signature",
        style={'placeholder': 'Sarah Johnson'}
    )
    upwork_profile_link = serializers.URLField(
        required=False,
        allow_blank=True,
        help_text="Your Upwork profile URL",
        style={'placeholder': 'https://www.upwork.com/freelancers/~your-profile'}
    )
    contact_information = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Your contact details (email, phone, etc.)",
        style={'base_template': 'textarea.html', 'placeholder': 'Email: sarah@example.com\nPhone: +1 (555) 987-6543\nLinkedIn: linkedin.com/in/sarahjohnson'}
    )
    
    def validate_company_website_links(self, value):
        """Clean and validate website links."""
        if not value:
            return []
        
        valid_links = []
        for link in value:
            if isinstance(link, str) and link.strip():
                link = link.strip()
                if not link.startswith(('http://', 'https://')):
                    link = f'https://{link}'
                valid_links.append(link)
        return valid_links
