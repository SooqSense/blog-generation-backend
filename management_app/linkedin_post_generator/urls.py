from django.urls import path
from . import views

urlpatterns = [
    path("generate-linkedin-post/", views.generate_linkedin_post_api, name="generate_linkedin_post_api"),
    path("post-on-linkedin/", views.post_on_linkedin_api, name="post_on_linkedin_api"),
    path("validate-linkedin-token/", views.validate_linkedin_token_api, name="validate_linkedin_token_api"),
    path("linkedin-reauth-url/", views.linkedin_reauth_url_api, name="linkedin_reauth_url_api"),
    path("linkedin-analytics/", views.fetch_linkedin_analytics_api, name="fetch_linkedin_analytics_api"),
    
    # List and Management endpoints
    path("list-posts/", views.list_linkedin_posts_api, name="list_linkedin_posts_api"),
    path("get-post/<int:post_id>/", views.get_linkedin_post_api, name="get_linkedin_post_api"),
    path("delete-posts/", views.delete_linkedin_posts_api, name="delete_linkedin_posts_api"),
    path("download-pdf/<int:post_id>/", views.download_linkedin_post_pdf_api, name="download_linkedin_post_pdf_api"),
    path("list-posting-content/", views.list_linkedin_posting_content_api, name="list_linkedin_posting_content_api"),
    path("delete-posting-content/", views.delete_linkedin_posting_content_api, name="delete_linkedin_posting_content_api"),
]
