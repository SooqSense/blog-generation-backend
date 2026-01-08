from django.urls import path
from . import views

urlpatterns = [
    # External API v1
    path("v1/blogs/", views.external_blog_list_api, name="external_blog_list_api"),
    path("v1/blogs/<str:blog_id>/", views.external_blog_detail_api, name="external_blog_detail_api"),
    
    # Key Management
    path("v1/keys/generate/", views.generate_api_key_api, name="generate_api_key_api"),
]
