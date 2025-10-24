from django.urls import path
from . import views

urlpatterns = [
    path("daily-ai-news/", views.generate_daily_ai_news, name="daily_ai_news"),
    
    # List and Management endpoints
    path("list/", views.list_ai_news_api, name="list_ai_news_api"),
    path("get/<int:news_id>/", views.get_ai_news_api, name="get_ai_news_api"),
    path("delete/", views.delete_ai_news_api, name="delete_ai_news_api"),
]
