from django.urls import path
from . import views

urlpatterns = [
    path("fetch-related-topics/", views.fetch_and_save_related_topics, name="fetch_and_save_related_topics"),
    
    # List and Management endpoints
    path("list/", views.list_trending_topics_api, name="list_trending_topics_api"),
    path("get/<int:topic_id>/", views.get_trending_topics_api, name="get_trending_topics_api"),
    path("delete/", views.delete_trending_topics_api, name="delete_trending_topics_api"),
]
