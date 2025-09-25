from django.urls import path
from . import views

urlpatterns = [
    path("fetch-related-topics/", views.fetch_and_save_related_topics, name="fetch_and_save_related_topics"),
]
