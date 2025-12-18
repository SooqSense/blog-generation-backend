"""
Access Control Services Module

This module provides organization-based access control decorators and utilities
for Django views and API endpoints.

Available Components:
- decorators: Organization-based access control decorators
- require_organization_access: Function decorator for organization membership
- require_sooqsense_organization: Convenience decorator for sooqsense organization
- require_organization_admin_access: Decorator for organization admin access
- RequireOrganizationMixin: Class-based view mixin for organization access control
"""

from .decorators import (
    require_organization_access,
    require_sooqsense_organization,
    require_organization_admin_access,
    RequireOrganizationMixin,
    get_user_selected_organization,
    set_selected_organization_context,
    REQUIRED_ORGANIZATION
)

__all__ = [
    'require_organization_access',
    'require_sooqsense_organization',
    'require_organization_admin_access',
    'RequireOrganizationMixin',
    'get_user_selected_organization',
    'set_selected_organization_context',
    'REQUIRED_ORGANIZATION'
]

# Version information
__version__ = '1.0.0'
__author__ = 'AI Blog Generator Team'
