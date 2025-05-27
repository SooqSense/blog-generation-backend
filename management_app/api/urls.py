from django.urls import path
from . import views

urlpatterns = [
    # Blog generation API endpoints
    path("generate-blog/", views.generate_blog_api, name="generate_blog_api"),
    path("daily-ai-news/", views.generate_daily_ai_news, name="daily_ai_news"),
    # New API endpoints
    path("generate-image/", views.generate_image_api, name="generate_image_api"),
    path(
        "generate-linkedin-post/",
        views.generate_linkedin_post_api,
        name="generate_linkedin_post_api",
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
    # Removed view endpoints as requested
]
