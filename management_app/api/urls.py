from django.urls import path
from . import views

urlpatterns = [
    # Blog generation API endpoints
    path("generate-blog/", views.generate_blog_api, name="generate_blog_api"),
    path("daily-ai-news/", views.generate_daily_ai_news, name="daily_ai_news"),
    # New API endpoints
    path("generate-image/", views.generate_image_api, name="generate_image_api"),
    path("edit-image/", views.edit_image_api, name="edit_image_api"),
    path(
        "generate-linkedin-post/",
        views.generate_linkedin_post_api,
        name="generate_linkedin_post_api",
    ),
    # LinkedIn posting endpoint
    path(
        "post-on-linkedin/",
        views.post_on_linkedin_api,
        name="post_on_linkedin_api",
    ),
    # LinkedIn token validation endpoint
    path(
        "validate-linkedin-token/",
        views.validate_linkedin_token_api,
        name="validate_linkedin_token_api",
    ),
    # LinkedIn re-authentication URL endpoint
    path(
        "linkedin-reauth-url/",
        views.linkedin_reauth_url_api,
        name="linkedin_reauth_url_api",
    ),
    # Trending topics endpoint - simplified to only accept keyword
    path(
        "fetch-related-topics/",
        views.fetch_and_save_related_topics,
        name="fetch_and_save_related_topics",
    ),
    # LinkedIn analytics endpoints
    path(
        "linkedin-analytics/",
        views.fetch_linkedin_analytics_api,
        name="fetch_linkedin_analytics_api",
    ),
    # Schedule LinkedIn Post endpoints
    path(
        "schedule-linkedin-post/",
        views.schedule_linkedin_post_api,
        name="schedule_linkedin_post_api",
    ),
    path(
        "scheduled-posts/",
        views.get_scheduled_posts_api,
        name="get_scheduled_posts_api",
    ),
    path(
        "cancel-scheduled-post/<int:schedule_id>/",
        views.cancel_scheduled_post_api,
        name="cancel_scheduled_post_api",
    ),
    # Removed view endpoints as requested
]
