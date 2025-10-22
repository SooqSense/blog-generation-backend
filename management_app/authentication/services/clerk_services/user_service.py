"""
Clerk User Service

Handles user management, synchronization, and Django user model operations.
Provides methods for creating, updating, and managing user data from Clerk.
"""

from typing import Optional, Dict, Any, List
from django.contrib.auth import get_user_model
from django.db import transaction

from .base_service import BaseClerkService
from .jwt_service import ClerkJWTAuthService
from .api_service import ClerkAPIService

User = get_user_model()


class ClerkUserService(BaseClerkService):
    """
    Service for managing Django users from Clerk data.
    
    Provides methods for:
    - Creating and updating Django users from Clerk payloads
    - Synchronizing user data with Clerk API
    - Handling user authentication flow
    - Managing user organizations and roles
    """
    
    def __init__(self):
        """Initialize user service with dependent services."""
        super().__init__()
        self.jwt_service = ClerkJWTAuthService()
        self.api_service = ClerkAPIService()
    
    def authenticate_user(self, token: str) -> Optional[User]:
        """
        Authenticate user with Clerk JWT token.
        
        This is the main entry point for user authentication.
        
        Args:
            token: JWT token from Clerk
            
        Returns:
            Django User instance if authentication successful, None otherwise
        """
        # Check if token is expired
        if self.jwt_service.is_token_expired(token):
            self.logger.warning("Token is expired according to Clerk's expiry")
            return None
        
        # Verify the token
        payload = self.jwt_service.verify_jwt_token(token)
        if not payload:
            self.logger.warning("Token verification failed")
            return None
        
        # Get or create user from payload
        return self.get_or_create_user(payload)
    
    def get_or_create_user(self, clerk_payload: Dict[str, Any]) -> Optional[User]:
        """
        Get existing user or create new user from Clerk payload.
        
        Args:
            clerk_payload: Decoded JWT payload from Clerk
            
        Returns:
            Django User instance if successful, None otherwise
        """
        try:
            # Extract basic user information from JWT
            user_info = self.jwt_service.extract_user_info(clerk_payload)
            clerk_user_id = user_info.get('clerk_user_id')
            
            if not clerk_user_id:
                self.logger.error("No clerk_user_id in JWT payload")
                return None
            
            # Fetch additional user data from Clerk API
            enhanced_user_info = self._enhance_user_info(user_info, clerk_user_id)
            
            # Log user processing information
            self.log_debug_info("Processing User from JWT", enhanced_user_info)
            
            # Try to find existing user
            user = self._find_existing_user(clerk_user_id, enhanced_user_info.get('email'))
            
            if user:
                return self._update_existing_user(user, enhanced_user_info)
            else:
                return self._create_new_user(enhanced_user_info)
                
        except Exception as e:
            self.logger.error(f"Error getting/creating user: {e}")
            return None
    
    def _enhance_user_info(self, user_info: Dict[str, Any], clerk_user_id: str) -> Dict[str, Any]:
        """
        Enhance user information with data from Clerk API.
        
        Args:
            user_info: Basic user info from JWT
            clerk_user_id: Clerk user ID
            
        Returns:
            Enhanced user information dictionary
        """
        enhanced_info = user_info.copy()
        
        # Fetch all user organizations from Clerk API
        self.logger.info("Fetching all user organizations from Clerk API...")
        all_organizations = self.api_service.get_user_organizations(clerk_user_id)
        enhanced_info['all_organizations'] = all_organizations
        
        # If user info is missing from JWT, fetch from Clerk API
        if not enhanced_info.get('email') or not enhanced_info.get('username'):
            self.logger.info("User info missing from JWT, fetching from Clerk API...")
            api_user_info = self.api_service.get_user_info(clerk_user_id)
            
            if api_user_info:
                enhanced_info.update(self._extract_api_user_info(api_user_info, enhanced_info))
        
        return enhanced_info
    
    def _extract_api_user_info(self, api_user_info: Dict[str, Any], current_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract user information from Clerk API response.
        
        Args:
            api_user_info: User data from Clerk API
            current_info: Current user information
            
        Returns:
            Updated user information dictionary
        """
        updates = {}
        
        # Extract email addresses
        email_addresses = api_user_info.get('email_addresses', [])
        if email_addresses and not current_info.get('email'):
            updates['email'] = email_addresses[0].get('email_address')
        
        # Extract username
        if not current_info.get('username'):
            updates['username'] = api_user_info.get('username')
        
        # Extract first and last name
        updates['first_name'] = api_user_info.get('first_name')
        updates['last_name'] = api_user_info.get('last_name')
        
        if updates:
            self.log_debug_info("Fetched from Clerk API", updates)
        
        return updates
    
    def _find_existing_user(self, clerk_user_id: str, email: Optional[str]) -> Optional[User]:
        """
        Find existing user by Clerk ID or email.
        
        Args:
            clerk_user_id: Clerk user ID
            email: User email address
            
        Returns:
            Existing User instance or None
        """
        # Try to get existing user by clerk_user_id first (most reliable)
        user = User.objects.filter(clerk_user_id=clerk_user_id).first()
        
        # If not found by clerk_user_id, try by email (for legacy users)
        if not user and email:
            user_by_email = User.objects.filter(email=email).first()
            if user_by_email:
                self.logger.info(
                    f"Found user by email but not clerk_user_id - this may be a legacy user"
                )
                user = user_by_email
        
        if user:
            self.logger.info(f"Found existing user: {user.username} (ID: {user.id})")
        
        return user
    
    @transaction.atomic
    def _update_existing_user(self, user: User, user_info: Dict[str, Any]) -> Optional[User]:
        """
        Update existing user with new information from Clerk.
        
        Args:
            user: Existing Django User instance
            user_info: Updated user information
            
        Returns:
            Updated User instance or None if update fails
        """
        try:
            updated = False
            
            # Update basic user fields
            updated |= self._update_basic_user_fields(user, user_info)
            
            # Update organization information
            updated |= self._update_user_organizations(user, user_info)
            
            if updated:
                user.save()
                self._log_user_update_success(user)
            else:
                self.logger.info(f"ℹ️  No updates needed for user: {user.username}")
            
            return user
            
        except Exception as save_error:
            self.logger.error(f"❌ Error saving user updates: {save_error}")
            # Refresh from database to ensure clean state
            user.refresh_from_db()
            return user
    
    def _update_basic_user_fields(self, user: User, user_info: Dict[str, Any]) -> bool:
        """
        Update basic user fields (email, username, names, clerk_user_id).
        
        Args:
            user: User instance to update
            user_info: User information dictionary
            
        Returns:
            True if any updates were made, False otherwise
        """
        updated = False
        
        # Update clerk_user_id if missing
        clerk_user_id = user_info.get('clerk_user_id')
        if clerk_user_id and (not user.clerk_user_id or user.clerk_user_id != clerk_user_id):
            self.logger.info(f"Updating clerk_user_id: {user.clerk_user_id} -> {clerk_user_id}")
            user.clerk_user_id = clerk_user_id
            updated = True
        
        # Update email with conflict resolution
        email = user_info.get('email')
        if email and user.email != email:
            if self._resolve_email_conflict(user, email):
                self.logger.info(f"Updating email: {user.email} -> {email}")
                user.email = email
                updated = True
        
        # Update username if available and unique
        username = user_info.get('username')
        if username and user.username != username:
            if not User.objects.filter(username=username).exclude(id=user.id).exists():
                self.logger.info(f"Updating username: {user.username} -> {username}")
                user.username = username
                updated = True
            else:
                self.logger.warning(f"⚠️  Username {username} already exists - keeping {user.username}")
        
        # Update first and last name
        first_name = user_info.get('first_name')
        if first_name is not None and user.first_name != first_name:
            self.logger.info(f"Updating first_name: '{user.first_name}' -> '{first_name}'")
            user.first_name = first_name
            updated = True
        
        last_name = user_info.get('last_name')
        if last_name is not None and user.last_name != last_name:
            self.logger.info(f"Updating last_name: '{user.last_name}' -> '{last_name}'")
            user.last_name = last_name
            updated = True
        
        return updated
    
    def _resolve_email_conflict(self, user: User, new_email: str) -> bool:
        """
        Resolve email conflicts by handling duplicate emails.
        
        Args:
            user: User instance being updated
            new_email: New email address
            
        Returns:
            True if conflict resolved and email can be updated, False otherwise
        """
        conflicting_user = User.objects.filter(email=new_email).exclude(id=user.id).first()
        
        if not conflicting_user:
            return True  # No conflict
        
        # Handle conflict with legacy user (no Clerk ID)
        if not conflicting_user.clerk_user_id:
            self.logger.warning(f"⚠️  Found duplicate user with email {new_email} - updating conflicting user")
            conflicting_user.email = f"old-{conflicting_user.id}-{new_email}"
            conflicting_user.save()
            self.logger.info(f"✅ Updated conflicting user email to: {conflicting_user.email}")
            return True
        else:
            self.logger.warning(
                f"⚠️  Cannot update email from {user.email} to {new_email} - "
                f"email already exists for another Clerk user"
            )
            return False
    
    def _update_user_organizations(self, user: User, user_info: Dict[str, Any]) -> bool:
        """
        Update user organization information.
        
        Args:
            user: User instance to update
            user_info: User information dictionary
            
        Returns:
            True if any updates were made, False otherwise
        """
        updated = False
        all_organizations = user_info.get('all_organizations', [])
        
        if all_organizations:
            # Update multiple organizations fields
            org_ids = [org['organization_id'] for org in all_organizations]
            org_names = [org['organization_name'] for org in all_organizations]
            org_roles = [org['organization_role'] for org in all_organizations]
            
            if user.organization_ids != org_ids:
                self.logger.info(f"Updating organization_ids: {user.organization_ids} -> {org_ids}")
                user.organization_ids = org_ids
                updated = True
            
            if user.organization_names != org_names:
                self.logger.info(f"Updating organization_names: {user.organization_names} -> {org_names}")
                user.organization_names = org_names
                updated = True
            
            if user.organization_roles != org_roles:
                self.logger.info(f"Updating organization_roles: {user.organization_roles} -> {org_roles}")
                user.organization_roles = org_roles
                updated = True
            
            # Update legacy fields with current organization from JWT
            org_id = user_info.get('organization_id')
            org_role = user_info.get('organization_role')
            org_slug = user_info.get('organization_slug')
            
            if org_id and user.organization_id != org_id:
                self.logger.info(f"Updating legacy organization_id: {user.organization_id} -> {org_id}")
                user.organization_id = org_id
                updated = True
            
            if org_role and user.organization_role != org_role:
                self.logger.info(f"Updating legacy organization_role: {user.organization_role} -> {org_role}")
                user.organization_role = org_role
                updated = True
            
            if org_slug and user.organization_name != org_slug:
                self.logger.info(f"Updating legacy organization_name: {user.organization_name} -> {org_slug}")
                user.organization_name = org_slug
                updated = True
        
        return updated
    
    @transaction.atomic
    def _create_new_user(self, user_info: Dict[str, Any]) -> Optional[User]:
        """
        Create a new Django user from Clerk information.
        
        Args:
            user_info: User information dictionary
            
        Returns:
            New User instance or None if creation fails
        """
        try:
            clerk_user_id = user_info.get('clerk_user_id')
            email = user_info.get('email', '')
            username = user_info.get('username')
            
            # Generate unique username
            display_username = self._generate_unique_username(username, email, clerk_user_id)
            
            # Prepare organization data
            all_organizations = user_info.get('all_organizations', [])
            org_ids = [org['organization_id'] for org in all_organizations]
            org_names = [org['organization_name'] for org in all_organizations]
            org_roles = [org['organization_role'] for org in all_organizations]
            
            # Log creation details
            creation_info = {
                'username': display_username,
                'email': email,
                'first_name': user_info.get('first_name', ''),
                'last_name': user_info.get('last_name', ''),
                'clerk_user_id': clerk_user_id,
                'organizations': org_names,
                'organization_ids': org_ids,
                'organization_roles': org_roles
            }
            self.log_debug_info("Creating New User", creation_info)
            
            # Create user
            user = User.objects.create_user(
                username=display_username,
                email=email,
                clerk_user_id=clerk_user_id,
                first_name=user_info.get('first_name', ''),
                last_name=user_info.get('last_name', ''),
                organization_ids=org_ids,
                organization_names=org_names,
                organization_roles=org_roles,
                # Legacy fields for backward compatibility
                organization_id=user_info.get('organization_id'),
                organization_name=user_info.get('organization_slug'),
                organization_role=user_info.get('organization_role'),
                is_active=True
            )
            
            self._log_user_creation_success(user)
            return user
            
        except Exception as e:
            self.logger.error(f"Error creating new user: {e}")
            return None
    
    def _generate_unique_username(self, username: Optional[str], email: str, clerk_user_id: str) -> str:
        """
        Generate a unique username for the user.
        
        Args:
            username: Preferred username
            email: User email address
            clerk_user_id: Clerk user ID
            
        Returns:
            Unique username string
        """
        # Determine base username
        if username:
            base_username = username
        elif email:
            base_username = email.split('@')[0]
        else:
            base_username = clerk_user_id
        
        # Ensure uniqueness
        display_username = base_username
        counter = 1
        
        while User.objects.filter(username=display_username).exists():
            display_username = f"{base_username}_{counter}"
            counter += 1
        
        return display_username
    
    def _log_user_update_success(self, user: User) -> None:
        """Log successful user update."""
        update_info = {
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'organization_id': user.organization_id,
            'organization_name': user.organization_name,
            'organization_role': user.organization_role
        }
        self.log_debug_info("Updated Existing User", update_info)
    
    def _log_user_creation_success(self, user: User) -> None:
        """Log successful user creation."""
        creation_info = {
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'clerk_user_id': user.clerk_user_id,
            'organization_id': user.organization_id,
            'organization_name': user.organization_name,
            'organization_role': user.organization_role
        }
        self.log_debug_info("Created New User", creation_info)
    
    def sync_user_with_clerk(self, user: User) -> bool:
        """
        Synchronize a Django user with latest Clerk data.
        
        Args:
            user: Django User instance to sync
            
        Returns:
            True if sync successful, False otherwise
        """
        if not user.clerk_user_id:
            self.logger.warning(f"User {user.username} has no Clerk user ID - cannot sync")
            return False
        
        try:
            # Fetch latest user info from Clerk
            api_user_info = self.api_service.get_user_info(user.clerk_user_id)
            if not api_user_info:
                self.logger.error(f"Could not fetch user info from Clerk for {user.clerk_user_id}")
                return False
            
            # Fetch organizations
            all_organizations = self.api_service.get_user_organizations(user.clerk_user_id)
            
            # Create enhanced user info
            enhanced_info = {
                'clerk_user_id': user.clerk_user_id,
                'all_organizations': all_organizations,
                **self._extract_api_user_info(api_user_info, {})
            }
            
            # Update user
            updated_user = self._update_existing_user(user, enhanced_info)
            return updated_user is not None
            
        except Exception as e:
            self.logger.error(f"Error syncing user {user.username} with Clerk: {e}")
            return False
