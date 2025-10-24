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
    use_knowledge_base = serializers.BooleanField(
        required=False,
        default=True,
        help_text="Whether to use knowledge base for relevant project examples"
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
            'contact_information',
            'use_knowledge_base'
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
            'use_knowledge_base',
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




# Additional Management Serializers for Upwork Proposals
class UpworkProposalListSerializer(serializers.ModelSerializer):
    """Serializer for listing Upwork proposals with basic information."""
    
    class Meta:
        model = UpworkProposal
        fields = [
            'id', 'client_name', 'company_name', 'title', 'status', 'username', 'email',
            'organization_id', 'organization_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class UpworkProposalDeleteSerializer(serializers.Serializer):
    """Serializer for Upwork proposal deletion response."""
    success = serializers.BooleanField()
    message = serializers.CharField()
    deleted_count = serializers.IntegerField(required=False)




class ErrorResponseSerializer(serializers.Serializer):
    """Serializer for error responses."""
    error = serializers.CharField()
