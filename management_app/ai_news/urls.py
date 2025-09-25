from django.urls import path
from . import views

urlpatterns = [
    path("daily-ai-news/", views.generate_daily_ai_news, name="daily_ai_news"),
]
