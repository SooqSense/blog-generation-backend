"""
Configuration settings for Pinecone indexing.
"""

from django.conf import settings


class PineconeConfig:
    """Centralized configuration for Pinecone indexing."""

    # Core index configuration
    INDEX_NAME = settings.PINECONE_INDEX_NAME
    DIMENSION = 1536
    METRIC = "cosine"

    # Namespaces
    PROJECTS_NAMESPACE = "Projects"
    FAQ_NAMESPACE = "FAQ"
    PDFS_NAMESPACE = "PDFS"
    DEFAULT_NAMESPACE = "Default"

    # Legacy compatibility
    INDEX_NAME_LEGACY = settings.PINECONE_INDEX_NAME
    FAQ_INDEX_NAME = settings.PINECONE_INDEX_NAME

    # Cloud and embedding configuration
    CLOUD = "aws"
    REGION = "us-east-1"
    EMBEDDING_MODEL = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS = 1536

    # API keys
    PINECONE_API_KEY = settings.PINECONE_API_KEY
    OPENAI_API_KEY = settings.OPENAI_API_KEY

    # Metadata limits
    MAX_DESCRIPTION_LENGTH = 500
    MAX_TECHNOLOGIES = 10
    MAX_TAGS = 10

    # Search configuration
    DEFAULT_TOP_K = 10
    MAX_TOP_K = 50

    # FAQ configuration
    MAX_FAQ_RESULTS = 3
    FAQ_SEARCH_THRESHOLD = 0.5
    FAQ_HIGH_CONFIDENCE_THRESHOLD = 0.6


# Singleton instance
config = PineconeConfig()
