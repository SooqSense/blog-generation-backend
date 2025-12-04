"""
Organization Components Module
Handles organization selection and display in the sidebar
"""

import streamlit as st


class OrganizationComponents:
    """Components for organization management UI"""
    
    @staticmethod
    def render_organization_selector():
        """Render organization selector if user has multiple organizations"""
        if not st.session_state.get('authenticated', False):
            return
        
        user_orgs = st.session_state.get('user_organizations', [])
        user = st.session_state.get('user', {})
        
        if not user_orgs:
            return
        
        st.markdown("### 🏢 Organizations")
        
        selected_org = st.session_state.get('selected_organization')
        org_ids = user.get('organization_ids', [])
        org_roles = user.get('organization_roles', [])
        
        if len(user_orgs) > 1:
            OrganizationComponents._render_multi_org_selector(
                user_orgs, org_ids, org_roles, selected_org
            )
        else:
            OrganizationComponents._render_single_org_display(
                user_orgs[0], org_roles[0] if org_roles else user.get('organization_role', 'member')
            )
        
        # Show organization access status
        if selected_org:
            st.success("✅ Organization Access Available")
        else:
            st.warning("⚠️ No Organization Selected")
        
        st.markdown("---")
    
    @staticmethod
    def _render_multi_org_selector(user_orgs: list, org_ids: list, org_roles: list, selected_org: str):
        """Render selector for multiple organizations"""
        current_index = 0
        if selected_org and selected_org in user_orgs:
            current_index = user_orgs.index(selected_org)
        
        # Create display options with role info
        display_options = []
        for i, org in enumerate(user_orgs):
            role = org_roles[i] if i < len(org_roles) else 'member'
            role_display = role.split(':')[-1] if ':' in role else role
            display_options.append(f"{org} ({role_display})")
        
        selected_display = st.selectbox(
            "Select Active Organization:",
            display_options,
            index=current_index,
            key="sidebar_org_selector"
        )
        
        # Extract the org name from the display option
        new_org = user_orgs[display_options.index(selected_display)]
        
        if new_org != selected_org:
            st.session_state.selected_organization = new_org
            # Update user's current org info for backward compatibility
            idx = user_orgs.index(new_org)
            user = st.session_state.get('user', {})
            if idx < len(org_ids):
                user['organization_id'] = org_ids[idx]
                user['organization_name'] = new_org
            if idx < len(org_roles):
                user['organization_role'] = org_roles[idx]
            st.session_state.user = user
            st.rerun()
        
        st.caption(f"You belong to {len(user_orgs)} organization(s)")
    
    @staticmethod
    def _render_single_org_display(org_name: str, org_role: str):
        """Render display for single organization"""
        role_display = org_role.split(':')[-1] if ':' in org_role else org_role
        st.info(f"📍 {org_name}")
        st.caption(f"Role: {role_display}")

