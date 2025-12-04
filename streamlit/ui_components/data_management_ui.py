"""
Unified Data Management UI Component for Streamlit Features
Provides read/delete operations for all features using existing API pattern
"""

import streamlit as st
import pandas as pd
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
import json

from api_client import APIClient


class DataManagementUI:
    """Unified data management UI component for all features"""
    
    def __init__(self, api_client: APIClient, feature_name: str):
        self.api = api_client
        self.feature_name = feature_name
        self._init_session_state()
    
    def _init_session_state(self):
        """Initialize session state for data management"""
        if f'{self.feature_name}_data' not in st.session_state:
            st.session_state[f'{self.feature_name}_data'] = []
        if f'{self.feature_name}_selected_items' not in st.session_state:
            st.session_state[f'{self.feature_name}_selected_items'] = []
    
    def render_data_management_tab(self):
        """Render the data management tab for any feature"""
        # Modern header with gradient background
        st.markdown("""
            <div style="
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 20px;
                border-radius: 10px;
                margin-bottom: 20px;
                color: white;
            ">
                <h2 style="margin: 0; color: white;">📊 {feature_name} Data Management</h2>
                <p style="margin: 5px 0 0 0; opacity: 0.9;">Manage and organize your {feature_name} data with modern tools</p>
            </div>
        """.replace("{feature_name}", self.feature_name.title()), unsafe_allow_html=True)
        
        # Modern action buttons with better styling
        st.markdown("### 🛠️ Quick Actions")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            if st.button("🔄 Refresh Data", key=f"refresh_{self.feature_name}", help="Reload data from server"):
                self.refresh_data()
        
        with col2:
            if st.button("📊 View Analytics", key=f"analytics_{self.feature_name}", help="View data analytics and insights"):
                self.show_analytics()
        
        with col3:
            if st.button("🗑️ Bulk Operations", key=f"bulk_delete_{self.feature_name}", help="Perform bulk operations on selected items"):
                self.show_bulk_delete()
        
        with col4:
            if st.button("📥 Export Data", key=f"export_{self.feature_name}", help="Export data in various formats"):
                self.show_export_options()
        
        with col5:
            if st.button("⚙️ Settings", key=f"settings_{self.feature_name}", help="Configure display settings"):
                self.show_settings()
        
        st.markdown("---")  # Separator
        
        # Load and display data
        self.load_and_display_data()
    
    def load_and_display_data(self):
        """Load and display data in a modern card-based UI"""
        try:
            # Get data from API
            data = self.get_data_from_api()
            
            if not data:
                st.info(f"No {self.feature_name} data found.")
                return
            
            # Store data in session state
            st.session_state[f'{self.feature_name}_data'] = data
            
            # Display header with count
            st.subheader(f"📊 {self.feature_name.title()} Data ({len(data)} items)")
            
            # Add search and filter functionality
            self.render_search_and_filters(data)
            
            # Display data in modern card format
            self.render_data_cards(data)
            
        except Exception as e:
            st.error(f"Error loading {self.feature_name} data: {str(e)}")
    
    def render_search_and_filters(self, data: List[Dict[str, Any]]):
        """Render search and filter controls"""
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            search_term = st.text_input(
                "🔍 Search",
                placeholder="Search by topic, content, or keywords...",
                key=f"search_{self.feature_name}",
                help="Filter data by searching in content"
            )
        
        with col2:
            sort_by = st.selectbox(
                "📅 Sort by",
                ["Created Date", "Updated Date", "Title", "Topic"],
                key=f"sort_{self.feature_name}"
            )
        
        with col3:
            sort_order = st.selectbox(
                "🔄 Order",
                ["Newest First", "Oldest First"],
                key=f"order_{self.feature_name}"
            )
        
        # Store filters in session state
        st.session_state[f'{self.feature_name}_search'] = search_term
        st.session_state[f'{self.feature_name}_sort'] = sort_by
        st.session_state[f'{self.feature_name}_order'] = sort_order
    
    def render_data_cards(self, data: List[Dict[str, Any]]):
        """Render data in modern card format"""
        # Apply search filter
        search_term = st.session_state.get(f'{self.feature_name}_search', '')
        filtered_data = self.filter_data(data, search_term)
        
        if not filtered_data:
            st.info("No data matches your search criteria.")
            return
        
        # Apply sorting
        sorted_data = self.sort_data(filtered_data)
        
        # Display cards in a grid
        self.display_cards_grid(sorted_data)
    
    def filter_data(self, data: List[Dict[str, Any]], search_term: str) -> List[Dict[str, Any]]:
        """Filter data based on search term"""
        if not search_term:
            return data
        
        search_lower = search_term.lower()
        filtered = []
        
        for item in data:
            # Search in common text fields
            searchable_fields = ['topic', 'title', 'content', 'post_content', 'keywords', 'username', 'organization_name']
            for field in searchable_fields:
                if field in item and item[field]:
                    if search_lower in str(item[field]).lower():
                        filtered.append(item)
                        break
        
        return filtered
    
    def sort_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sort data based on selected criteria"""
        sort_by = st.session_state.get(f'{self.feature_name}_sort', 'Created Date')
        sort_order = st.session_state.get(f'{self.feature_name}_order', 'Newest First')
        
        # Map sort options to actual field names
        sort_field_map = {
            'Created Date': 'created_at',
            'Updated Date': 'updated_at',
            'Title': 'title',
            'Topic': 'topic'
        }
        
        sort_field = sort_field_map.get(sort_by, 'created_at')
        reverse = sort_order == 'Newest First'
        
        # Sort the data
        try:
            sorted_data = sorted(data, key=lambda x: x.get(sort_field, ''), reverse=reverse)
        except (TypeError, ValueError):
            # If sorting fails, return original order
            sorted_data = data
        
        return sorted_data
    
    def display_cards_grid(self, data: List[Dict[str, Any]]):
        """Display data in a responsive card grid"""
        # Create a grid of cards
        cards_per_row = 2
        
        for i in range(0, len(data), cards_per_row):
            cols = st.columns(cards_per_row)
            
            for j, col in enumerate(cols):
                if i + j < len(data):
                    with col:
                        self.render_single_card(data[i + j], i + j)
    
    def render_single_card(self, item: Dict[str, Any], index: int):
        """Render a single data card"""
        with st.container():
            # Card container with custom styling
            st.markdown("""
                <div style="
                    border: 1px solid #e0e0e0;
                    border-radius: 10px;
                    padding: 20px;
                    margin: 10px 0;
                    background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                    transition: transform 0.2s ease;
                ">
            """, unsafe_allow_html=True)
            
            # Card header with title/topic
            title = item.get('title') or item.get('topic', 'Untitled')
            st.markdown(f"### 📝 {title}")
            
            # Card content
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # Display key information
                self.display_card_info(item)
            
            with col2:
                # Display action buttons
                self.display_card_actions(item, index)
            
            st.markdown("</div>", unsafe_allow_html=True)
    
    def display_card_info(self, item: Dict[str, Any]):
        """Display key information in the card"""
        # Organization info
        if 'organization_name' in item:
            st.markdown(f"**🏢 Organization:** {item['organization_name']}")
        
        # User info
        if 'username' in item:
            st.markdown(f"**👤 User:** {item['username']}")
        
        # Date info
        if 'created_at' in item:
            try:
                from datetime import datetime
                created_date = pd.to_datetime(item['created_at']).strftime('%Y-%m-%d %H:%M')
                st.markdown(f"**📅 Created:** {created_date}")
            except:
                st.markdown(f"**📅 Created:** {item['created_at']}")
        
        # Content preview
        content_fields = ['content', 'post_content', 'linkedin_post', 'text']
        content = None
        for field in content_fields:
            if field in item and item[field]:
                content = item[field]
                break
        
        if content:
            # Truncate content for preview
            preview = content[:150] + "..." if len(str(content)) > 150 else content
            st.markdown(f"**📄 Content:** {preview}")
    
    def display_card_actions(self, item: Dict[str, Any], index: int):
        """Display action buttons for the card"""
        st.markdown("**Actions:**")
        
        # Download button (PDF or MD depending on feature)
        if self.feature_name in ['upwork', 'blog']:
            download_label = "📥 MD"
            download_help = "Download as Markdown"
        else:
            download_label = "📥 PDF"
            download_help = "Download as PDF"
            
        if st.button(download_label, key=f"pdf_card_{index}", help=download_help):
            self.download_single_item_pdf(item)
        
        # Delete button
        if st.button("🗑️ Delete", key=f"delete_card_{index}", help="Delete this item", type="secondary"):
            self.delete_single_item(item)
    
    def show_card_details(self, item: Dict[str, Any]):
        """Show detailed view of a single item"""
        with st.expander(f"📄 Details for {item.get('title', item.get('topic', 'Item'))}", expanded=True):
            # Display all fields in a nice format
            for key, value in item.items():
                if value is not None and value != "":
                    st.markdown(f"**{key.replace('_', ' ').title()}:** {value}")
    
    def download_single_item_pdf(self, item: Dict[str, Any]):
        """Download file for a single item (PDF or MD depending on feature)"""
        item_id = item.get('id')
        if item_id:
            try:
                # Use the appropriate download method based on feature
                if self.feature_name == 'blog' and hasattr(self, 'download_md'):
                    self.download_md(item_id)
                elif hasattr(self, 'download_pdf'):
                    self.download_pdf(item_id)
                else:
                    # Fallback to API method
                    response = self.get_api_download_method(item_id)
                    
                    if response:
                        # Determine file type and MIME based on feature
                        if self.feature_name in ['upwork', 'blog']:
                            # For Upwork proposals and blog posts, download as MD
                            filename = f"{item.get('title', item.get('topic', 'Item')).replace(' ', '_')}_{item_id}.md"
                            mime_type = "text/markdown"
                            label = "📥 Download MD"
                        else:
                            # For other features, download as PDF
                            filename = f"{item.get('title', item.get('topic', 'Item')).replace(' ', '_')}_{item_id}.pdf"
                            mime_type = "application/pdf"
                            label = "📥 Download PDF"
                        
                        # Use Streamlit's download button to trigger the download
                        st.download_button(
                            label=label,
                            data=response,
                            file_name=filename,
                            mime=mime_type,
                            help=f"Download {filename.split('.')[-1].upper()} for {item.get('title', item.get('topic', 'Item'))}"
                        )
                        st.success(f"File ready for download: {filename}")
                    else:
                        st.error(f"Failed to generate file for {item.get('title', item.get('topic', 'Item'))}")
            except Exception as e:
                st.error(f"Error downloading file: {str(e)}")
    
    def download_single_item_images(self, item: Dict[str, Any]):
        """Download images for a single item"""
        if not self.supports_image_download():
            st.warning("Image download is not supported for this feature.")
            return
        
        item_id = item.get('id')
        if item_id:
            try:
                # Use the new download_images method if available
                if hasattr(self, 'download_images'):
                    self.download_images(item_id)
                else:
                    # Fallback to API method
                    if hasattr(self, 'get_image_download_method'):
                        response = self.get_image_download_method(item_id)
                    else:
                        endpoint = self.get_image_download_endpoint(item_id)
                        response = self.api.get(endpoint)
                    if response and response.get('success'):
                        st.success(f"Image download initiated for {item.get('title', item.get('topic', 'Item'))}")
                    else:
                        st.error(f"Failed to download images for {item.get('title', item.get('topic', 'Item'))}")
            except Exception as e:
                st.error(f"Error downloading images: {str(e)}")
    
    def delete_single_item(self, item: Dict[str, Any]):
        """Delete a single item"""
        item_id = item.get('id')
        if item_id:
            try:
                response = self.get_api_delete_method([item_id])
                if response and response.get('success'):
                    st.success(f"Successfully deleted {item.get('title', item.get('topic', 'Item'))}")
                    st.rerun()
                else:
                    st.error("Failed to delete item.")
            except Exception as e:
                st.error(f"Error deleting item: {str(e)}")
    
    def get_data_from_api(self) -> List[Dict[str, Any]]:
        """Get data from API - to be implemented by subclasses"""
        try:
            # Use the specific API method for this feature
            response = self.get_api_list_method()
            
            if response and response.get('success'):
                return response.get('data', [])
            else:
                st.error(f"Failed to load {self.feature_name} data.")
                return []
        except Exception as e:
            st.error(f"Error loading {self.feature_name} data: {str(e)}")
            return []
    
    def get_api_list_method(self):
        """Get the API list method for this feature - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement get_api_list_method")
    
    def get_api_delete_method(self, ids: List[int]):
        """Get the API delete method for this feature - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement get_api_delete_method")
    
    def get_api_download_method(self, item_id: int):
        """Get the API download method for this feature - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement get_api_download_method")
    
    def show_item_details(self, df):
        """Show details for selected items"""
        selected_items = df[df['Select'] == True]
        if selected_items.empty:
            st.warning("Please select items to view details.")
            return
        
        for idx, item in selected_items.iterrows():
            with st.expander(f"Details for {item.get('title', item.get('topic', 'Item'))}"):
                st.json(item.to_dict())
    
    def download_pdf(self, df):
        """Download PDF for selected items"""
        selected_items = df[df['Select'] == True]
        if selected_items.empty:
            st.warning("Please select items to download PDF.")
            return
        
        for idx, item in selected_items.iterrows():
            item_id = item.get('id')
            if item_id:
                try:
                    response = self.get_api_download_method(item_id)
                    if response and response.get('success'):
                        st.success(f"PDF download initiated for {item.get('title', item.get('topic', 'Item'))}")
                    else:
                        st.error(f"Failed to download PDF for {item.get('title', item.get('topic', 'Item'))}")
                except Exception as e:
                    st.error(f"Error downloading PDF: {str(e)}")
    
    def download_images(self, df):
        """Download images for selected items (if supported)"""
        if not self.supports_image_download():
            st.warning("Image download is not supported for this feature.")
            return
        
        selected_items = df[df['Select'] == True]
        if selected_items.empty:
            st.warning("Please select items to download images.")
            return
        
        for idx, item in selected_items.iterrows():
            item_id = item.get('id')
            if item_id:
                try:
                    if hasattr(self, 'get_image_download_method'):
                        response = self.get_image_download_method(item_id)
                    else:
                        # Fallback to generic method if not implemented
                        endpoint = self.get_image_download_endpoint(item_id)
                        response = self.api.get(endpoint)
                    if response and response.get('success'):
                        st.success(f"Image download initiated for {item.get('title', item.get('topic', 'Item'))}")
                    else:
                        st.error(f"Failed to download images for {item.get('title', item.get('topic', 'Item'))}")
                except Exception as e:
                    st.error(f"Error downloading images: {str(e)}")
    
    def supports_image_download(self) -> bool:
        """Check if this feature supports image download"""
        return False
    
    def get_image_download_endpoint(self, item_id: int) -> str:
        """Get the image download endpoint for this feature"""
        raise NotImplementedError("Subclasses must implement get_image_download_endpoint if they support image download")
    
    def delete_selected_items(self, df):
        """Delete selected items"""
        selected_items = df[df['Select'] == True]
        if selected_items.empty:
            st.warning("Please select items to delete.")
            return
        
        # Confirm deletion
        if st.button("Confirm Deletion", key=f"confirm_delete_{self.feature_name}"):
            item_ids = selected_items['id'].tolist()
            try:
                response = self.get_api_delete_method(item_ids)
                if response and response.get('success'):
                    st.success(f"Successfully deleted {len(item_ids)} items.")
                    st.rerun()
                else:
                    st.error("Failed to delete items.")
            except Exception as e:
                st.error(f"Error deleting items: {str(e)}")
    
    def refresh_data(self):
        """Refresh data from API"""
        st.rerun()
    
    def show_analytics(self):
        """Show analytics for this feature"""
        st.subheader(f"📊 {self.feature_name.title()} Analytics")
        
        try:
            data = st.session_state.get(f'{self.feature_name}_data', [])
            if not data:
                st.info("No data available for analytics.")
                return
            
            # Basic analytics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Items", len(data))
            
            with col2:
                # Count by organization
                orgs = set(item.get('organization_name', 'Unknown') for item in data)
                st.metric("Organizations", len(orgs))
            
            with col3:
                # Count by user
                users = set(item.get('username', 'Unknown') for item in data)
                st.metric("Users", len(users))
            
            with col4:
                # Recent items (last 7 days)
                from datetime import datetime, timedelta
                recent_count = 0
                week_ago = datetime.now() - timedelta(days=7)
                for item in data:
                    if 'created_at' in item:
                        try:
                            created_date = pd.to_datetime(item['created_at'])
                            if created_date >= week_ago:
                                recent_count += 1
                        except:
                            pass
                st.metric("Recent (7 days)", recent_count)
            
            # Charts
            st.subheader("📈 Data Distribution")
            
            # Organization distribution
            if len(orgs) > 1:
                org_counts = {}
                for item in data:
                    org = item.get('organization_name', 'Unknown')
                    org_counts[org] = org_counts.get(org, 0) + 1
                
                st.bar_chart(org_counts)
            
        except Exception as e:
            st.error(f"Error generating analytics: {str(e)}")
    
    def show_bulk_delete(self):
        """Show bulk delete options"""
        st.subheader(f"🗑️ Bulk Operations for {self.feature_name.title()}")
        
        data = st.session_state.get(f'{self.feature_name}_data', [])
        if not data:
            st.info("No data available for bulk operations.")
            return
        
        st.warning("⚠️ Bulk operations are powerful tools. Please use with caution.")
        
        # Selection options
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📋 Select Items")
            
            # Date range selection
            date_range = st.date_input("Select date range", value=None, key=f"bulk_date_range_{self.feature_name}")
            
            # Organization filter
            orgs = list(set(item.get('organization_name', 'Unknown') for item in data))
            selected_orgs = st.multiselect("Select organizations", orgs, key=f"bulk_orgs_{self.feature_name}")
            
            # User filter
            users = list(set(item.get('username', 'Unknown') for item in data))
            selected_users = st.multiselect("Select users", users, key=f"bulk_users_{self.feature_name}")
        
        with col2:
            st.subheader("⚡ Operations")
            
            operation = st.selectbox(
                "Choose operation",
                ["Delete Selected", "Export Selected", "Archive Selected"],
                key=f"bulk_operation_{self.feature_name}"
            )
            
            if st.button("🚀 Execute Operation", key=f"execute_bulk_{self.feature_name}"):
                self.execute_bulk_operation(operation, data, date_range, selected_orgs, selected_users)
    
    def execute_bulk_operation(self, operation, data, date_range, selected_orgs, selected_users):
        """Execute bulk operation on filtered data"""
        # Filter data based on selections
        filtered_data = data.copy()
        
        if date_range:
            # Filter by date range
            start_date, end_date = date_range
            filtered_data = [item for item in filtered_data 
                           if self.is_item_in_date_range(item, start_date, end_date)]
        
        if selected_orgs:
            filtered_data = [item for item in filtered_data 
                           if item.get('organization_name') in selected_orgs]
        
        if selected_users:
            filtered_data = [item for item in filtered_data 
                           if item.get('username') in selected_users]
        
        if not filtered_data:
            st.warning("No items match the selected criteria.")
            return
        
        st.info(f"Operation '{operation}' will be performed on {len(filtered_data)} items.")
        
        if operation == "Delete Selected":
            if st.button("⚠️ Confirm Deletion", key=f"confirm_bulk_delete_{self.feature_name}"):
                item_ids = [item['id'] for item in filtered_data if 'id' in item]
                try:
                    response = self.get_api_delete_method(item_ids)
                    if response and response.get('success'):
                        st.success(f"Successfully deleted {len(item_ids)} items.")
                        st.rerun()
                    else:
                        st.error("Failed to delete items.")
                except Exception as e:
                    st.error(f"Error deleting items: {str(e)}")
    
    def is_item_in_date_range(self, item, start_date, end_date):
        """Check if item is within date range"""
        if 'created_at' not in item:
            return False
        
        try:
            item_date = pd.to_datetime(item['created_at']).date()
            return start_date <= item_date <= end_date
        except:
            return False
    
    def show_export_options(self):
        """Show export options"""
        st.subheader(f"📥 Export {self.feature_name.title()} Data")
        
        data = st.session_state.get(f'{self.feature_name}_data', [])
        if not data:
            st.info("No data available for export.")
            return
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📋 Export Options")
            
            export_format = st.selectbox(
                "Export Format",
                ["CSV", "JSON", "Excel", "PDF Report"],
                key=f"export_format_{self.feature_name}"
            )
            
            include_fields = st.multiselect(
                "Select fields to include",
                self.get_available_fields(data),
                default=self.get_available_fields(data)[:5],  # Default to first 5 fields
                key=f"export_fields_{self.feature_name}"
            )
        
        with col2:
            st.subheader("🎯 Filter Options")
            
            # Date range
            date_range = st.date_input("Date range", value=None, key=f"export_date_range_{self.feature_name}")
            
            # Organization filter
            orgs = list(set(item.get('organization_name', 'Unknown') for item in data))
            selected_orgs = st.multiselect("Organizations", orgs, key=f"export_orgs_{self.feature_name}")
        
        if st.button("📥 Generate Export", key=f"generate_export_{self.feature_name}"):
            self.generate_export(data, export_format, include_fields, date_range, selected_orgs)
    
    def get_available_fields(self, data):
        """Get available fields from data"""
        if not data:
            return []
        
        all_fields = set()
        for item in data:
            all_fields.update(item.keys())
        
        return sorted(list(all_fields))
    
    def generate_export(self, data, format_type, fields, date_range, orgs):
        """Generate export file"""
        # Filter data
        filtered_data = data.copy()
        
        if date_range:
            start_date, end_date = date_range
            filtered_data = [item for item in filtered_data 
                           if self.is_item_in_date_range(item, start_date, end_date)]
        
        if orgs:
            filtered_data = [item for item in filtered_data 
                           if item.get('organization_name') in orgs]
        
        if not filtered_data:
            st.warning("No data matches the export criteria.")
            return
        
        # Filter fields
        if fields:
            filtered_data = [{k: v for k, v in item.items() if k in fields} for item in filtered_data]
        
        try:
            if format_type == "CSV":
                df = pd.DataFrame(filtered_data)
                csv = df.to_csv(index=False)
                st.download_button(
                    "📥 Download CSV",
                    csv,
                    f"{self.feature_name}_data.csv",
                    "text/csv",
                    key=f"download_csv_{self.feature_name}"
                )
            
            elif format_type == "JSON":
                import json
                json_data = json.dumps(filtered_data, indent=2, default=str)
                st.download_button(
                    "📥 Download JSON",
                    json_data,
                    f"{self.feature_name}_data.json",
                    "application/json",
                    key=f"download_json_{self.feature_name}"
                )
            
            elif format_type == "Excel":
                df = pd.DataFrame(filtered_data)
                # Create Excel file in memory
                from io import BytesIO
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name=f'{self.feature_name.title()} Data')
                excel_data = output.getvalue()
                
                st.download_button(
                    "📥 Download Excel",
                    excel_data,
                    f"{self.feature_name}_data.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"download_excel_{self.feature_name}"
                )
            
            st.success(f"Export ready! {len(filtered_data)} items will be exported.")
            
        except Exception as e:
            st.error(f"Error generating export: {str(e)}")
    
    def show_settings(self):
        """Show settings for data management"""
        st.subheader(f"⚙️ {self.feature_name.title()} Settings")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🎨 Display Settings")
            
            # Cards per row
            cards_per_row = st.slider(
                "Cards per row",
                min_value=1,
                max_value=4,
                value=2,
                key=f"cards_per_row_{self.feature_name}",
                help="Number of cards to display per row"
            )
            
            # Items per page
            items_per_page = st.slider(
                "Items per page",
                min_value=5,
                max_value=50,
                value=20,
                key=f"items_per_page_{self.feature_name}",
                help="Number of items to display per page"
            )
            
            # Show preview
            show_preview = st.checkbox(
                "Show content preview",
                value=True,
                key=f"show_preview_{self.feature_name}",
                help="Show content preview in cards"
            )
        
        with col2:
            st.subheader("🔍 Search Settings")
            
            # Search fields
            search_fields = st.multiselect(
                "Searchable fields",
                ['topic', 'title', 'content', 'username', 'organization_name'],
                default=['topic', 'title', 'content'],
                key=f"search_fields_{self.feature_name}",
                help="Fields to include in search"
            )
            
            # Case sensitive search
            case_sensitive = st.checkbox(
                "Case sensitive search",
                value=False,
                key=f"case_sensitive_{self.feature_name}",
                help="Make search case sensitive"
            )
        
        if st.button("💾 Save Settings", key=f"save_settings_{self.feature_name}"):
            st.success("Settings saved successfully!")
            st.rerun()
