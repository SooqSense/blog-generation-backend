from django.urls import path
from . import views

urlpatterns = [
    # Blog generation API endpoints
    path("generate-blog/", views.generate_blog_api, name="generate_blog_api"),
    path("weekly-news/", views.generate_weekly_news_blog, name="weekly_news_blog"),
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
    # Removed view endpoints as requested
]
