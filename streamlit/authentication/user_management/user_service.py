"""
User service for authentication system
Handles user creation, retrieval, and management operations
"""

import logging
import hashlib
import os
from typing import Optional, Dict, Any
from datetime import datetime

from ..database import DatabaseOperations

logger = logging.getLogger(__name__)

class UserService:
    """Service for user management operations"""
    
    def __init__(self, db_operations: DatabaseOperations):
        """
        Initialize user service
        
        Args:
            db_operations: DatabaseOperations instance
        """
        self.db_operations = db_operations
    
    def create_or_get_user(self, clerk_user_id: str, clerk_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Create or get Django user from Clerk user ID
        
        Args:
            clerk_user_id: Clerk user ID
            clerk_data: Clerk user data
            
        Returns:
            User data dict or None
        """
        try:
            # First, try to find existing user
            existing_user = self.db_operations.get_user_by_clerk_id(clerk_user_id)
            
            if existing_user:
                logger.info(f"✅ Found existing Django user for Clerk ID: {clerk_user_id}")
                existing_user['is_new'] = False
                return existing_user
            
            # Create new user
            email = clerk_data.get('email', f'clerk_{clerk_user_id[-8:]}@clerk.dev')
            username = clerk_data.get('name', f'clerk_user_{clerk_user_id[-8:]}')
            
            # Generate a secure password hash (user won't use it for login)
            password_hash = self._generate_password_hash()
            
            # Create user
            new_user = self.db_operations.create_user(
                username=username,
                email=email,
                password_hash=password_hash,
                clerk_user_id=clerk_user_id,
                is_active=True,
                is_staff=False,
                is_superuser=False
            )
            
            if new_user:
                logger.info(f"✅ Created new Django user for Clerk ID: {clerk_user_id}")
                new_user['is_new'] = True
                return new_user
            
            return None
            
        except Exception as e:
            logger.error(f"Error creating/getting user: {e}")
            return None
    
    def update_user_last_login(self, user_id: int) -> bool:
        """
        Update user's last login timestamp
        
        Args:
            user_id: Django user ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            success = self.db_operations.update_last_login(user_id)
            if success:
                logger.info(f"✅ Updated last login for user ID: {user_id}")
            return success
        except Exception as e:
            logger.error(f"Error updating last login: {e}")
            return False
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get user by Django user ID
        
        Args:
            user_id: Django user ID
            
        Returns:
            User data dict or None
        """
        try:
            return self.db_operations.get_user_by_id(user_id)
        except Exception as e:
            logger.error(f"Error getting user by ID: {e}")
            return None
    
    def get_user_by_clerk_id(self, clerk_user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user by Clerk user ID
        
        Args:
            clerk_user_id: Clerk user ID
            
        Returns:
            User data dict or None
        """
        try:
            return self.db_operations.get_user_by_clerk_id(clerk_user_id)
        except Exception as e:
            logger.error(f"Error getting user by Clerk ID: {e}")
            return None
    
    def validate_user_session(self, user_id: int, clerk_user_id: str) -> bool:
        """
        Validate user session
        
        Args:
            user_id: Django user ID
            clerk_user_id: Clerk user ID
            
        Returns:
            True if valid, False otherwise
        """
        try:
            return self.db_operations.validate_user_session(user_id, clerk_user_id)
        except Exception as e:
            logger.error(f"Error validating user session: {e}")
            return False
    
    def get_user_specific_data(self, table_name: str, user_id: int, 
                              columns: str = "*", additional_filters: str = "", 
                              params: Optional[list] = None) -> list:
        """
        Get user-specific data with automatic isolation
        
        Args:
            table_name: Database table name
            user_id: Django user ID
            columns: Columns to select
            additional_filters: Additional WHERE conditions
            params: Additional parameters
            
        Returns:
            List of records
        """
        try:
            return self.db_operations.get_user_specific_data(
                table_name, user_id, columns, additional_filters, params
            )
        except Exception as e:
            logger.error(f"Error getting user-specific data: {e}")
            return []
    
    def count_user_records(self, table_name: str, user_id: int) -> int:
        """
        Count user records in a table
        
        Args:
            table_name: Database table name
            user_id: Django user ID
            
        Returns:
            Number of records
        """
        try:
            return self.db_operations.count_user_records(table_name, user_id)
        except Exception as e:
            logger.error(f"Error counting user records: {e}")
            return 0
    
    def get_user_data_isolation_filter(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get database filter conditions to ensure user data isolation
        
        Args:
            user_data: User data dict
            
        Returns:
            Filter conditions dict
        """
        django_user_id = user_data.get('django_user_id')
        clerk_user_id = user_data.get('clerk_user_id')
        
        if not django_user_id:
            raise Exception("User not authenticated - cannot provide data isolation")
        
        return {
            'django_user_id': django_user_id,
            'clerk_user_id': clerk_user_id,
            'user_email': user_data.get('email'),
            'username': user_data.get('username')
        }
    
    def _generate_password_hash(self) -> str:
        """Generate a secure password hash"""
        return hashlib.sha256(os.urandom(32).hex().encode()).hexdigest()
    
    def get_user_statistics(self) -> Dict[str, Any]:
        """
        Get user statistics
        
        Returns:
            Statistics dict
        """
        try:
            from datetime import datetime, timedelta
            recent_threshold = datetime.now() - timedelta(days=7)
            
            # This would need to be implemented in DatabaseOperations
            # For now, return basic info
            return {
                'total_users': 0,
                'active_users': 0,
                'recent_logins': 0
            }
        except Exception as e:
            logger.error(f"Error getting user statistics: {e}")
            return {}
