"""
Base Clerk Service

Provides common functionality and configuration for all Clerk services.
Implements the base class with shared settings, logging, and utilities.
"""

import logging
import urllib3
from abc import ABC
from typing import Optional, Dict, Any
from django.conf import settings


class BaseClerkService(ABC):
    """
    Base class for all Clerk services.
    
    Provides common configuration, logging, and utility methods
    that are shared across different Clerk service implementations.
    """
    
    def __init__(self):
        """Initialize base service with common Clerk configuration."""
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Core Clerk configuration
        self.clerk_secret_key = getattr(settings, 'CLERK_SECRET_KEY', None)
        self.clerk_publishable_key = getattr(settings, 'NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY', None)
        self.clerk_api_url = getattr(settings, 'CLERK_API_URL', 'https://api.clerk.com')
        self.clerk_jwks_url = getattr(settings, 'CLERK_JWKS_URL', None)
        self.clerk_frontend_url = getattr(settings, 'CLERK_FRONTEND_URL', None)
        
        # JWT configuration
        self.jwt_max_leeway = getattr(settings, 'JWT_MAX_LEEWAY_SECONDS', 600)  # 10 minutes
        self.jwt_disable_iat_on_failure = getattr(settings, 'JWT_DISABLE_IAT_ON_FAILURE', True)
        
        # Session configuration
        self.session_expiry_hours = getattr(settings, 'CLERK_SESSION_EXPIRY_HOURS', 24)  # 24 hours
        
        # Initialize SSL configuration for development
        self._configure_ssl()
        
        # Validate configuration
        self._validate_configuration()
    
    def _configure_ssl(self) -> None:
        """Configure SSL settings for development environments."""
        try:
            # Disable SSL warnings for development
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            self.logger.debug("SSL warnings disabled for development")
        except Exception as e:
            self.logger.warning(f"Could not configure SSL settings: {e}")
    
    def _validate_configuration(self) -> None:
        """Validate essential Clerk configuration."""
        if not self.clerk_secret_key:
            self.logger.warning("CLERK_SECRET_KEY not found in settings")
        
        if not self.clerk_jwks_url:
            self.logger.warning("CLERK_JWKS_URL not found in settings")
        
        self.logger.info(f"Clerk service initialized: {self.__class__.__name__}")
    
    def get_auth_headers(self) -> Dict[str, str]:
        """
        Get standard authorization headers for Clerk API requests.
        
        Returns:
            Dict containing authorization headers
            
        Raises:
            ValueError: If clerk_secret_key is not configured
        """
        if not self.clerk_secret_key:
            raise ValueError("Clerk secret key not configured")
        
        return {
            'Authorization': f'Bearer {self.clerk_secret_key}',
            'Content-Type': 'application/json'
        }
    
    def log_debug_info(self, title: str, data: Dict[str, Any]) -> None:
        """
        Log debug information in a formatted way.
        
        Args:
            title: Title for the debug section
            data: Dictionary of data to log
        """
        self.logger.info("=" * 80)
        self.logger.info(f"{title.upper()}")
        self.logger.info("=" * 80)
        
        for key, value in data.items():
            self.logger.info(f"  {key}: {value}")
        
        self.logger.info("=" * 80)
    
    def handle_api_error(self, operation: str, status_code: int, response_text: str) -> None:
        """
        Handle and log API errors consistently.
        
        Args:
            operation: Description of the operation that failed
            status_code: HTTP status code
            response_text: Response text from the API
        """
        self.logger.error(
            f"Failed to {operation}: {status_code} - {response_text}"
        )
    
    def is_development_mode(self) -> bool:
        """
        Check if the application is running in development mode.
        
        Returns:
            True if in development mode, False otherwise
        """
        return getattr(settings, 'DEBUG', False)
    
    def get_service_info(self) -> Dict[str, Any]:
        """
        Get information about the service configuration.
        
        Returns:
            Dictionary containing service configuration info
        """
        return {
            'service_name': self.__class__.__name__,
            'clerk_api_url': self.clerk_api_url,
            'has_secret_key': bool(self.clerk_secret_key),
            'has_jwks_url': bool(self.clerk_jwks_url),
            'session_expiry_hours': self.session_expiry_hours,
            'jwt_max_leeway': self.jwt_max_leeway,
            'development_mode': self.is_development_mode()
        }
