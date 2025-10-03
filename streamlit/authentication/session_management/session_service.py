"""
Session service for authentication system
Handles session persistence, validation, and management
"""

import streamlit as st
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from ..user_management import UserService

logger = logging.getLogger(__name__)

class SessionService:
    """Service for session management operations"""
    
    def __init__(self, user_service: UserService):
        """
        Initialize session service
        
        Args:
            user_service: UserService instance
        """
        self.user_service = user_service
        self.max_session_duration = timedelta(hours=24)
        
        # Initialize session cache
        self._init_session_cache()
    
    def _init_session_cache(self):
        """Initialize session cache using Streamlit's cache"""
        # Initialize cache keys if they don't exist
        if 'auth_cache_initialized' not in st.session_state:
            st.session_state.auth_cache_initialized = True
            st.session_state.auth_cache = {}
            logger.info("Session cache initialized")
        
        # Ensure auth_cache always exists
        if 'auth_cache' not in st.session_state:
            st.session_state.auth_cache = {}
        
        # Initialize persistent session storage using st.cache_data
        self._init_persistent_storage()
    
    def _init_persistent_storage(self):
        """Initialize persistent storage using st.cache_data"""
        # Create a persistent cache for user sessions
        if 'persistent_sessions' not in st.session_state:
            st.session_state.persistent_sessions = {}
    
    @st.cache_data(ttl=86400)  # Cache for 24 hours
    def _get_persistent_user_data(_clerk_user_id: str) -> Optional[Dict[str, Any]]:
        """Get persistent user data by Clerk user ID"""
        return None  # This will be populated by the cache
    
    def _store_persistent_user_data(self, clerk_user_id: str, user_data: Dict[str, Any]):
        """Store user data persistently using st.cache_data"""
        try:
            # Use st.cache_data for true persistence across refreshes
            self._get_persistent_user_data.clear()  # Clear cache first
            
            # Store in persistent sessions
            st.session_state.persistent_sessions[clerk_user_id] = {
                'user_data': user_data,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"User data stored persistently for: {clerk_user_id}")
        except Exception as e:
            logger.error(f"Error storing persistent user data: {e}")
    
    def _get_persistent_user_data_by_id(self, clerk_user_id: str) -> Optional[Dict[str, Any]]:
        """Get persistent user data by Clerk user ID"""
        try:
            if 'persistent_sessions' not in st.session_state:
                return None
            
            persistent_data = st.session_state.persistent_sessions.get(clerk_user_id)
            
            if persistent_data:
                # Check if cache is still valid (24 hours)
                timestamp = persistent_data.get('timestamp')
                if timestamp:
                    try:
                        cache_time = datetime.fromisoformat(timestamp)
                        if datetime.now() - cache_time < self.max_session_duration:
                            return persistent_data['user_data']
                        else:
                            # Remove expired cache
                            del st.session_state.persistent_sessions[clerk_user_id]
                    except Exception:
                        # Remove invalid cache
                        del st.session_state.persistent_sessions[clerk_user_id]
            
            return None
        except Exception as e:
            logger.error(f"Error getting persistent user data: {e}")
            return None
    
    def _cache_user_data(self, clerk_user_id: str, user_data: Dict[str, Any]):
        """Cache user data using Streamlit's cache"""
        try:
            # Ensure auth_cache exists
            if 'auth_cache' not in st.session_state:
                st.session_state.auth_cache = {}
            
            # Use a simple cache key based on clerk_user_id
            cache_key = f"user_data_{clerk_user_id}"
            st.session_state.auth_cache[cache_key] = {
                'user_data': user_data,
                'timestamp': datetime.now().isoformat()
            }
            logger.info(f"User data cached for: {clerk_user_id}")
        except Exception as e:
            logger.error(f"Error caching user data: {e}")
    
    def _get_cached_user_data_by_id(self, clerk_user_id: str) -> Optional[Dict[str, Any]]:
        """Get cached user data by Clerk user ID"""
        try:
            # Ensure auth_cache exists
            if 'auth_cache' not in st.session_state:
                st.session_state.auth_cache = {}
                return None
            
            cache_key = f"user_data_{clerk_user_id}"
            cached_data = st.session_state.auth_cache.get(cache_key)
            
            if cached_data:
                # Check if cache is still valid (24 hours)
                timestamp = datetime.fromisoformat(cached_data['timestamp'])
                if datetime.now() - timestamp < self.max_session_duration:
                    return cached_data['user_data']
                else:
                    # Remove expired cache
                    del st.session_state.auth_cache[cache_key]
            
            return None
        except Exception as e:
            logger.error(f"Error getting cached user data: {e}")
            return None
    
    def set_authenticated_user(self, user_data: Dict[str, Any]) -> bool:
        """
        Set user as authenticated in session state with cache storage
        
        Args:
            user_data: User data to store in session
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Set Streamlit session state
            st.session_state.authenticated = True
            st.session_state.user_data = user_data
            
            # Set individual fields for backward compatibility
            st.session_state.user_email = user_data.get('email')
            st.session_state.username = user_data.get('name', user_data.get('email', '').split('@')[0])
            st.session_state.user_id = user_data.get('id')
            st.session_state.django_user_id = user_data.get('django_user_id')
            st.session_state.clerk_user_id = user_data.get('clerk_user_id')
            
            # Store authentication timestamp for session management
            auth_timestamp = datetime.now().isoformat()
            st.session_state.auth_timestamp = auth_timestamp
            
            # Cache user data for persistence
            clerk_user_id = user_data.get('clerk_user_id')
            if clerk_user_id:
                self._cache_user_data(clerk_user_id, user_data)
                self._store_persistent_user_data(clerk_user_id, user_data)
            
            logger.info(f"User authenticated: {user_data.get('email')} (Django ID: {user_data.get('django_user_id')}) - Cached")
            return True
            
        except Exception as e:
            logger.error(f"Error setting authenticated user: {e}")
            return False
    
    def clear_authentication_state(self) -> bool:
        """
        Clear authentication state and cache
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get user info before clearing
            user_data = st.session_state.get('user_data', {})
            django_user_id = user_data.get('django_user_id')
            clerk_user_id = user_data.get('clerk_user_id')
            
            # Clear from cache
            if clerk_user_id and 'auth_cache' in st.session_state:
                cache_key = f"user_data_{clerk_user_id}"
                if cache_key in st.session_state.auth_cache:
                    del st.session_state.auth_cache[cache_key]
            
            # Clear from persistent sessions
            if clerk_user_id and 'persistent_sessions' in st.session_state:
                if clerk_user_id in st.session_state.persistent_sessions:
                    del st.session_state.persistent_sessions[clerk_user_id]
            
            # Clear session state
            keys_to_clear = [
                'authenticated', 'user_data', 'user_email', 'username', 'user_id',
                'django_user_id', 'clerk_user_id', 'auth_timestamp'
            ]
            
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            
            # Log logout
            if django_user_id:
                logger.info(f"User {django_user_id} logged out")
            
            logger.info("User logged out successfully - Cache cleared")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing authentication state: {e}")
            return False
    
    def is_authenticated(self) -> bool:
        """
        Check if user is currently authenticated with cache recovery
        
        Returns:
            True if authenticated, False otherwise
        """
        # First check Streamlit session state
        session_authenticated = st.session_state.get('authenticated', False)
        logger.info(f"🔍 Session authenticated: {session_authenticated}")
        
        if session_authenticated:
            return True
        
        # If not in session state, try to recover from cache
        logger.info("🔍 Attempting cache recovery...")
        cache_recovered = self._recover_from_cache()
        logger.info(f"🔍 Cache recovery result: {cache_recovered}")
        return cache_recovered
    
    def _recover_from_cache(self) -> bool:
        """Recover session from cache"""
        try:
            # First try persistent sessions
            if 'persistent_sessions' in st.session_state:
                for clerk_user_id, persistent_data in st.session_state.persistent_sessions.items():
                    user_data = persistent_data.get('user_data')
                    timestamp = persistent_data.get('timestamp')
                    
                    if user_data and timestamp:
                        # Check if cache is still valid
                        try:
                            cache_time = datetime.fromisoformat(timestamp)
                            if datetime.now() - cache_time < self.max_session_duration:
                                # Restore session state
                                st.session_state.authenticated = True
                                st.session_state.user_data = user_data
                                st.session_state.user_email = user_data.get('email')
                                st.session_state.username = user_data.get('name', user_data.get('email', '').split('@')[0])
                                st.session_state.user_id = user_data.get('id')
                                st.session_state.django_user_id = user_data.get('django_user_id')
                                st.session_state.clerk_user_id = user_data.get('clerk_user_id')
                                st.session_state.auth_timestamp = timestamp
                                
                                logger.info(f"Session recovered from persistent storage for: {user_data.get('email')}")
                                return True
                            else:
                                # Remove expired cache
                                del st.session_state.persistent_sessions[clerk_user_id]
                        except Exception:
                            # Remove invalid cache
                            del st.session_state.persistent_sessions[clerk_user_id]
            
            # Fallback to regular cache
            if 'auth_cache' not in st.session_state:
                st.session_state.auth_cache = {}
                return False
            
            # Look for any cached user data
            for cache_key, cached_data in st.session_state.auth_cache.items():
                if cache_key.startswith('user_data_'):
                    user_data = cached_data.get('user_data')
                    timestamp = cached_data.get('timestamp')
                    
                    if user_data and timestamp:
                        # Check if cache is still valid
                        try:
                            cache_time = datetime.fromisoformat(timestamp)
                            if datetime.now() - cache_time < self.max_session_duration:
                                # Restore session state
                                st.session_state.authenticated = True
                                st.session_state.user_data = user_data
                                st.session_state.user_email = user_data.get('email')
                                st.session_state.username = user_data.get('name', user_data.get('email', '').split('@')[0])
                                st.session_state.user_id = user_data.get('id')
                                st.session_state.django_user_id = user_data.get('django_user_id')
                                st.session_state.clerk_user_id = user_data.get('clerk_user_id')
                                st.session_state.auth_timestamp = timestamp
                                
                                logger.info(f"Session recovered from cache for: {user_data.get('email')}")
                                return True
                            else:
                                # Remove expired cache
                                del st.session_state.auth_cache[cache_key]
                        except Exception:
                            # Remove invalid cache
                            del st.session_state.auth_cache[cache_key]
            
            return False
            
        except Exception as e:
            logger.error(f"Error recovering from cache: {e}")
            return False
    
    def get_user_data(self) -> Dict[str, Any]:
        """
        Get current user data with Django user information
        
        Returns:
            User data dict
        """
        user_data = st.session_state.get('user_data', {})
        
        # If we have a Django user ID, fetch fresh data from database
        django_user_id = user_data.get('django_user_id')
        if django_user_id:
            try:
                fresh_user_data = self.user_service.get_user_by_id(django_user_id)
                if fresh_user_data:
                    # Update session data with fresh database data
                    user_data.update({
                        'django_user_id': fresh_user_data['id'],
                        'username': fresh_user_data['username'],
                        'email': fresh_user_data['email'],
                        'clerk_user_id': fresh_user_data['clerk_user_id'],
                        'created_at': fresh_user_data['created_at'],
                        'updated_at': fresh_user_data['updated_at'],
                        'last_login': fresh_user_data['last_login']
                    })
            except Exception as e:
                logger.error(f"Error fetching user data from database: {e}")
        
        return user_data
    
    def validate_session_persistence(self) -> bool:
        """
        Validate that the session is still valid and user exists in database
        
        Returns:
            True if valid, False otherwise
        """
        try:
            user_data = st.session_state.get('user_data', {})
            django_user_id = user_data.get('django_user_id')
            clerk_user_id = user_data.get('clerk_user_id')
            
            if not django_user_id or not clerk_user_id:
                logger.warning("Session missing required user identifiers")
                return False
            
            # Check if user still exists in database and is active
            if not self.user_service.validate_user_session(django_user_id, clerk_user_id):
                logger.warning(f"User {django_user_id} session validation failed")
                return False
            
            # Check session age
            auth_timestamp = st.session_state.get('auth_timestamp')
            if auth_timestamp:
                try:
                    auth_time = datetime.fromisoformat(auth_timestamp)
                    session_age = datetime.now() - auth_time
                    
                    if session_age > self.max_session_duration:
                        logger.info(f"Session expired after {session_age}")
                        return False
                except Exception as e:
                    logger.error(f"Error parsing auth timestamp: {e}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating session persistence: {e}")
            return False
    
    def handle_auth_callback(self) -> bool:
        """
        Handle authentication with cache-based session persistence
        
        Returns:
            True if authenticated, False otherwise
        """
        try:
            # Check if there's a pending user ID authentication
            if 'pending_user_id' in st.session_state:
                user_id = st.session_state.pending_user_id
                del st.session_state.pending_user_id
                
                logger.info(f"Processing pending authentication for user: {user_id}")
                # This would need to be handled by the main auth class
                return False  # Placeholder
            
            # Check if already authenticated (this will try to recover from cache)
            if self.is_authenticated():
                # Validate session persistence
                return self.validate_session_persistence()
            
            return False
            
        except Exception as e:
            logger.error(f"Error handling auth callback: {e}")
            return False
    
    def get_session_info(self) -> Dict[str, Any]:
        """
        Get current session information
        
        Returns:
            Session info dict
        """
        try:
            user_data = self.get_user_data()
            auth_timestamp = st.session_state.get('auth_timestamp')
            
            session_info = {
                'authenticated': self.is_authenticated(),
                'user_id': user_data.get('django_user_id'),
                'clerk_user_id': user_data.get('clerk_user_id'),
                'email': user_data.get('email'),
                'username': user_data.get('username'),
                'auth_timestamp': auth_timestamp
            }
            
            # Calculate session age
            if auth_timestamp:
                try:
                    auth_time = datetime.fromisoformat(auth_timestamp)
                    session_age = datetime.now() - auth_time
                    session_info['session_age_seconds'] = session_age.total_seconds()
                    session_info['session_age_hours'] = session_age.total_seconds() / 3600
                except Exception as e:
                    logger.error(f"Error calculating session age: {e}")
            
            return session_info
            
        except Exception as e:
            logger.error(f"Error getting session info: {e}")
            return {}
    
    def refresh_session(self) -> bool:
        """
        Refresh session timestamp
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.is_authenticated():
                st.session_state.auth_timestamp = datetime.now().isoformat()
                logger.info("Session refreshed")
                return True
            return False
        except Exception as e:
            logger.error(f"Error refreshing session: {e}")
            return False
    
    def set_max_session_duration(self, duration: timedelta):
        """
        Set maximum session duration
        
        Args:
            duration: Maximum session duration
        """
        self.max_session_duration = duration
        logger.info(f"Max session duration set to {duration}")
    
    def cleanup_expired_sessions(self) -> int:
        """
        Cleanup expired sessions (placeholder for future database cleanup)
        
        Returns:
            Number of sessions cleaned up
        """
        # This would be implemented if we store sessions in database
        # For now, just return 0
        return 0
