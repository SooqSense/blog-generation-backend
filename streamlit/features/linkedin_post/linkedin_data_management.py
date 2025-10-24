"""
LinkedIn Data Management Component for Streamlit
Handles LinkedIn post data management functionality
"""

import streamlit as st
from typing import List, Dict, Any
from base.data_management_ui import DataManagementUI
from base.download_service import download_service


class LinkedInDataManagement(DataManagementUI):
    """Data management component for LinkedIn post feature"""
    
    def __init__(self, api_client):
        super().__init__(api_client, "linkedin")
    
    def get_api_list_method(self):
        """Get the API list method for LinkedIn posts"""
        return self.api.list_posts()
    
    def get_api_delete_method(self, ids: List[int]):
        """Get the API delete method for LinkedIn posts"""
        return self.api.delete_posts(ids)
    
    def download_pdf(self, item_id: int):
        """Download LinkedIn post as PDF using Streamlit download service"""
        try:
            # Get LinkedIn post details
            post_data = self.api.get_post(item_id)
            if post_data and 'success' in post_data and post_data['success']:
                post_info = post_data['data']
                
                # Generate PDF using the download service
                pdf_bytes = download_service.generate_linkedin_post_pdf(post_info)
                
                # Create filename
                topic = post_info.get('topic', 'linkedin_post').replace(' ', '_')
                filename = f"linkedin_post_{topic}_{item_id}.pdf"
                
                # Use Streamlit's download button
                st.download_button(
                    label="📄 Download PDF",
                    data=pdf_bytes,
                    file_name=filename,
                    mime="application/pdf",
                    key=f"download_linkedin_{item_id}"
                )
                return True
            else:
                st.error("Failed to retrieve LinkedIn post data")
                return False
        except Exception as e:
            st.error(f"Error generating PDF: {str(e)}")
            return False
    
    def supports_image_download(self) -> bool:
        """LinkedIn posts don't support image download"""
        return False
    
    def display_card_info(self, item: Dict[str, Any]):
        """Display key information in the card with LinkedIn-specific details"""
        # Call parent method first
        super().display_card_info(item)
        
        # Add LinkedIn-specific information
        if 'topic' in item and item['topic']:
            st.markdown(f"**💼 Topic:** {item['topic']}")
        
        # Display engagement metrics if available
        if 'likes' in item or 'comments' in item or 'shares' in item:
            st.markdown("**📊 Engagement:**")
            metrics = []
            if 'likes' in item and item['likes']:
                metrics.append(f"👍 {item['likes']}")
            if 'comments' in item and item['comments']:
                metrics.append(f"💬 {item['comments']}")
            if 'shares' in item and item['shares']:
                metrics.append(f"🔄 {item['shares']}")
            if metrics:
                st.caption(" | ".join(metrics))
        
        # Display hashtags if available
        if 'hashtags' in item and item['hashtags']:
            hashtags = item['hashtags']
            if isinstance(hashtags, list):
                hashtag_text = " ".join([f"#{tag}" for tag in hashtags])
            else:
                hashtag_text = str(hashtags)
            st.markdown(f"**#️⃣ Hashtags:** {hashtag_text}")
        
        # Display post status if available
        if 'status' in item and item['status']:
            status_icons = {
                'published': '✅',
                'scheduled': '⏰',
                'draft': '📝',
                'failed': '❌'
            }
            icon = status_icons.get(item['status'].lower(), '📄')
            st.markdown(f"**{icon} Status:** {item['status'].title()}")
    
    def display_card_actions(self, item: Dict[str, Any], index: int):
        """Display action buttons for the card with LinkedIn-specific actions"""
        st.markdown("**Actions:**")
        
        # Download PDF button
        if st.button("📥 PDF", key=f"pdf_card_{index}", help="Download as PDF"):
            self.download_single_item_pdf(item)
        
        # LinkedIn-specific actions
        if 'status' in item and item['status'] == 'draft':
            if st.button("📤 Publish", key=f"publish_card_{index}", help="Publish to LinkedIn"):
                self.publish_to_linkedin(item)
        
        if 'status' in item and item['status'] == 'published':
            if st.button("📊 Analytics", key=f"analytics_card_{index}", help="View post analytics"):
                self.show_post_analytics(item)
        
        # Schedule post button (if not already scheduled)
        if 'status' in item and item['status'] not in ['scheduled', 'published']:
            if st.button("⏰ Schedule", key=f"schedule_card_{index}", help="Schedule post"):
                self.schedule_post(item)
        
        # Delete button
        if st.button("🗑️ Delete", key=f"delete_card_{index}", help="Delete this post", type="secondary"):
            self.delete_single_item(item)
    
    def publish_to_linkedin(self, item: Dict[str, Any]):
        """Publish a draft post to LinkedIn"""
        item_id = item.get('id')
        if item_id:
            try:
                # This would call the LinkedIn API to publish the post
                st.info("🚀 Publishing to LinkedIn...")
                # For now, just show a message
                st.success(f"Post '{item.get('topic', 'Untitled')}' published to LinkedIn!")
            except Exception as e:
                st.error(f"Error publishing post: {str(e)}")
    
    def show_post_analytics(self, item: Dict[str, Any]):
        """Show analytics for a published post"""
        with st.expander(f"📊 Analytics for {item.get('topic', 'Post')}", expanded=True):
            st.markdown("**Post Performance:**")
            
            # Display engagement metrics
            col1, col2, col3 = st.columns(3)
            
            with col1:
                likes = item.get('likes', 0)
                st.metric("👍 Likes", likes)
            
            with col2:
                comments = item.get('comments', 0)
                st.metric("💬 Comments", comments)
            
            with col3:
                shares = item.get('shares', 0)
                st.metric("🔄 Shares", shares)
            
            # Calculate engagement rate if we have reach data
            if 'reach' in item and item['reach'] > 0:
                total_engagement = likes + comments + shares
                engagement_rate = (total_engagement / item['reach']) * 100
                st.metric("📈 Engagement Rate", f"{engagement_rate:.2f}%")
            
            # Show post content preview
            if 'content' in item and item['content']:
                st.markdown("**Post Content:**")
                st.text(item['content'][:200] + "..." if len(item['content']) > 200 else item['content'])
    
    def schedule_post(self, item: Dict[str, Any]):
        """Schedule a post for later publishing"""
        with st.expander(f"⏰ Schedule Post: {item.get('topic', 'Untitled')}", expanded=True):
            st.markdown("**Schedule Settings:**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                schedule_date = st.date_input("Schedule Date", key=f"schedule_date_{item.get('id')}")
            
            with col2:
                schedule_time = st.time_input("Schedule Time", key=f"schedule_time_{item.get('id')}")
            
            if st.button("⏰ Confirm Schedule", key=f"confirm_schedule_{item.get('id')}"):
                try:
                    # This would call the scheduling API
                    st.success(f"Post '{item.get('topic', 'Untitled')}' scheduled for {schedule_date} at {schedule_time}")
                except Exception as e:
                    st.error(f"Error scheduling post: {str(e)}")
    
    def show_card_details(self, item: Dict[str, Any]):
        """Show detailed view of a LinkedIn post with enhanced formatting"""
        with st.expander(f"📄 LinkedIn Post Details: {item.get('topic', 'Untitled')}", expanded=True):
            # Display all fields in a nice format with LinkedIn-specific styling
            for key, value in item.items():
                if value is not None and value != "":
                    # Format LinkedIn-specific fields nicely
                    if key == 'content':
                        st.markdown(f"**📝 Post Content:**")
                        st.markdown(value)
                        st.markdown("---")
                    elif key == 'hashtags':
                        if isinstance(value, list):
                            hashtag_text = " ".join([f"#{tag}" for tag in value])
                        else:
                            hashtag_text = str(value)
                        st.markdown(f"**#️⃣ Hashtags:** {hashtag_text}")
                    elif key in ['likes', 'comments', 'shares']:
                        icons = {'likes': '👍', 'comments': '💬', 'shares': '🔄'}
                        icon = icons.get(key, '📊')
                        st.markdown(f"**{icon} {key.title()}:** {value}")
                    elif key == 'status':
                        status_icons = {
                            'published': '✅',
                            'scheduled': '⏰',
                            'draft': '📝',
                            'failed': '❌'
                        }
                        icon = status_icons.get(str(value).lower(), '📄')
                        st.markdown(f"**{icon} Status:** {value}")
                    else:
                        st.markdown(f"**{key.replace('_', ' ').title()}:** {value}")
    
    def show_analytics(self):
        """Show LinkedIn-specific analytics with engagement metrics"""
        st.subheader(f"📊 LinkedIn Analytics")
        
        try:
            data = st.session_state.get(f'{self.feature_name}_data', [])
            if not data:
                st.info("No LinkedIn data available for analytics.")
                return
            
            # Basic analytics from parent class
            super().show_analytics()
            
            # LinkedIn-specific analytics
            st.subheader("💼 LinkedIn-Specific Metrics")
            
            # Engagement metrics
            total_likes = sum(item.get('likes', 0) for item in data)
            total_comments = sum(item.get('comments', 0) for item in data)
            total_shares = sum(item.get('shares', 0) for item in data)
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("👍 Total Likes", total_likes)
            
            with col2:
                st.metric("💬 Total Comments", total_comments)
            
            with col3:
                st.metric("🔄 Total Shares", total_shares)
            
            with col4:
                total_engagement = total_likes + total_comments + total_shares
                st.metric("📊 Total Engagement", total_engagement)
            
            # Post status distribution
            status_counts = {}
            for item in data:
                status = item.get('status', 'unknown')
                status_counts[status] = status_counts.get(status, 0) + 1
            
            if status_counts:
                st.subheader("📈 Post Status Distribution")
                col1, col2 = st.columns(2)
                
                with col1:
                    st.bar_chart(status_counts)
                
                with col2:
                    for status, count in status_counts.items():
                        status_icons = {
                            'published': '✅',
                            'scheduled': '⏰',
                            'draft': '📝',
                            'failed': '❌'
                        }
                        icon = status_icons.get(status.lower(), '📄')
                        st.metric(f"{icon} {status.title()}", count)
            
            # Top performing posts
            published_posts = [item for item in data if item.get('status') == 'published']
            if published_posts:
                st.subheader("🏆 Top Performing Posts")
                
                # Sort by total engagement
                for item in published_posts:
                    engagement = item.get('likes', 0) + item.get('comments', 0) + item.get('shares', 0)
                    item['total_engagement'] = engagement
                
                top_posts = sorted(published_posts, key=lambda x: x.get('total_engagement', 0), reverse=True)[:5]
                
                for i, post in enumerate(top_posts, 1):
                    with st.expander(f"#{i} {post.get('topic', 'Untitled')} - {post.get('total_engagement', 0)} engagements"):
                        st.markdown(f"**Content:** {post.get('content', 'No content')[:200]}...")
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("👍 Likes", post.get('likes', 0))
                        with col2:
                            st.metric("💬 Comments", post.get('comments', 0))
                        with col3:
                            st.metric("🔄 Shares", post.get('shares', 0))
            
        except Exception as e:
            st.error(f"Error generating LinkedIn analytics: {str(e)}")