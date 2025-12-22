from django.urls import path
from . import views

urlpatterns = [
    path('chat/', views.chat_api, name='chat'),
    path('sessions/', views.get_user_sessions_api, name='get_user_sessions'),
]
