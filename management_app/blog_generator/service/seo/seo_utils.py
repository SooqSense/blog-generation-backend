"""
SEO Utility Functions.
Handles reading time, word count, content hash, and other utility functions.
"""

import hashlib
import re
from typing import Dict, Any


class SEOUtils:
    """Utility functions for SEO operations."""

    @staticmethod
    def calculate_reading_time(word_count: int, words_per_minute: int = 200) -> int:
        """
        Calculate reading time in minutes.

        Args:
            word_count: Total number of words
            words_per_minute: Average reading speed (default: 200)

        Returns:
            Reading time in minutes (minimum 1)
        """
        if word_count <= 0:
            return 1
        reading_time = max(1, round(word_count / words_per_minute))
        return reading_time

    @staticmethod
    def count_words(text: str) -> int:
        """
        Count words in text.

        Args:
            text: Text content

        Returns:
            Word count
        """
        if not text:
            return 0
        # Remove markdown syntax and count words
        clean_text = re.sub(r'[#*`\[\]()]', ' ', text)
        words = clean_text.split()
        return len(words)

    @staticmethod
    def generate_content_hash(content: str) -> str:
        """
        Generate SHA256 hash for content duplicate detection.

        Args:
            content: Content to hash

        Returns:
            SHA256 hash string
        """
        if not content:
            return ""
        content_normalized = re.sub(r'\s+', ' ', content.strip().lower())
        return hashlib.sha256(content_normalized.encode('utf-8')).hexdigest()

    @staticmethod
    def generate_slug(text: str, max_length: int = 100) -> str:
        """
        Generate URL-friendly slug from text.

        Args:
            text: Text to convert to slug
            max_length: Maximum slug length

        Returns:
            URL-friendly slug
        """
        if not text:
            return ""
        
        # Convert to lowercase
        slug = text.lower()
        
        # Remove special characters, keep alphanumeric, spaces, and hyphens
        slug = re.sub(r'[^a-z0-9\s-]', '', slug)
        
        # Replace spaces and multiple hyphens with single hyphen
        slug = re.sub(r'[\s-]+', '-', slug)
        
        # Remove leading/trailing hyphens
        slug = slug.strip('-')
        
        # Truncate to max_length
        if len(slug) > max_length:
            slug = slug[:max_length].rstrip('-')
        
        return slug

    @staticmethod
    def extract_keywords_from_text(text: str, max_keywords: int = 10) -> list:
        """
        Extract potential keywords from text (simple frequency-based).

        Note: This is a basic implementation. The SEO agent will provide better keyword analysis.

        Args:
            text: Text to analyze
            max_keywords: Maximum number of keywords to return

        Returns:
            List of potential keywords
        """
        if not text:
            return []
        
        # Remove markdown and special characters
        clean_text = re.sub(r'[#*`\[\]()]', ' ', text.lower())
        
        # Split into words
        words = re.findall(r'\b[a-z]{4,}\b', clean_text)  # Words with 4+ characters
        
        # Count frequency
        word_freq = {}
        for word in words:
            # Skip common stop words
            stop_words = {'this', 'that', 'with', 'from', 'have', 'been', 'will', 'your', 'their', 
                         'there', 'what', 'which', 'about', 'would', 'could', 'should', 'these', 
                         'those', 'them', 'they', 'when', 'where', 'were', 'than', 'then', 'more'}
            if word not in stop_words:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Sort by frequency and return top keywords
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, _ in sorted_words[:max_keywords]]

    @staticmethod
    def validate_seo_title(title: str) -> Dict[str, Any]:
        """
        Validate SEO title against best practices.

        Args:
            title: Title to validate

        Returns:
            Validation result with recommendations
        """
        result = {
            "valid": True,
            "length": len(title),
            "recommendations": []
        }
        
        if len(title) < 30:
            result["valid"] = False
            result["recommendations"].append("Title is too short (minimum 30 characters recommended)")
        elif len(title) > 60:
            result["valid"] = False
            result["recommendations"].append("Title is too long (maximum 60 characters recommended)")
        
        if not title.strip():
            result["valid"] = False
            result["recommendations"].append("Title cannot be empty")
        
        return result

    @staticmethod
    def validate_meta_description(description: str) -> Dict[str, Any]:
        """
        Validate meta description against best practices.

        Args:
            description: Meta description to validate

        Returns:
            Validation result with recommendations
        """
        result = {
            "valid": True,
            "length": len(description),
            "recommendations": []
        }
        
        if len(description) < 120:
            result["valid"] = False
            result["recommendations"].append("Meta description is too short (minimum 120 characters recommended)")
        elif len(description) > 160:
            result["valid"] = False
            result["recommendations"].append("Meta description is too long (maximum 160 characters recommended)")
        
        if not description.strip():
            result["valid"] = False
            result["recommendations"].append("Meta description cannot be empty")
        
        return result

    @staticmethod
    def generate_canonical_url(base_url: str, slug: str) -> str:
        """
        Generate canonical URL.

        Args:
            base_url: Base website URL
            slug: Blog post slug

        Returns:
            Canonical URL
        """
        base_url = base_url.rstrip('/')
        slug = slug.lstrip('/')
        return f"{base_url}/blog/{slug}"

