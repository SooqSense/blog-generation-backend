import requests
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
import urllib.parse
import time
import re

# Selenium imports for scraping functionality
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

logger = logging.getLogger(__name__)


class LinkedInAnalyticsService:
    """
    Service for fetching LinkedIn analytics data using access tokens.
    
    Now optimized for apps with w_member_social scope which provides access to:
    - User's posts, comments, and reactions
    - Social activity data
    - Enhanced profile information
    """
    
    BASE_URL = "https://api.linkedin.com"
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'X-Restli-Protocol-Version': '2.0.0',
            'LinkedIn-Version': '202505'  # Use latest version
        }
        self.available_scopes = self._detect_available_scopes()
    
    def _detect_available_scopes(self) -> List[str]:
        """
        Detect which scopes are available by testing API endpoints.
        This helps optimize which endpoints to use.
        """
        scopes = ['openid', 'profile', 'email']  # Basic scopes
        
        try:
            # Test for w_member_social scope by trying posts endpoint
            url = f"{self.BASE_URL}/rest/posts"
            params = {'q': 'author', 'author': 'urn:li:person:test', 'count': 1}
            headers = self.headers.copy()
            headers['X-RestLi-Method'] = 'FINDER'
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            if response.status_code != 403:  # If not forbidden, we likely have the scope
                scopes.append('w_member_social')
                logger.info("Detected w_member_social scope - enhanced social data access available")
            
        except:
            pass
        
        logger.info(f"Detected scopes: {scopes}")
        return scopes
    
    def get_profile_info(self) -> Dict:
        """
        Fetch comprehensive profile information using available scopes.
        """
        try:
            profile_data = {}
            
            # Method 1: Try userinfo endpoint (works with openid scope)
            url = f"{self.BASE_URL}/v2/userinfo"
            logger.info(f"Fetching profile info from: {url}")
            
            response = requests.get(url, headers=self.headers, timeout=30)
            logger.info(f"Userinfo API response status: {response.status_code}")
            
            if response.status_code == 200:
                userinfo_data = response.json()
                profile_data.update(userinfo_data)
                logger.info(f"Successfully fetched userinfo for: {userinfo_data.get('sub', 'unknown')}")
            
            # Method 2: Try /me endpoint for additional profile details
            url = f"{self.BASE_URL}/v2/me"
            response = requests.get(url, headers=self.headers, timeout=30)
            logger.info(f"Profile /me API response status: {response.status_code}")
            
            if response.status_code == 200:
                me_data = response.json()
                profile_data.update(me_data)
                logger.info("Successfully fetched detailed profile data")
            
            # Method 3: If we have w_member_social, try to get enhanced profile data
            if 'w_member_social' in self.available_scopes:
                url = f"{self.BASE_URL}/v2/people/(id:{profile_data.get('id', profile_data.get('sub', ''))})"
                response = requests.get(url, headers=self.headers, timeout=30)
                
                if response.status_code == 200:
                    enhanced_data = response.json()
                    profile_data.update(enhanced_data)
                    logger.info("Successfully fetched enhanced profile data with w_member_social scope")
            
            if not profile_data:
                logger.error("Failed to fetch any profile information")
                return {}
            
            return profile_data
                
        except requests.exceptions.Timeout:
            logger.error("LinkedIn API request timed out")
            return {}
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error while fetching profile info: {e}")
            return {}
        except Exception as e:
            logger.error(f"Unexpected error fetching profile info: {str(e)}")
            return {}
    
    def get_user_posts(self, profile_id: str) -> List[Dict]:
        """
        Fetch user's posts using the most appropriate endpoint based on available scopes.
        With w_member_social scope, we should have full access to posts data.
        """
        try:
            posts = []
            
            # Method 1: Use REST Posts API (requires w_member_social)
            if 'w_member_social' in self.available_scopes:
                posts = self._fetch_posts_with_member_social(profile_id)
                if posts:
                    logger.info(f"Successfully fetched {len(posts)} posts using w_member_social scope")
                    return posts
            
            # Method 2: Try alternative endpoints
            posts = self._try_alternative_posts_fetch(profile_id)
            
            return posts
                
        except Exception as e:
            logger.error(f"Error fetching posts: {str(e)}")
            return []
    
    def _fetch_posts_with_member_social(self, profile_id: str) -> List[Dict]:
        """
        Fetch posts using the REST API with w_member_social scope.
        This should provide the most comprehensive posts data.
        """
        try:
            person_urn = f"urn:li:person:{profile_id}"
            encoded_urn = urllib.parse.quote(person_urn, safe='')
            
            url = f"{self.BASE_URL}/rest/posts"
            params = {
                'q': 'author',
                'author': encoded_urn,
                'count': 50,
                'sortBy': 'LAST_MODIFIED'
            }
            
            headers = self.headers.copy()
            headers['X-RestLi-Method'] = 'FINDER'
            
            logger.info(f"Fetching posts with w_member_social scope from: {url}")
            logger.info(f"Params: {params}")
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            logger.info(f"Posts API response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                posts = data.get('elements', [])
                logger.info(f"Successfully fetched {len(posts)} posts with full social scope")
                
                # Log sample post structure for debugging
                if posts:
                    sample_post = posts[0]
                    logger.debug(f"Sample post keys: {list(sample_post.keys())}")
                
                return posts
            else:
                logger.warning(f"Posts API failed: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Error in _fetch_posts_with_member_social: {str(e)}")
            return []
    
    def _try_alternative_posts_fetch(self, profile_id: str) -> List[Dict]:
        """
        Try alternative methods to fetch posts or post-related data.
        """
        try:
            logger.info("Trying alternative posts fetch methods...")
            
            # Method 1: Try to get shares/activities
            url = f"{self.BASE_URL}/v2/shares"
            params = {
                'q': 'owners',
                'owners': f'urn:li:person:{profile_id}',
                'count': 50
            }
            
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            logger.info(f"Shares API response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                shares = data.get('elements', [])
                logger.info(f"Successfully fetched {len(shares)} shares via alternative method")
                return shares
            
            # Method 2: Try UGC posts endpoint
            url = f"{self.BASE_URL}/v2/ugcPosts"
            params = {
                'q': 'authors',
                'authors': f'urn:li:person:{profile_id}',
                'count': 50
            }
            
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            logger.info(f"UGC Posts API response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                ugc_posts = data.get('elements', [])
                logger.info(f"Successfully fetched {len(ugc_posts)} UGC posts via alternative method")
                return ugc_posts
            
            logger.warning("All alternative post fetch methods failed")
            return []
            
        except Exception as e:
            logger.error(f"Error in alternative posts fetch: {str(e)}")
            return []
    
    def get_post_analytics(self, post_urn: str) -> Dict:
        """
        Fetch comprehensive analytics for a specific post.
        With w_member_social scope, we should have access to detailed engagement data.
        """
        try:
            analytics_data = {}
            
            # Method 1: Try social actions endpoint with enhanced scope
            if 'w_member_social' in self.available_scopes:
                url = f"{self.BASE_URL}/rest/socialActions"
                params = {
                    'q': 'entity',
                    'entity': urllib.parse.quote(post_urn, safe='')
                }
                
                headers = self.headers.copy()
                headers['X-RestLi-Method'] = 'FINDER'
                
                response = requests.get(url, headers=headers, params=params, timeout=30)
                logger.debug(f"Enhanced social actions API response status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    analytics_data.update(data)
                    logger.info(f"Successfully fetched enhanced social actions for post: {post_urn}")
            
            # Method 2: Try legacy social actions endpoint
            url = f"{self.BASE_URL}/v2/socialActions/{urllib.parse.quote(post_urn, safe='')}"
            response = requests.get(url, headers=self.headers, timeout=30)
            logger.debug(f"Legacy social actions API response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                analytics_data.update(data)
                logger.info(f"Successfully fetched social actions for post: {post_urn}")
            
            # Method 3: Try specific engagement endpoints
            engagement_data = self._fetch_specific_engagement(post_urn)
            analytics_data.update(engagement_data)
            
            return analytics_data
                
        except Exception as e:
            logger.error(f"Error fetching post analytics: {str(e)}")
            return {}
    
    def _fetch_specific_engagement(self, post_urn: str) -> Dict:
        """
        Fetch specific engagement metrics (likes, comments, shares) for a post.
        """
        engagement_data = {}
        
        try:
            # Try to get likes
            url = f"{self.BASE_URL}/v2/socialActions/{urllib.parse.quote(post_urn, safe='')}/likes"
            response = requests.get(url, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                likes_data = response.json()
                engagement_data['likes'] = likes_data
                logger.debug(f"Successfully fetched likes for post: {post_urn}")
            
            # Try to get comments
            url = f"{self.BASE_URL}/v2/socialActions/{urllib.parse.quote(post_urn, safe='')}/comments"
            response = requests.get(url, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                comments_data = response.json()
                engagement_data['comments'] = comments_data
                logger.debug(f"Successfully fetched comments for post: {post_urn}")
            
            # Try to get shares
            url = f"{self.BASE_URL}/v2/socialActions/{urllib.parse.quote(post_urn, safe='')}/shares"
            response = requests.get(url, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                shares_data = response.json()
                engagement_data['shares'] = shares_data
                logger.debug(f"Successfully fetched shares for post: {post_urn}")
            
        except Exception as e:
            logger.debug(f"Error fetching specific engagement: {str(e)}")
        
        return engagement_data
    
    def get_connections_count(self) -> int:
        """
        Get connections count using enhanced methods available with w_member_social scope.
        """
        try:
            # Method 1: Enhanced people search with w_member_social scope
            if 'w_member_social' in self.available_scopes:
                profile_id = self.get_profile_id()
                if profile_id:
                    url = f"{self.BASE_URL}/v2/people/(id:{profile_id})"
                    response = requests.get(url, headers=self.headers, timeout=30)
                    
                    if response.status_code == 200:
                        data = response.json()
                        connections = (
                            data.get('numConnections', 0) or
                            data.get('connectionCount', 0) or
                            data.get('numConnectionsDisplay', 0)
                        )
                        if connections > 0:
                            logger.info(f"Successfully fetched connections count with enhanced scope: {connections}")
                            return connections
            
            # Method 2: Try people search
            url = f"{self.BASE_URL}/v2/people"
            params = {'q': 'viewer'}
            
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            logger.info(f"People API response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if 'elements' in data and len(data['elements']) > 0:
                    person_data = data['elements'][0]
                    connections = (
                        person_data.get('numConnections', 0) or
                        person_data.get('connectionCount', 0) or
                        person_data.get('connections', {}).get('total', 0)
                    )
                    if connections > 0:
                        logger.info(f"Successfully fetched connections count: {connections}")
                        return connections
            
            # Method 3: Try network sizes endpoint
            profile_id = self.get_profile_id()
            if profile_id:
                url = f"{self.BASE_URL}/v2/networkSizes/urn:li:person:{profile_id}"
                response = requests.get(url, headers=self.headers, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    first_degree = data.get('firstDegreeSize', 0)
                    if first_degree > 0:
                        logger.info(f"Successfully fetched first degree connections: {first_degree}")
                        return first_degree
            
            logger.warning("Could not fetch connections count")
            return 0
                
        except Exception as e:
            logger.error(f"Error fetching connections: {str(e)}")
            return 0
    
    def get_profile_id(self) -> str:
        """Get the profile ID from the current user's profile info."""
        try:
            profile_info = self.get_profile_info()
            return profile_info.get('id', '') or profile_info.get('sub', '')
        except:
            return ''
    
    def fetch_analytics_data(self, linkedin_profile_id: Optional[str] = None) -> Dict:
        """
        Main method to fetch comprehensive analytics data using all available scopes.
        
        Returns a dictionary with analytics data structure.
        """
        try:
            # Get profile info first
            profile_info = self.get_profile_info()
            
            if not profile_info:
                raise ValueError("Unable to fetch profile information. Check access token and permissions.")
            
            # Extract profile ID if not provided
            if not linkedin_profile_id:
                linkedin_profile_id = profile_info.get('id') or profile_info.get('sub')
            
            if not linkedin_profile_id:
                raise ValueError("Unable to determine LinkedIn profile ID")
            
            logger.info(f"Fetching analytics for LinkedIn profile ID: {linkedin_profile_id}")
            logger.info(f"Available scopes: {self.available_scopes}")
            
            # Initialize analytics data structure
            analytics_data = {
                'linkedin_profile_id': linkedin_profile_id,
                'profile_info': profile_info,
                'available_scopes': self.available_scopes,
                'total_followers': 0,
                'total_posts': 0,
                'posts_analytics': [],
                'total_reactions': 0,
                'total_comments': 0,
                'total_reposts': 0,
                'total_impressions': 0,
                'total_engagement': 0,
                'last_updated': datetime.now(timezone.utc),
                'api_limitations': [],
                'data_quality': 'enhanced' if 'w_member_social' in self.available_scopes else 'basic'
            }
            
            # Get connections count
            logger.info("Fetching connections count...")
            connections_count = self.get_connections_count()
            analytics_data['total_followers'] = connections_count
            if connections_count == 0:
                analytics_data['api_limitations'].append('Connections count may require special permissions')
            
            # Fetch user posts
            logger.info("Fetching user posts...")
            posts = self.get_user_posts(linkedin_profile_id)
            analytics_data['total_posts'] = len(posts)
            if len(posts) == 0:
                analytics_data['api_limitations'].append('Posts data may require additional permissions')
            
            # Process each post for analytics
            logger.info(f"Processing {len(posts)} posts for analytics...")
            for i, post in enumerate(posts):
                logger.debug(f"Processing post {i+1}/{len(posts)}")
                post_analytics = self._process_post_analytics(post)
                if post_analytics:
                    analytics_data['posts_analytics'].append(post_analytics)
                    
                    # Add to totals
                    analytics_data['total_reactions'] += post_analytics.get('reactions', 0)
                    analytics_data['total_comments'] += post_analytics.get('comments', 0)
                    analytics_data['total_reposts'] += post_analytics.get('reposts', 0)
                    analytics_data['total_impressions'] += post_analytics.get('impressions', 0)
                    analytics_data['total_engagement'] += post_analytics.get('engagement', 0)
            
            # Log comprehensive summary
            logger.info("=" * 50)
            logger.info("LINKEDIN ANALYTICS SUMMARY")
            logger.info("=" * 50)
            logger.info(f"Profile ID: {analytics_data['linkedin_profile_id']}")
            logger.info(f"Data Quality: {analytics_data['data_quality']}")
            logger.info(f"Available Scopes: {', '.join(analytics_data['available_scopes'])}")
            logger.info(f"Total Followers: {analytics_data['total_followers']}")
            logger.info(f"Total Posts: {analytics_data['total_posts']}")
            logger.info(f"Total Reactions: {analytics_data['total_reactions']}")
            logger.info(f"Total Comments: {analytics_data['total_comments']}")
            logger.info(f"Total Reposts: {analytics_data['total_reposts']}")
            logger.info(f"Total Engagement: {analytics_data['total_engagement']}")
            
            if analytics_data['api_limitations']:
                logger.warning("API Limitations:")
                for limitation in analytics_data['api_limitations']:
                    logger.warning(f"- {limitation}")
            else:
                logger.info("✅ No API limitations detected - full data access available!")
            
            logger.info("=" * 50)
            
            return analytics_data
            
        except Exception as e:
            logger.error(f"Error fetching analytics data: {str(e)}")
            raise
    
    def _process_post_analytics(self, post: Dict) -> Optional[Dict]:
        """
        Process a single post to extract comprehensive analytics data.
        Enhanced for w_member_social scope capabilities.
        """
        try:
            post_id = post.get('id', '')
            post_urn = post.get('urn', post_id)
            
            # Extract basic post info
            post_analytics = {
                'post_id': post_id,
                'post_urn': post_urn,
                'post_content': self._extract_post_content(post),
                'post_date': self._extract_post_date(post),
                'reactions': 0,
                'comments': 0,
                'reposts': 0,
                'impressions': 0,
                'engagement': 0,
                'visibility': post.get('visibility', 'UNKNOWN'),
                'lifecycle_state': post.get('lifecycleState', 'UNKNOWN'),
                'post_type': self._determine_post_type(post)
            }
            
            # Extract engagement data directly from post object first
            self._extract_direct_engagement(post, post_analytics)
            
            # If we have w_member_social scope, try to get detailed analytics
            if 'w_member_social' in self.available_scopes and post_urn:
                logger.debug(f"Fetching detailed analytics for post: {post_urn}")
                social_actions = self.get_post_analytics(post_urn)
                if social_actions:
                    metrics = self._extract_social_metrics(social_actions)
                    # Merge metrics, keeping higher values
                    for key in ['reactions', 'comments', 'reposts', 'impressions']:
                        post_analytics[key] = max(post_analytics.get(key, 0), metrics.get(key, 0))
            
            # Calculate total engagement
            post_analytics['engagement'] = (
                post_analytics['reactions'] + 
                post_analytics['comments'] + 
                post_analytics['reposts']
            )
            
            logger.debug(f"Processed post {post_id} - Type: {post_analytics['post_type']}, Engagement: {post_analytics['engagement']}")
            
            return post_analytics
            
        except Exception as e:
            logger.error(f"Error processing post analytics: {str(e)}")
            return None
    
    def _determine_post_type(self, post: Dict) -> str:
        """Determine the type of post (text, image, video, article, etc.)"""
        try:
            if 'content' in post:
                content = post['content']
                if 'media' in content:
                    media = content['media']
                    if 'id' in media:
                        media_id = media['id']
                        if 'video' in media_id:
                            return 'video'
                        elif 'image' in media_id:
                            return 'image'
                if 'article' in content:
                    return 'article'
            
            if 'specificContent' in post:
                specific = post['specificContent']
                if 'com.linkedin.ugc.ShareContent' in specific:
                    share_content = specific['com.linkedin.ugc.ShareContent']
                    if 'media' in share_content:
                        return 'media'
            
            return 'text'
        except:
            return 'unknown'
    
    def _extract_direct_engagement(self, post: Dict, post_analytics: Dict) -> None:
        """Extract engagement data directly from post object if available."""
        try:
            # Look for engagement data in various possible fields
            if 'socialDetail' in post:
                social_detail = post['socialDetail']
                if 'totalSocialActivityCounts' in social_detail:
                    counts = social_detail['totalSocialActivityCounts']
                    post_analytics['reactions'] = max(post_analytics['reactions'], counts.get('numLikes', 0))
                    post_analytics['comments'] = max(post_analytics['comments'], counts.get('numComments', 0))
                    post_analytics['reposts'] = max(post_analytics['reposts'], counts.get('numShares', 0))
            
            # Check for activity counts
            if 'activity' in post:
                activity = post['activity']
                post_analytics['reactions'] = max(post_analytics['reactions'], activity.get('likes', 0))
                post_analytics['comments'] = max(post_analytics['comments'], activity.get('comments', 0))
                post_analytics['reposts'] = max(post_analytics['reposts'], activity.get('shares', 0))
            
            # Check for statistics
            if 'statistics' in post:
                stats = post['statistics']
                post_analytics['reactions'] = max(post_analytics['reactions'], stats.get('likeCount', 0))
                post_analytics['comments'] = max(post_analytics['comments'], stats.get('commentCount', 0))
                post_analytics['reposts'] = max(post_analytics['reposts'], stats.get('shareCount', 0))
                post_analytics['impressions'] = max(post_analytics['impressions'], stats.get('viewCount', 0))
            
            # Check for engagement summary
            if 'engagementSummary' in post:
                engagement = post['engagementSummary']
                post_analytics['reactions'] = max(post_analytics['reactions'], engagement.get('totalLikes', 0))
                post_analytics['comments'] = max(post_analytics['comments'], engagement.get('totalComments', 0))
                post_analytics['reposts'] = max(post_analytics['reposts'], engagement.get('totalShares', 0))
            
        except Exception as e:
            logger.debug(f"Error extracting direct engagement: {str(e)}")
    
    def _extract_post_content(self, post: Dict) -> str:
        """Extract post content text with enhanced extraction for different post types."""
        try:
            # Try different possible content fields
            commentary = post.get('commentary', '')
            if commentary:
                return commentary
            
            # Try text field
            text = post.get('text', '')
            if text:
                return text
            
            # Try content object
            content = post.get('content', {})
            if isinstance(content, dict):
                content_text = content.get('text', '') or content.get('commentary', '')
                if content_text:
                    return content_text
            
            # Try specificContent for UGC posts
            specific_content = post.get('specificContent', {})
            if isinstance(specific_content, dict):
                share_content = specific_content.get('com.linkedin.ugc.ShareContent', {})
                if share_content:
                    share_commentary = share_content.get('shareCommentary', {})
                    if share_commentary:
                        return share_commentary.get('text', '')
            
            # Try activity content
            if 'activity' in post:
                activity = post['activity']
                activity_text = activity.get('text', '') or activity.get('message', '')
                if activity_text:
                    return activity_text
            
            return str(content) if content else ''
        except:
            return ''
    
    def _extract_post_date(self, post: Dict) -> Optional[datetime]:
        """Extract post creation date with enhanced date field detection."""
        try:
            # Try different timestamp fields
            created_time = (
                post.get('createdAt') or 
                post.get('publishedAt') or 
                post.get('created', {}).get('time') or
                post.get('lastModified', {}).get('time') or
                post.get('createdTime') or
                post.get('publishedTime')
            )
            
            if created_time:
                # LinkedIn timestamps are usually in milliseconds
                if created_time > 10000000000:  # If it looks like milliseconds
                    return datetime.fromtimestamp(created_time / 1000, tz=timezone.utc)
                else:  # If it's in seconds
                    return datetime.fromtimestamp(created_time, tz=timezone.utc)
            return None
        except:
            return None
    
    def _extract_social_metrics(self, social_actions: Dict) -> Dict:
        """Extract metrics from social actions response with enhanced parsing."""
        metrics = {
            'reactions': 0,
            'comments': 0,
            'reposts': 0,
            'impressions': 0
        }
        
        try:
            # Extract different types of social actions
            if 'likesSummary' in social_actions:
                metrics['reactions'] = social_actions['likesSummary'].get('totalLikes', 0)
            
            if 'commentsSummary' in social_actions:
                metrics['comments'] = social_actions['commentsSummary'].get('totalComments', 0)
            
            if 'sharesSummary' in social_actions:
                metrics['reposts'] = social_actions['sharesSummary'].get('totalShares', 0)
            
            # Try alternative field names
            if 'likes' in social_actions:
                likes_data = social_actions['likes']
                if isinstance(likes_data, dict):
                    metrics['reactions'] = max(metrics['reactions'], likes_data.get('paging', {}).get('total', 0))
                elif isinstance(likes_data, list):
                    metrics['reactions'] = max(metrics['reactions'], len(likes_data))
            
            if 'comments' in social_actions:
                comments_data = social_actions['comments']
                if isinstance(comments_data, dict):
                    metrics['comments'] = max(metrics['comments'], comments_data.get('paging', {}).get('total', 0))
                elif isinstance(comments_data, list):
                    metrics['comments'] = max(metrics['comments'], len(comments_data))
            
            if 'shares' in social_actions:
                shares_data = social_actions['shares']
                if isinstance(shares_data, dict):
                    metrics['reposts'] = max(metrics['reposts'], shares_data.get('paging', {}).get('total', 0))
                elif isinstance(shares_data, list):
                    metrics['reposts'] = max(metrics['reposts'], len(shares_data))
            
            # Look for total counts
            if 'totalCounts' in social_actions:
                total_counts = social_actions['totalCounts']
                metrics['reactions'] = max(metrics['reactions'], total_counts.get('LIKE', 0))
                metrics['comments'] = max(metrics['comments'], total_counts.get('COMMENT', 0))
                metrics['reposts'] = max(metrics['reposts'], total_counts.get('SHARE', 0))
            
            # Look for elements array
            if 'elements' in social_actions:
                elements = social_actions['elements']
                if isinstance(elements, list):
                    for element in elements:
                        if 'socialActivityType' in element:
                            activity_type = element['socialActivityType']
                            if activity_type == 'LIKE':
                                metrics['reactions'] += 1
                            elif activity_type == 'COMMENT':
                                metrics['comments'] += 1
                            elif activity_type == 'SHARE':
                                metrics['reposts'] += 1
            
        except Exception as e:
            logger.error(f"Error extracting social metrics: {str(e)}")
        
        return metrics


def fetch_linkedin_analytics(access_token: str, linkedin_profile_id: Optional[str] = None) -> Dict:
    """
    Main function to fetch LinkedIn analytics data with enhanced scope support.
    
    Args:
        access_token: LinkedIn access token
        linkedin_profile_id: Optional LinkedIn profile ID
    
    Returns:
        Dictionary containing comprehensive analytics data
    """
    service = LinkedInAnalyticsService(access_token)
    return service.fetch_analytics_data(linkedin_profile_id)


class LinkedInScraperService:
    """
    ⚠️ WARNING: Educational/Research purposes only!
    
    This service attempts to scrape LinkedIn profile data using Selenium.
    
    RISKS:
    - Violates LinkedIn ToS
    - May result in account suspension
    - Anti-scraping measures may block access
    - Unreliable due to frequent UI changes
    
    USE OFFICIAL API INSTEAD!
    """
    
    def __init__(self, access_token: str, headless: bool = True):
        if not SELENIUM_AVAILABLE:
            raise ImportError("Selenium not available. Install with: pip install selenium")
        
        self.access_token = access_token
        self.headless = headless
        self.driver = None
        self.wait = None
        
        # Log warning
        logger.warning("🚨 LinkedIn Scraper initialized - USE AT YOUR OWN RISK!")
        logger.warning("This may violate LinkedIn's Terms of Service")
        logger.warning("Recommended: Use official LinkedIn API instead")
    
    def _setup_driver(self) -> None:
        """Setup Chrome WebDriver with appropriate options."""
        try:
            chrome_options = Options()
            
            if self.headless:
                chrome_options.add_argument("--headless")
            
            # Anti-detection measures (may not be sufficient)
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Set user agent to look more like a real browser
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            self.wait = WebDriverWait(self.driver, 10)
            
            logger.info("Chrome WebDriver initialized")
            
        except Exception as e:
            logger.error(f"Failed to setup WebDriver: {str(e)}")
            raise
    
    def _login_with_token(self) -> bool:
        """
        Attempt to use access token for authentication.
        
        Note: This is complex because LinkedIn's web interface
        doesn't directly accept API access tokens.
        """
        try:
            # Navigate to LinkedIn
            self.driver.get("https://www.linkedin.com")
            
            # This is where it gets tricky - we'd need to:
            # 1. Either use the token to get session cookies
            # 2. Or implement OAuth flow in the browser
            # 3. Or ask user to manually login (not automated)
            
            logger.warning("Token-based login not implemented - would need manual login")
            logger.warning("This is a major limitation of the scraping approach")
            
            return False
            
        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            return False
    
    def scrape_profile_analytics(self, profile_url: Optional[str] = None) -> Dict:
        """
        Attempt to scrape profile analytics data.
        
        ⚠️ WARNING: This is highly unreliable and risky!
        """
        try:
            if not self.driver:
                self._setup_driver()
            
            # Attempt login (this is the major blocker)
            if not self._login_with_token():
                logger.error("Cannot proceed without authentication")
                return {
                    'error': 'Authentication failed',
                    'message': 'Scraping requires manual login - not recommended',
                    'recommendation': 'Use official LinkedIn API instead'
                }
            
            # If we somehow got past login, scrape profile data
            analytics_data = self._scrape_profile_data(profile_url)
            
            return analytics_data
            
        except Exception as e:
            logger.error(f"Scraping failed: {str(e)}")
            return {
                'error': str(e),
                'message': 'Scraping failed - this approach is unreliable',
                'recommendation': 'Use official LinkedIn API instead'
            }
        finally:
            self._cleanup()
    
    def _scrape_profile_data(self, profile_url: str) -> Dict:
        """
        Scrape profile data from LinkedIn profile page.
        
        Note: This would be extremely fragile and break frequently.
        """
        try:
            # Navigate to profile
            if not profile_url:
                profile_url = "https://www.linkedin.com/in/me/"
            
            self.driver.get(profile_url)
            time.sleep(3)  # Wait for page load
            
            analytics_data = {
                'scraping_method': 'selenium',
                'scraped_at': datetime.now(timezone.utc),
                'profile_url': profile_url,
                'total_followers': 0,
                'total_posts': 0,
                'posts_analytics': [],
                'warnings': [
                    'Data scraped using unofficial methods',
                    'May be incomplete or inaccurate',
                    'Violates LinkedIn Terms of Service',
                    'Use official API instead'
                ]
            }
            
            # Attempt to scrape follower count
            try:
                # These selectors would break frequently as LinkedIn updates their UI
                follower_elements = self.driver.find_elements(By.CSS_SELECTOR, 
                    "[data-test-id='followers-count'], .pv-recent-activity-section__follower-count, .t-bold")
                
                for element in follower_elements:
                    text = element.text.lower()
                    if 'follower' in text or 'connection' in text:
                        # Extract number from text like "1,234 followers"
                        numbers = re.findall(r'[\d,]+', text)
                        if numbers:
                            follower_count = int(numbers[0].replace(',', ''))
                            analytics_data['total_followers'] = follower_count
                            break
                            
            except Exception as e:
                logger.warning(f"Could not scrape follower count: {str(e)}")
            
            # Attempt to scrape recent posts
            try:
                # Navigate to activity/posts section
                activity_url = f"{profile_url.rstrip('/')}/recent-activity/all/"
                self.driver.get(activity_url)
                time.sleep(3)
                
                # Look for posts (selectors would be very fragile)
                post_elements = self.driver.find_elements(By.CSS_SELECTOR, 
                    ".feed-shared-update-v2, .occludable-update")
                
                analytics_data['total_posts'] = len(post_elements)
                
                # Scrape individual post metrics (very unreliable)
                for i, post_element in enumerate(post_elements[:10]):  # Limit to first 10
                    try:
                        post_data = self._scrape_post_metrics(post_element, i)
                        if post_data:
                            analytics_data['posts_analytics'].append(post_data)
                    except Exception as e:
                        logger.warning(f"Failed to scrape post {i}: {str(e)}")
                        
            except Exception as e:
                logger.warning(f"Could not scrape posts: {str(e)}")
            
            return analytics_data
            
        except Exception as e:
            logger.error(f"Profile scraping failed: {str(e)}")
            raise
    
    def _scrape_post_metrics(self, post_element, index: int) -> Optional[Dict]:
        """
        Attempt to scrape metrics from a single post element.
        
        This would be extremely fragile and unreliable.
        """
        try:
            post_data = {
                'post_index': index,
                'reactions': 0,
                'comments': 0,
                'reposts': 0,
                'post_content': '',
                'scraped_method': 'selenium_dom_parsing'
            }
            
            # Try to extract post content
            try:
                content_element = post_element.find_element(By.CSS_SELECTOR, 
                    ".feed-shared-text, .feed-shared-update-v2__description")
                post_data['post_content'] = content_element.text[:200]  # First 200 chars
            except:
                pass
            
            # Try to extract engagement metrics
            try:
                # Look for reaction counts (selectors would break frequently)
                reaction_elements = post_element.find_elements(By.CSS_SELECTOR,
                    ".social-counts-reactions__count, .social-detail__social-counts")
                
                for element in reaction_elements:
                    text = element.text
                    numbers = re.findall(r'\d+', text)
                    if numbers:
                        post_data['reactions'] = int(numbers[0])
                        break
                        
            except:
                pass
            
            # Try to extract comment counts
            try:
                comment_elements = post_element.find_elements(By.CSS_SELECTOR,
                    ".social-counts-comments, [data-test-id='comments-count']")
                
                for element in comment_elements:
                    text = element.text
                    numbers = re.findall(r'\d+', text)
                    if numbers:
                        post_data['comments'] = int(numbers[0])
                        break
                        
            except:
                pass
            
            return post_data
            
        except Exception as e:
            logger.warning(f"Failed to scrape post metrics: {str(e)}")
            return None
    
    def _cleanup(self) -> None:
        """Clean up WebDriver resources."""
        try:
            if self.driver:
                self.driver.quit()
                logger.info("WebDriver cleaned up")
        except Exception as e:
            logger.warning(f"Cleanup warning: {str(e)}")


def scrape_linkedin_analytics(access_token: str, profile_url: Optional[str] = None) -> Dict:
    """
    ⚠️ WARNING: Educational purposes only!
    
    Attempt to scrape LinkedIn analytics using Selenium.
    
    MAJOR LIMITATIONS:
    1. Violates LinkedIn Terms of Service
    2. Requires manual login (access token can't be used directly)
    3. Extremely unreliable due to UI changes
    4. May result in account suspension
    5. Anti-scraping measures will likely block this
    
    RECOMMENDATION: Use official LinkedIn API instead!
    
    Args:
        access_token: LinkedIn access token (limited use in scraping)
        profile_url: Optional profile URL to scrape
    
    Returns:
        Dictionary with scraped data (if successful) or error messages
    """
    
    # Log strong warning
    logger.warning("🚨" * 20)
    logger.warning("ATTEMPTING LINKEDIN SCRAPING - HIGH RISK!")
    logger.warning("This may violate Terms of Service")
    logger.warning("Account suspension risk")
    logger.warning("Unreliable and not recommended")
    logger.warning("USE OFFICIAL API INSTEAD!")
    logger.warning("🚨" * 20)
    
    scraper = LinkedInScraperService(access_token)
    return scraper.scrape_profile_analytics(profile_url)


def hybrid_linkedin_analytics(access_token: str, linkedin_profile_id: Optional[str] = None) -> Dict:
    """
    Hybrid approach: Try API first, fallback to scraping.
    
    ⚠️ Still not recommended due to scraping risks!
    """
    
    # First, try the official API
    try:
        logger.info("Attempting official LinkedIn API first...")
        api_data = fetch_linkedin_analytics(access_token, linkedin_profile_id)
        
        # Check if we got meaningful data
        if (api_data.get('total_posts', 0) > 0 or 
            api_data.get('total_followers', 0) > 0 or
            len(api_data.get('posts_analytics', [])) > 0):
            
            logger.info("Official API provided sufficient data")
            api_data['data_source'] = 'official_api'
            return api_data
        
        logger.warning("Official API returned limited data, considering scraping...")
        
    except Exception as e:
        logger.error(f"Official API failed: {str(e)}")
    
    # If API fails or returns no data, warn about scraping
    logger.warning("⚠️ Official API insufficient - scraping NOT recommended!")
    
    return {
        'error': 'Official API insufficient',
        'message': 'Scraping is risky and not recommended',
        'recommendation': 'Contact LinkedIn for API access or use available data',
        'api_data': api_data if 'api_data' in locals() else None
    } 