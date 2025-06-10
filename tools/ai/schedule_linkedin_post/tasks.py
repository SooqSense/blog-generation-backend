from celery import shared_task
from django.utils import timezone
from datetime import datetime
import requests
import logging
import os
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def schedule_linkedin_post_task(self, schedule_post_id):
    """
    Celery task to post content to LinkedIn at the scheduled time
    """
    try:
        # Import Django and setup if not already done
        import django
        if not django.apps.apps.ready:
            django.setup()
        
        # Import models inside the task to avoid Django app context issues
        from api.models import SchedulePosts, LinkedinPostingContent
        
        # Get the scheduled post
        schedule_post = SchedulePosts.objects.get(id=schedule_post_id)
        
        # Check if post is still scheduled (not cancelled)
        if schedule_post.status != 'scheduled':
            logger.info(f"Scheduled post {schedule_post_id} is no longer scheduled. Status: {schedule_post.status}")
            return f"Post {schedule_post_id} is no longer scheduled"
        
        # Check if it's time to post (with some tolerance)
        current_time = timezone.now()
        scheduled_time = schedule_post.scheduled_datetime
        
        # Allow posting up to 5 minutes early or late
        time_diff = abs((current_time - scheduled_time).total_seconds())
        if time_diff > 300:  # 5 minutes
            logger.warning(f"Post {schedule_post_id} scheduled for {scheduled_time} but current time is {current_time}")
        
        # Prepare LinkedIn API request
        linkedin_api_url = "https://api.linkedin.com/v2/ugcPosts"
        
        # Get LinkedIn access token (you'll need to implement this based on your auth system)
        access_token = get_linkedin_access_token(schedule_post.user_id, schedule_post.linkedin_profile_id)
        
        if not access_token:
            raise Exception("LinkedIn access token not found or expired")
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'X-Restli-Protocol-Version': '2.0.0'
        }
        
        # Prepare post data
        post_data = {
            "author": f"urn:li:person:{schedule_post.linkedin_profile_id}",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": schedule_post.content
                    },
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }
        
        # Handle images if present
        if schedule_post.post_type == 'image' and schedule_post.image_urls:
            post_data["specificContent"]["com.linkedin.ugc.ShareContent"]["shareMediaCategory"] = "IMAGE"
            media_list = []
            
            for image_url in schedule_post.image_urls:
                # Upload image to LinkedIn and get asset URN
                asset_urn = upload_image_to_linkedin(access_token, schedule_post.linkedin_profile_id, image_url)
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
        response = requests.post(linkedin_api_url, json=post_data, headers=headers)
        
        if response.status_code == 201:
            # Success
            response_data = response.json()
            linkedin_post_id = response_data.get('id', '')
            
            # Update schedule post status
            schedule_post.status = 'posted'
            schedule_post.linkedin_post_id = linkedin_post_id
            schedule_post.posted_at = timezone.now()
            schedule_post.save()
            
            # Create record in LinkedinPostingContent
            LinkedinPostingContent.objects.create(
                user_id=schedule_post.user_id,
                username=schedule_post.username,
                email=schedule_post.email,
                linkedin_profile_id=schedule_post.linkedin_profile_id,
                linkedin_username=schedule_post.linkedin_username,
                content=schedule_post.content,
                post_date=timezone.now(),
                linkedin_post_id=linkedin_post_id,
                post_status='success',
                image_urls=schedule_post.image_urls,
                images_count=schedule_post.images_count,
                post_type=schedule_post.post_type
            )
            
            logger.info(f"Successfully posted scheduled LinkedIn post {schedule_post_id}")
            return f"Successfully posted to LinkedIn. Post ID: {linkedin_post_id}"
            
        else:
            # LinkedIn API error
            error_msg = f"LinkedIn API error: {response.status_code} - {response.text}"
            logger.error(f"Failed to post scheduled LinkedIn post {schedule_post_id}: {error_msg}")
            
            # Update schedule post with error
            schedule_post.status = 'failed'
            schedule_post.error_message = error_msg
            schedule_post.save()
            
            raise Exception(error_msg)
    
    except Exception as exc:
        logger.error(f"Error in schedule_linkedin_post_task for post {schedule_post_id}: {str(exc)}")
        
        # Update schedule post with error if it exists
        try:
            from api.models import SchedulePosts
            schedule_post = SchedulePosts.objects.get(id=schedule_post_id)
            schedule_post.status = 'failed'
            schedule_post.error_message = str(exc)
            schedule_post.save()
        except:
            pass
        
        # Retry the task
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying task for post {schedule_post_id}. Attempt {self.request.retries + 1}")
            raise self.retry(countdown=60 * (self.request.retries + 1))  # Exponential backoff
        
        return f"Failed to post after {self.max_retries} retries: {str(exc)}"


def get_linkedin_access_token(user_id, linkedin_profile_id):
    """
    Get LinkedIn access token for the user
    """
    try:
        from authentication.models import User
        user = User.objects.get(id=user_id)
        return getattr(user, 'linkedin_access_token', None)
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