"""
Session validation for authentication system
Handles session data validation and security checks
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class SessionValidator:
    """Validates session data and authentication state"""
    
    def __init__(self, max_session_duration: timedelta = timedelta(hours=24)):
        """
        Initialize session validator
        
        Args:
            max_session_duration: Maximum allowed session duration
        """
        self.max_session_duration = max_session_duration
    
    def validate_session_data(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate session data
        
        Args:
            session_data: Session data to validate
            
        Returns:
            Validation result dict
        """
        result = {
            'valid': False,
            'errors': [],
            'warnings': []
        }
        
        # Check required fields
        required_fields = ['django_user_id', 'clerk_user_id', 'email']
        for field in required_fields:
            if not session_data.get(field):
                result['errors'].append(f"Missing required field: {field}")
        
        if result['errors']:
            return result
        
        # Validate session age
        auth_timestamp = session_data.get('auth_timestamp')
        if auth_timestamp:
            try:
                auth_time = datetime.fromisoformat(auth_timestamp)
                session_age = datetime.now() - auth_time
                
                if session_age > self.max_session_duration:
                    result['errors'].append(f"Session expired after {session_age}")
                    return result
                
                # Warning for sessions approaching expiry
                if session_age > self.max_session_duration * 0.8:
                    result['warnings'].append("Session approaching expiry")
                    
            except Exception as e:
                result['errors'].append(f"Invalid auth timestamp: {e}")
                return result
        
        result['valid'] = True
        return result
    
    def validate_authentication_state(self, auth_state: Dict[str, Any]) -> bool:
        """
        Validate authentication state
        
        Args:
            auth_state: Authentication state to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Check if authenticated flag is set
            if not auth_state.get('authenticated', False):
                return False
            
            # Check if user data exists
            user_data = auth_state.get('user_data', {})
            if not user_data:
                return False
            
            # Validate user data
            validation_result = self.validate_session_data(user_data)
            return validation_result['valid']
            
        except Exception as e:
            logger.error(f"Error validating authentication state: {e}")
            return False
    
    def check_session_security(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check session security
        
        Args:
            session_data: Session data to check
            
        Returns:
            Security check result
        """
        result = {
            'secure': True,
            'warnings': [],
            'recommendations': []
        }
        
        # Check session age
        auth_timestamp = session_data.get('auth_timestamp')
        if auth_timestamp:
            try:
                auth_time = datetime.fromisoformat(auth_timestamp)
                session_age = datetime.now() - auth_time
                
                # Warning for long sessions
                if session_age > timedelta(hours=12):
                    result['warnings'].append("Long-running session detected")
                    result['recommendations'].append("Consider refreshing session")
                
                # Warning for very long sessions
                if session_age > timedelta(hours=48):
                    result['warnings'].append("Very long session detected")
                    result['recommendations'].append("Consider logging out and back in")
                    
            except Exception as e:
                result['warnings'].append(f"Could not parse session timestamp: {e}")
        
        # Check for suspicious patterns
        user_id = session_data.get('django_user_id')
        clerk_id = session_data.get('clerk_user_id')
        
        if user_id and clerk_id:
            # Check if IDs are consistent
            if not isinstance(user_id, int) or not isinstance(clerk_id, str):
                result['warnings'].append("Inconsistent user ID types")
                result['secure'] = False
        
        return result
    
    def validate_user_permissions(self, current_user_data: Dict[str, Any], 
                                requested_user_id: int) -> bool:
        """
        Validate user permissions for data access
        
        Args:
            current_user_data: Current user's data
            requested_user_id: User ID being accessed
            
        Returns:
            True if access is allowed, False otherwise
        """
        try:
            current_user_id = current_user_data.get('django_user_id')
            
            if not current_user_id:
                logger.warning("No current user ID for permission check")
                return False
            
            # Users can only access their own data
            if current_user_id != requested_user_id:
                logger.warning(f"User {current_user_id} attempted to access data for user {requested_user_id}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating user permissions: {e}")
            return False
    
    def check_session_integrity(self, session_data: Dict[str, Any]) -> bool:
        """
        Check session data integrity
        
        Args:
            session_data: Session data to check
            
        Returns:
            True if integrity is maintained, False otherwise
        """
        try:
            # Check for required fields
            required_fields = ['django_user_id', 'clerk_user_id', 'email']
            for field in required_fields:
                if not session_data.get(field):
                    logger.warning(f"Session missing required field: {field}")
                    return False
            
            # Check data types
            if not isinstance(session_data.get('django_user_id'), int):
                logger.warning("Invalid django_user_id type")
                return False
            
            if not isinstance(session_data.get('clerk_user_id'), str):
                logger.warning("Invalid clerk_user_id type")
                return False
            
            if not isinstance(session_data.get('email'), str):
                logger.warning("Invalid email type")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking session integrity: {e}")
            return False
    
    def get_session_health_score(self, session_data: Dict[str, Any]) -> int:
        """
        Get session health score (0-100)
        
        Args:
            session_data: Session data to evaluate
            
        Returns:
            Health score (0-100)
        """
        try:
            score = 100
            
            # Check session age
            auth_timestamp = session_data.get('auth_timestamp')
            if auth_timestamp:
                try:
                    auth_time = datetime.fromisoformat(auth_timestamp)
                    session_age = datetime.now() - auth_time
                    
                    # Deduct points for old sessions
                    if session_age > timedelta(hours=12):
                        score -= 20
                    if session_age > timedelta(hours=24):
                        score -= 30
                    if session_age > self.max_session_duration:
                        score = 0
                        
                except Exception:
                    score -= 10
            
            # Check data integrity
            if not self.check_session_integrity(session_data):
                score -= 30
            
            # Check security
            security_result = self.check_session_security(session_data)
            if not security_result['secure']:
                score -= 20
            
            # Deduct points for warnings
            score -= len(security_result['warnings']) * 5
            
            return max(0, score)
            
        except Exception as e:
            logger.error(f"Error calculating session health score: {e}")
            return 0
