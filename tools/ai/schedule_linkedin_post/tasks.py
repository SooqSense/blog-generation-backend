from celery import shared_task
from django.utils import timezone
from datetime import datetime
import requests
import logging
import os
from django.conf import settings

logger = logging.getLogger(__name__)


def _schedule_linkedin_post_batch_logic(task_self, schedule_post_id, delay_between_posts=5):
    """
    Core logic for posting multiple content items to LinkedIn at the scheduled time with delays
    """
    try:
        # Import Django and setup if not already done (with comprehensive safety check)
        import django
        import sys
        import os
        
        # Comprehensive server context check
        def is_server_context():
            # Check for Django management command context
            if 'django.core.management' in sys.modules:
                return True
            
            # Check if Django apps are loading
            if hasattr(django, 'apps') and django.apps:
                if django.apps.apps.loading or django.apps.apps.ready:
                    return True
            
            # Check for server commands
            server_commands = ['runserver', 'gunicorn', 'uwsgi', 'celery', 'manage.py']
            if any(cmd in ' '.join(sys.argv) for cmd in server_commands):
                return True
            
            # Check environment - likely in server if DJANGO_SETTINGS_MODULE is set
            if os.environ.get('DJANGO_SETTINGS_MODULE'):
                return True
            
            return False
        
        # Only setup if absolutely necessary and safe
        if not is_server_context():
            try:
                if not django.apps.apps.ready and not django.apps.apps.loading:
                    django.setup()
            except RuntimeError as e:
                if "populate() isn't reentrant" in str(e):
                    print("LinkedIn tasks: Django already initialized - using existing setup")
                else:
                    raise e
        else:
            print("LinkedIn tasks: Running in server context - skipping Django setup")
        
        # Import models inside the task to avoid Django app context issues
        from api.models import SchedulePosts, LinkedinPostingContent
        from datetime import timedelta
        
        # Get the scheduled post
        schedule_post = SchedulePosts.objects.get(id=schedule_post_id)
        
        # Check if post is still scheduled (not cancelled)
        if schedule_post.status != 'scheduled':
            logger.info(f"Scheduled post batch {schedule_post_id} is no longer scheduled. Status: {schedule_post.status}")
            return f"Post batch {schedule_post_id} is no longer scheduled"
        
        # Check if it's time to post (with some tolerance)
        current_time = timezone.now()
        scheduled_time = schedule_post.scheduled_datetime
        
        logger.info(f"Time check - Current: {current_time}, Scheduled: {scheduled_time}")
        
        # Allow posting up to 5 minutes early or late
        time_diff = abs((current_time - scheduled_time).total_seconds())
        logger.info(f"Time difference: {time_diff} seconds")
        
        if time_diff > 300:  # 5 minutes
            logger.warning(f"Post batch {schedule_post_id} scheduled for {scheduled_time} but current time is {current_time}")
            logger.warning(f"Time difference is {time_diff} seconds (more than 5 minutes)")
        else:
            logger.info(f"Time check passed - proceeding with posting")
        
        # Get LinkedIn access token
        logger.info(f"Attempting to get LinkedIn access token for user {schedule_post.user_id}")
        access_token = get_linkedin_access_token(schedule_post.user_id, schedule_post.linkedin_profile_id)
        
        if not access_token:
            error_msg = f"LinkedIn access token not found or expired for user {schedule_post.user_id}"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        logger.info(f"Successfully retrieved LinkedIn access token for user {schedule_post.user_id}")
        
        # Get content array
        content_array = schedule_post.content
        if not isinstance(content_array, list):
            content_array = [content_array]  # Fallback for single content
        
        total_posts = len(content_array)
        successful_posts = 0
        failed_posts = 0
        posted_ids = []
        errors = []
        
        # Distribute images across posts if available
        image_urls = schedule_post.image_urls or []
        images_per_post = len(image_urls) // total_posts if total_posts > 0 else 0
        remaining_images = len(image_urls) % total_posts if total_posts > 0 else 0
        
        logger.info(f"Starting batch posting for {total_posts} posts with {delay_between_posts} minutes delay")
        
        # Post each content item with delay
        for i, content_item in enumerate(content_array):
            try:
                # Calculate images for this post
                start_img_idx = i * images_per_post
                end_img_idx = start_img_idx + images_per_post
                if i < remaining_images:  # Distribute remaining images to first posts
                    end_img_idx += 1
                    start_img_idx += i
                    end_img_idx += i
                
                post_images = image_urls[start_img_idx:end_img_idx] if image_urls else []
                
                # Post individual content
                linkedin_post_id = post_single_content(
                    access_token, 
                    schedule_post.linkedin_profile_id, 
                    content_item, 
                    post_images
                )
                
                if linkedin_post_id:
                    successful_posts += 1
                    posted_ids.append(linkedin_post_id)
                    
                    # Create record in LinkedinPostingContent for each post
                    LinkedinPostingContent.objects.create(
                        user_id=schedule_post.user_id,
                        username=schedule_post.username,
                        email=schedule_post.email,
                        linkedin_profile_id=schedule_post.linkedin_profile_id,
                        linkedin_username=schedule_post.linkedin_username,
                        content=content_item,
                        post_date=timezone.now(),
                        linkedin_post_id=linkedin_post_id,
                        post_status='success',
                        image_urls=post_images,
                        images_count=len(post_images),
                        post_type='image' if post_images else 'text'
                    )
                    
                    logger.info(f"Successfully posted content {i+1}/{total_posts} - Post ID: {linkedin_post_id}")
                else:
                    failed_posts += 1
                    errors.append(f"Failed to post content {i+1}")
                    logger.error(f"Failed to post content {i+1}/{total_posts}")
                
                # Add delay between posts (except for the last post)
                if i < total_posts - 1:
                    import time
                    time.sleep(delay_between_posts * 60)  # Convert minutes to seconds
                    
            except Exception as e:
                failed_posts += 1
                error_msg = f"Error posting content {i+1}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        # Update schedule post status
        if successful_posts == total_posts:
            schedule_post.status = 'posted'
            schedule_post.linkedin_post_id = ', '.join(posted_ids)  # Store all post IDs
        elif successful_posts > 0:
            schedule_post.status = 'partially_posted'
            schedule_post.linkedin_post_id = ', '.join(posted_ids)
            schedule_post.error_message = f"Posted {successful_posts}/{total_posts} posts. Errors: {'; '.join(errors)}"
        else:
            schedule_post.status = 'failed'
            schedule_post.error_message = f"All posts failed. Errors: {'; '.join(errors)}"
        
        schedule_post.posted_at = timezone.now()
        schedule_post.save()
        
        result_msg = f"Batch posting completed: {successful_posts}/{total_posts} posts successful"
        logger.info(f"Batch posting completed for {schedule_post_id}: {successful_posts}/{total_posts} successful")
        return result_msg
        
    except Exception as exc:
        logger.error(f"Error in schedule_linkedin_post_batch_logic for post {schedule_post_id}: {str(exc)}")
        
        # Update schedule post with error if it exists
        try:
            from api.models import SchedulePosts
            schedule_post = SchedulePosts.objects.get(id=schedule_post_id)
            schedule_post.status = 'failed'
            schedule_post.error_message = str(exc)
            schedule_post.save()
        except:
            pass
        
        # Retry the task if task_self is provided
        if task_self and hasattr(task_self, 'request') and hasattr(task_self, 'max_retries'):
            if task_self.request.retries < task_self.max_retries:
                logger.info(f"Retrying batch task for post {schedule_post_id}. Attempt {task_self.request.retries + 1}")
                raise task_self.retry(countdown=60 * (task_self.request.retries + 1))  # Exponential backoff
        
        return f"Failed to post batch: {str(exc)}"


@shared_task(bind=True, max_retries=3)
def schedule_linkedin_post_batch_task(self, schedule_post_id, delay_between_posts=5):
    """
    Celery task to post multiple content items to LinkedIn at the scheduled time with delays
    """
    return _schedule_linkedin_post_batch_logic(self, schedule_post_id, delay_between_posts)


def post_single_content(access_token, linkedin_profile_id, content, image_urls=None):
    """
    Post a single content item to LinkedIn
    """
    try:
        logger.info(f"Posting content to LinkedIn for profile {linkedin_profile_id}")
        logger.info(f"Content length: {len(content)} characters")
        logger.info(f"Images: {len(image_urls) if image_urls else 0}")
        
        linkedin_api_url = "https://api.linkedin.com/v2/ugcPosts"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'X-Restli-Protocol-Version': '2.0.0'
        }
        
        logger.info(f"Using LinkedIn API URL: {linkedin_api_url}")
        logger.info(f"Token preview: {access_token[:20]}...")
        
        # Prepare post data
        post_data = {
            "author": f"urn:li:person:{linkedin_profile_id}",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": content
                    },
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }
        
        # Handle images if present
        if image_urls:
            post_data["specificContent"]["com.linkedin.ugc.ShareContent"]["shareMediaCategory"] = "IMAGE"
            media_list = []
            
            for image_url in image_urls:
                # Upload image to LinkedIn and get asset URN
                asset_urn = upload_image_to_linkedin(access_token, linkedin_profile_id, image_url)
                if asset_urn:
                    media_list.append({
                        "status": "READY",
                        "description": {
                            "text": ""
                        },
                        "media": asset_urn,
                        "title": {
                            "text": ""
                        }
                    })
            
            if media_list:
                post_data["specificContent"]["com.linkedin.ugc.ShareContent"]["media"] = media_list
        
        # Make the LinkedIn API request
        logger.info(f"Making LinkedIn API request...")
        logger.info(f"Post data: {post_data}")
        
        response = requests.post(linkedin_api_url, json=post_data, headers=headers)
        
        logger.info(f"LinkedIn API response status: {response.status_code}")
        logger.info(f"LinkedIn API response: {response.text}")
        
        if response.status_code == 201:
            response_data = response.json()
            post_id = response_data.get('id', '')
            logger.info(f"Successfully posted to LinkedIn! Post ID: {post_id}")
            return post_id
        else:
            logger.error(f"LinkedIn API error: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Error posting single content: {str(e)}")
        return None


# Keep the original task for backward compatibility
@shared_task(bind=True, max_retries=3)
def schedule_linkedin_post_task(self, schedule_post_id):
    """
    Celery task to post content to LinkedIn at the scheduled time (backward compatibility)
    """
    return _schedule_linkedin_post_batch_logic(self, schedule_post_id, 0)


def get_linkedin_access_token(user_id, linkedin_profile_id):
    """
    Get LinkedIn access token for the user
    """
    try:
        from authentication.models import User
        user = User.objects.get(id=user_id)
        token = getattr(user, 'linkedin_access_token', None)
        
        # Debug logging
        logger.info(f"Getting LinkedIn token for user {user_id}")
        logger.info(f"User found: {user.username} ({user.email})")
        logger.info(f"Token exists: {bool(token)}")
        if token:
            logger.info(f"Token preview: {token[:20]}...")
            logger.info(f"LinkedIn profile ID: {getattr(user, 'linkedin_profile_id', 'None')}")
            
            # Check token expiration
            if hasattr(user, 'linkedin_token_expires_at') and user.linkedin_token_expires_at:
                from django.utils import timezone
                if user.linkedin_token_expires_at < timezone.now():
                    logger.error(f"LinkedIn token expired for user {user_id} at {user.linkedin_token_expires_at}")
                    return None
                else:
                    logger.info(f"Token expires at: {user.linkedin_token_expires_at}")
        else:
            logger.error(f"No LinkedIn token found for user {user_id}")
            
        return token
    except Exception as e:
        logger.error(f"Error getting LinkedIn access token for user {user_id}: {str(e)}")
        return None


def upload_image_to_linkedin(access_token, linkedin_profile_id, image_url):
    """
    Upload image to LinkedIn and return asset URN
    """
    try:
        # Step 1: Register upload
        register_url = "https://api.linkedin.com/v2/assets?action=registerUpload"
        
        register_data = {
            "registerUploadRequest": {
                "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                "owner": f"urn:li:person:{linkedin_profile_id}",
                "serviceRelationships": [
                    {
                        "relationshipType": "OWNER",
                        "identifier": "urn:li:userGeneratedContent"
                    }
                ]
            }
        }
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        register_response = requests.post(register_url, json=register_data, headers=headers)
        
        if register_response.status_code != 200:
            logger.error(f"Failed to register upload: {register_response.text}")
            return None
        
        register_result = register_response.json()
        upload_url = register_result['value']['uploadMechanism']['com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest']['uploadUrl']
        asset_urn = register_result['value']['asset']
        
        # Step 2: Download image from URL
        image_response = requests.get(image_url)
        if image_response.status_code != 200:
            logger.error(f"Failed to download image from {image_url}")
            return None
        
        # Step 3: Upload image to LinkedIn
        upload_headers = {
            'Authorization': f'Bearer {access_token}',
        }
        
        upload_response = requests.post(upload_url, data=image_response.content, headers=upload_headers)
        
        if upload_response.status_code == 201:
            return asset_urn
        else:
            logger.error(f"Failed to upload image: {upload_response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Error uploading image to LinkedIn: {str(e)}")
        return None


@shared_task
def cancel_scheduled_post_task(schedule_post_id):
    """
    Cancel a scheduled LinkedIn post
    """
    try:
        # Import models inside the task to avoid Django app context issues
        from api.models import SchedulePosts
        
        schedule_post = SchedulePosts.objects.get(id=schedule_post_id)
        
        if schedule_post.status == 'scheduled':
            schedule_post.status = 'cancelled'
            schedule_post.save()
            
            logger.info(f"Cancelled scheduled post {schedule_post_id}")
            return f"Successfully cancelled scheduled post {schedule_post_id}"
        else:
            return f"Post {schedule_post_id} cannot be cancelled. Current status: {schedule_post.status}"
            
    except Exception as e:
        if 'DoesNotExist' in str(type(e)):
            return f"Scheduled post {schedule_post_id} not found"
        else:
            logger.error(f"Error cancelling scheduled post {schedule_post_id}: {str(e)}")
            return f"Error cancelling post: {str(e)}" 