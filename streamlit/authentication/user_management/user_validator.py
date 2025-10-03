"""
User validation for authentication system
Handles user data validation and security checks
"""

import logging
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class UserValidator:
    """Validates user data and authentication requests"""
    
    def __init__(self):
        """Initialize user validator"""
        self.clerk_id_pattern = re.compile(r'^user_[a-zA-Z0-9]{20,}$')
        self.email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        self.username_pattern = re.compile(r'^[a-zA-Z0-9._-]{3,50}$')
    
    def validate_clerk_user_id(self, clerk_user_id: str) -> bool:
        """
        Validate Clerk user ID format
        
        Args:
            clerk_user_id: Clerk user ID to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not clerk_user_id or not isinstance(clerk_user_id, str):
            return False
        
        return bool(self.clerk_id_pattern.match(clerk_user_id.strip()))
    
    def validate_email(self, email: str) -> bool:
        """
        Validate email format
        
        Args:
            email: Email to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not email or not isinstance(email, str):
            return False
        
        return bool(self.email_pattern.match(email.strip()))
    
    def validate_username(self, username: str) -> bool:
        """
        Validate username format
        
        Args:
            username: Username to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not username or not isinstance(username, str):
            return False
        
        return bool(self.username_pattern.match(username.strip()))
    
    def validate_user_data(self, user_data: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Validate user data
        
        Args:
            user_data: User data to validate
            
        Returns:
            Dict with validation errors (empty if valid)
        """
        errors = {
            'clerk_user_id': [],
            'email': [],
            'username': [],
            'general': []
        }
        
        # Validate Clerk user ID
        clerk_user_id = user_data.get('clerk_user_id')
        if not clerk_user_id:
            errors['clerk_user_id'].append("Clerk user ID is required")
        elif not self.validate_clerk_user_id(clerk_user_id):
            errors['clerk_user_id'].append("Invalid Clerk user ID format")
        
        # Validate email
        email = user_data.get('email')
        if not email:
            errors['email'].append("Email is required")
        elif not self.validate_email(email):
            errors['email'].append("Invalid email format")
        
        # Validate username
        username = user_data.get('username')
        if not username:
            errors['username'].append("Username is required")
        elif not self.validate_username(username):
            errors['username'].append("Invalid username format")
        
        # Remove empty error lists
        return {k: v for k, v in errors.items() if v}
    
    def validate_session_data(self, session_data: Dict[str, Any]) -> bool:
        """
        Validate session data
        
        Args:
            session_data: Session data to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ['django_user_id', 'clerk_user_id', 'email']
        
        for field in required_fields:
            if not session_data.get(field):
                logger.warning(f"Session missing required field: {field}")
                return False
        
        # Validate session age
        auth_timestamp = session_data.get('auth_timestamp')
        if auth_timestamp:
            try:
                auth_time = datetime.fromisoformat(auth_timestamp)
                session_age = datetime.now() - auth_time
                
                # Check if session is too old (e.g., 24 hours)
                max_session_duration = timedelta(hours=24)
                if session_age > max_session_duration:
                    logger.info(f"Session expired after {session_age}")
                    return False
            except Exception as e:
                logger.error(f"Error parsing auth timestamp: {e}")
                return False
        
        return True
    
    def validate_authentication_request(self, user_id: str) -> Dict[str, Any]:
        """
        Validate authentication request
        
        Args:
            user_id: User ID to validate
            
        Returns:
            Validation result dict
        """
        result = {
            'valid': False,
            'errors': [],
            'warnings': []
        }
        
        if not user_id:
            result['errors'].append("User ID is required")
            return result
        
        if not isinstance(user_id, str):
            result['errors'].append("User ID must be a string")
            return result
        
        user_id = user_id.strip()
        
        if not user_id:
            result['errors'].append("User ID cannot be empty")
            return result
        
        if not self.validate_clerk_user_id(user_id):
            result['errors'].append("Invalid Clerk user ID format")
            return result
        
        result['valid'] = True
        return result
    
    def sanitize_user_input(self, input_data: str) -> str:
        """
        Sanitize user input
        
        Args:
            input_data: Input to sanitize
            
        Returns:
            Sanitized input
        """
        if not input_data or not isinstance(input_data, str):
            return ""
        
        # Remove potentially dangerous characters
        sanitized = input_data.strip()
        
        # Remove null bytes and control characters
        sanitized = ''.join(char for char in sanitized if ord(char) >= 32)
        
        # Limit length
        if len(sanitized) > 1000:
            sanitized = sanitized[:1000]
            logger.warning("User input truncated due to length")
        
        return sanitized
    
    def check_password_strength(self, password: str) -> Dict[str, Any]:
        """
        Check password strength (for future use)
        
        Args:
            password: Password to check
            
        Returns:
            Strength analysis dict
        """
        # This is a placeholder for future password validation
        # Since we're using Clerk for authentication, this might not be needed
        return {
            'strong': True,
            'score': 100,
            'feedback': []
        }
    
    def validate_data_access_permissions(self, user_data: Dict[str, Any], 
                                       requested_user_id: int) -> bool:
        """
        Validate that user can access requested data
        
        Args:
            user_data: Current user data
            requested_user_id: User ID being accessed
            
        Returns:
            True if access is allowed, False otherwise
        """
        current_user_id = user_data.get('django_user_id')
        
        if not current_user_id:
            logger.warning("No current user ID for permission check")
            return False
        
        # Users can only access their own data
        if current_user_id != requested_user_id:
            logger.warning(f"User {current_user_id} attempted to access data for user {requested_user_id}")
            return False
        
        return True
