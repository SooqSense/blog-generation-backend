from django.urls import path
from . import views

urlpatterns = [
    path("generate-linkedin-post/", views.generate_linkedin_post_api, name="generate_linkedin_post_api"),
    path("post-on-linkedin/", views.post_on_linkedin_api, name="post_on_linkedin_api"),
    path("validate-linkedin-token/", views.validate_linkedin_token_api, name="validate_linkedin_token_api"),
    path("linkedin-reauth-url/", views.linkedin_reauth_url_api, name="linkedin_reauth_url_api"),
    path("linkedin-analytics/", views.fetch_linkedin_analytics_api, name="fetch_linkedin_analytics_api"),
]
