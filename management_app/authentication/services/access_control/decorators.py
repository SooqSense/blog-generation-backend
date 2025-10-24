"""
Organization-based access control decorators for Django views.
"""
import logging
from functools import wraps
from django.http import JsonResponse
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)

# Configuration: Organization name that has access to all features
REQUIRED_ORGANIZATION = "sooqsense"


def require_organization_access(organization_name=None):
    """
    Decorator to restrict access to users who are members of any organization.
    
    Usage:
        @require_organization_access()  # Requires any organization membership
        @require_organization_access('specific-org')  # Requires specific organization
        def my_view(request):
            ...
    
    This decorator checks if the authenticated user is a member of any organization.
    If organization_name is provided, it checks for that specific organization.
    If not, it allows access to any organization member.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            # Check if user is authenticated
            if not hasattr(request, 'user') or not request.user.is_authenticated:
                logger.warning(f"Unauthenticated access attempt to {view_func.__name__}")
                return Response({
                    'error': 'Authentication required',
                    'detail': 'You must be authenticated to access this feature.'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            user = request.user
            
            # If no specific organization is required, just check if user has any organization
            if organization_name is None:
                # Check if user is a member of any organization
                if not user.organization_names or len(user.organization_names) == 0:
                    logger.warning(
                        f"Access denied for user {user.username} (ID: {user.id}) to {view_func.__name__}. "
                        f"User is not a member of any organization."
                    )
                    return Response({
                        'error': 'Access forbidden',
                        'detail': 'Access to this feature requires membership in an organization.',
                        'user_organizations': user.organization_names or []
                    }, status=status.HTTP_403_FORBIDDEN)
                
                # Get the selected organization from request headers
                selected_org = request.META.get('HTTP_X_SELECTED_ORGANIZATION')
                if selected_org:
                    # Verify that the selected organization is one the user belongs to
                    if not user.is_member_of_organization(selected_org):
                        logger.warning(
                            f"Organization mismatch for user {user.username} (ID: {user.id}). "
                            f"Selected: {selected_org}, User organizations: {user.organization_names}"
                        )
                        return Response({
                            'error': 'Organization mismatch',
                            'detail': f'You are not a member of the "{selected_org}" organization.',
                            'selected_organization': selected_org,
                            'user_organizations': user.organization_names or []
                        }, status=status.HTTP_403_FORBIDDEN)
                    
                    logger.info(
                        f"User {user.username} (ID: {user.id}) accessing {view_func.__name__} "
                        f"with organization: {selected_org}"
                    )
                else:
                    logger.info(
                        f"User {user.username} (ID: {user.id}) accessing {view_func.__name__} "
                        f"(member of organizations: {user.organization_names})"
                    )
            else:
                # Check if user is a member of the specific required organization
                if not user.is_member_of_organization(organization_name):
                    logger.warning(
                        f"Access denied for user {user.username} (ID: {user.id}) to {view_func.__name__}. "
                        f"User is not a member of '{organization_name}' organization. "
                        f"User organizations: {user.organization_names}"
                    )
                    return Response({
                        'error': 'Access forbidden',
                        'detail': f'Access to this feature requires membership in the "{organization_name}" organization.',
                        'required_organization': organization_name,
                        'user_organizations': user.organization_names or []
                    }, status=status.HTTP_403_FORBIDDEN)
                
                # Get the selected organization from request headers (optional)
                selected_org = request.META.get('HTTP_X_SELECTED_ORGANIZATION')
                if selected_org:
                    # Verify that the selected organization matches the required one
                    if selected_org.lower() != organization_name.lower():
                        logger.warning(
                            f"Organization mismatch for user {user.username} (ID: {user.id}). "
                            f"Selected: {selected_org}, Required: {organization_name}"
                        )
                        return Response({
                            'error': 'Organization mismatch',
                            'detail': f'Please switch to the "{organization_name}" organization to access this feature.',
                            'selected_organization': selected_org,
                            'required_organization': organization_name
                        }, status=status.HTTP_403_FORBIDDEN)
                    
                    logger.info(
                        f"User {user.username} (ID: {user.id}) accessing {view_func.__name__} "
                        f"with organization: {selected_org}"
                    )
                else:
                    logger.info(
                        f"User {user.username} (ID: {user.id}) accessing {view_func.__name__} "
                        f"(member of '{organization_name}' organization)"
                    )
            
            # User has access, proceed with the view
            return view_func(request, *args, **kwargs)
        
        return wrapped_view
    return decorator


def require_sooqsense_organization(view_func):
    """
    Convenience decorator that requires 'sooqsense' organization membership.
    
    Usage:
        @require_sooqsense_organization
        def my_view(request):
            ...
    """
    return require_organization_access(REQUIRED_ORGANIZATION)(view_func)


def require_organization_admin_access(view_func):
    """
    Decorator to restrict access to organization admins only.
    This decorator allows access to any organization admin, not just sooqsense.
    
    Usage:
        @require_organization_admin_access
        def my_view(request):
            ...
    """
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        # Check if user is authenticated
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            logger.warning(f"Unauthenticated access attempt to {view_func.__name__}")
            return Response({
                'error': 'Authentication required',
                'detail': 'You must be authenticated to access this feature.'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        user = request.user
        
        # Get the selected organization from request headers
        selected_org = request.META.get('HTTP_X_SELECTED_ORGANIZATION')
        if not selected_org:
            logger.warning(f"No organization selected for user {user.username} (ID: {user.id})")
            return Response({
                'error': 'Organization selection required',
                'detail': 'Please select an organization to access this feature.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if user is a member of the selected organization
        if not user.is_member_of_organization(selected_org):
            logger.warning(
                f"Access denied for user {user.username} (ID: {user.id}) to {view_func.__name__}. "
                f"User is not a member of '{selected_org}' organization. "
                f"User organizations: {user.organization_names}"
            )
            return Response({
                'error': 'Access forbidden',
                'detail': f'You are not a member of the "{selected_org}" organization.',
                'selected_organization': selected_org,
                'user_organizations': user.organization_names or []
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Check if user is admin of the selected organization
        user_role = user.get_organization_role(selected_org)
        if not user_role or not _is_admin_role(user_role):
            logger.warning(
                f"Access denied for user {user.username} (ID: {user.id}) to {view_func.__name__}. "
                f"User role '{user_role}' is not admin in '{selected_org}' organization."
            )
            return Response({
                'error': 'Admin privileges required',
                'detail': f'Only administrators of the "{selected_org}" organization can access this feature.',
                'selected_organization': selected_org,
                'user_role': user_role
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Set organization context for the view
        request.selected_organization = selected_org
        request.organization_id = _get_organization_id(user, selected_org)
        
        logger.info(
            f"Admin access granted to user {user.username} (ID: {user.id}) for {view_func.__name__} "
            f"in organization: {selected_org}"
        )
        
        # User has admin access, proceed with the view
        return view_func(request, *args, **kwargs)
    
    return wrapped_view


def _is_admin_role(role: str) -> bool:
    """Check if the role indicates admin privileges."""
    if not role:
        return False
    
    role_lower = role.lower().strip()
    # Handle various admin role formats
    return (
        role_lower == 'admin' or 
        role_lower == 'org:admin' or 
        role_lower.endswith(':admin') or
        role_lower == 'organization_admin'
    )


def _get_organization_id(user, organization_name: str) -> str:
    """Get the organization ID for the given organization name."""
    if not user.organization_names or not user.organization_ids:
        return None
    
    try:
        # Find index of organization
        org_index = next(
            (i for i, org in enumerate(user.organization_names) if org.lower() == organization_name.lower()),
            None
        )
        if org_index is not None and org_index < len(user.organization_ids):
            return user.organization_ids[org_index]
    except (ValueError, IndexError):
        pass
    return None


def get_user_selected_organization(request):
    """
    Get the organization currently selected by the user from request headers.
    
    Returns:
        str: The selected organization name, or None if not set
    """
    return request.META.get('HTTP_X_SELECTED_ORGANIZATION')


def set_selected_organization_context(request, organization_name):
    """
    Helper function to set the selected organization in request context.
    This can be used in middleware or custom authentication.
    
    Args:
        request: The Django request object
        organization_name: The organization name to set
    """
    request.selected_organization = organization_name
    logger.debug(f"Set selected organization to: {organization_name}")


# Class-based view mixin
from django.utils.decorators import method_decorator


class RequireOrganizationMixin:
    """
    Mixin for class-based views to require organization membership.
    
    Usage:
        class MyView(RequireOrganizationMixin, generics.ListCreateAPIView):
            required_organization = 'sooqsense'  # Optional, defaults to REQUIRED_ORGANIZATION
            ...
    """
    required_organization = REQUIRED_ORGANIZATION
    
    @method_decorator(require_sooqsense_organization)
    def dispatch(self, request, *args, **kwargs):
        """Override dispatch to apply organization check"""
        return super().dispatch(request, *args, **kwargs)

