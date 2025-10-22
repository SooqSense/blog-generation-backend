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


def require_organization_access(organization_name=REQUIRED_ORGANIZATION):
    """
    Decorator to restrict access to users who are members of a specific organization.
    
    Usage:
        @require_organization_access()  # Requires 'sooqsense' organization
        @require_organization_access('custom-org')  # Requires 'custom-org' organization
        def my_view(request):
            ...
    
    This decorator checks if the authenticated user is a member of the specified organization.
    If not, it returns a 403 Forbidden response.
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
            
            # Check if user is a member of the required organization
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

