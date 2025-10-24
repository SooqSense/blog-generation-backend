from django.urls import path
from . import views

urlpatterns = [
    path("generate-blog/", views.generate_blog_api, name="generate_blog_api"),
    path("list/", views.list_blog_posts_api, name="list_blog_posts_api"),
    path("get/<int:blog_id>/", views.get_blog_post_api, name="get_blog_post_api"),
    path("delete/", views.delete_blog_posts_api, name="delete_blog_posts_api"),
]
