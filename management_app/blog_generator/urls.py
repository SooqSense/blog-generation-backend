from django.urls import path
from . import views

urlpatterns = [
    path("generate-blog/", views.generate_blog_api, name="generate_blog_api"),
]
