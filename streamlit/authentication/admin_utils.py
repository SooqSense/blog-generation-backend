"""
Admin utilities for checking user permissions from Clerk metadata
"""
import streamlit as st
from typing import Optional, Dict, Any

def is_user_admin() -> bool:
    """
    Check if the current user is an admin based on Clerk permissions
    
    Returns:
        True if user has admin permissions, False otherwise
    """
    try:
        user_data = st.session_state.get('user_data', {})
        
        # Check Clerk permissions first
        permissions = user_data.get('permissions', 'user')
        is_admin = user_data.get('is_admin', False)
        
        # Admin if permissions is 'admin' or is_admin is True
        return permissions == 'admin' or is_admin
    except Exception:
        return False

def get_user_permissions() -> Dict[str, Any]:
    """
    Get detailed user permissions information
    
    Returns:
        Dict with permission details
    """
    try:
        user_data = st.session_state.get('user_data', {})
        return {
            'permissions': user_data.get('permissions', 'user'),
            'is_admin': user_data.get('is_admin', False),
            'is_staff': user_data.get('is_staff', False),
            'is_superuser': user_data.get('is_superuser', False),
            'is_active': user_data.get('is_active', False),
            'public_metadata': user_data.get('public_metadata', {}),
            'user_id': user_data.get('django_user_id'),
            'clerk_user_id': user_data.get('clerk_user_id'),
            'email': user_data.get('email')
        }
    except Exception:
        return {
            'permissions': 'user',
            'is_admin': False,
            'is_staff': False,
            'is_superuser': False,
            'is_active': False,
            'public_metadata': {},
            'user_id': None,
            'clerk_user_id': None,
            'email': None
        }

def require_admin(feature_name: str = "this feature"):
    """
    Require admin access for a feature
    
    Args:
        feature_name: Name of the feature requiring admin access
    """
    if not is_user_admin():
        st.error(f"🔒 Admin access required for {feature_name}")
        st.info("You need admin permissions to access this feature.")
        return False
    return True

def display_admin_badge():
    """
    Display admin badge in the UI
    """
    if is_user_admin():
        st.success("👑 Admin Access")
        return True
    return False

def display_user_permissions():
    """
    Display user permissions in the UI
    """
    permissions = get_user_permissions()
    
    st.markdown("### 🔐 User Permissions")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Clerk Permissions:**")
        st.code(f"permissions: {permissions['permissions']}")
        
        if permissions['is_admin']:
            st.success("👑 Admin User")
        else:
            st.info("👤 Regular User")
    
    with col2:
        st.markdown("**Database Permissions:**")
        st.code(f"is_staff: {permissions['is_staff']}")
        st.code(f"is_superuser: {permissions['is_superuser']}")
        st.code(f"is_active: {permissions['is_active']}")
    
    if permissions['public_metadata']:
        st.markdown("**Public Metadata:**")
        st.json(permissions['public_metadata'])
    
    # Add refresh button to force fresh Clerk API call
    st.markdown("---")
    if st.button("🔄 Refresh Metadata from Clerk", help="Force fetch fresh metadata from Clerk API"):
        # Clear all session data
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()  # Restart the app