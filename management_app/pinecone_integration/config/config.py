"""
Configuration settings for Pinecone indexing.
"""

import os

# Import Django settings only when needed to avoid import-time errors
def _get_django_settings():
    """Get Django settings with proper error handling."""
    try:
        # Check if Django is available and configured
        from django import apps
        if not apps.ready:
            # Django is not fully configured
            return None
        
        from django.conf import settings
        if not settings.configured:
            return None
            
        return settings
    except Exception:
        return None


class PineconeConfig:
    """Configuration class for Pinecone indexing settings."""

    # Environment-based unified index configuration
    @property
    def index_name(self) -> str:
        """Get unified index name based on environment."""
        settings = _get_django_settings()
        
        # Try to get from Django settings first
        if settings:
            env_name = getattr(settings, "PINECONE_INDEX_NAME", None)
            if env_name:
                return env_name
            
            # Fallback based on Django environment
            django_env = getattr(settings, "DJANGO_ENVIRONMENT", None)
            if django_env:
                return f"artilence-{django_env.lower()}"
        
        # Fallback to environment variables
        env_name = os.getenv("PINECONE_INDEX_NAME")
        if env_name:
            return env_name
            
        # Final fallback based on environment variable
        django_env = os.getenv("DJANGO_ENVIRONMENT", "development")
        return f"artilence-{django_env.lower()}"

    # Unified index configuration (standardized dimensions)
    DIMENSION = 1536  # Standardized to 1536 for both projects and FAQs
    METRIC = "cosine"

    # Namespace configuration
    PROJECTS_NAMESPACE = "Projects"
    FAQ_NAMESPACE = "FAQ"
    PDFS_NAMESPACE = "PDFS"  # New namespace for PDF documents
    DEFAULT_NAMESPACE = "Default"

    # Legacy configuration (deprecated but kept for backward compatibility)
    @property
    def INDEX_NAME(self) -> str:
        """Legacy property for backward compatibility."""
        return self.index_name

    @property
    def FAQ_INDEX_NAME(self) -> str:
        """Legacy property for backward compatibility."""
        return self.index_name

    # Keep legacy dimensions for reference
    FAQ_DIMENSION = 1536  # Now same as unified dimension
    FAQ_METRIC = "cosine"

    # Cloud configuration
    CLOUD = "aws"
    REGION = "us-east-1"

    # Embedding configuration
    EMBEDDING_MODEL = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS = 1536  # Unified dimension for all content types

    # API Keys
    @property
    def pinecone_api_key(self) -> str:
        """Get Pinecone API key from settings or environment."""
        settings = _get_django_settings()
        if settings:
            api_key = getattr(settings, "PINECONE_API_KEY", None)
            if api_key:
                return api_key
        return os.getenv("PINECONE_API_KEY", "")

    @property
    def openai_api_key(self) -> str:
        """Get OpenAI API key from settings or environment."""
        settings = _get_django_settings()
        if settings:
            api_key = getattr(settings, "OPENAI_API_KEY", None)
            if api_key:
                return api_key
        return os.getenv("OPENAI_API_KEY", "")

    # Metadata limits
    MAX_DESCRIPTION_LENGTH = 500
    MAX_TECHNOLOGIES = 10
    MAX_TAGS = 10

    # Search defaults
    DEFAULT_TOP_K = 10
    MAX_TOP_K = 50

    # FAQ specific configuration
    MAX_FAQ_RESULTS = 3
    FAQ_SEARCH_THRESHOLD = 0.5
    FAQ_HIGH_CONFIDENCE_THRESHOLD = 0.6


# Create singleton instance
config = PineconeConfig()
