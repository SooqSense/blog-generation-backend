from django.urls import path
from .views import (
    RegisterView, LoginView, UserListView,
    CustomTokenRefreshView, GoogleLoginRedirectView,
    GoogleLoginCallbackView, 
    LinkedInLoginRedirectView, LinkedInLoginCallbackView,
    LinkedInTokenView
)

urlpatterns = [
    # Regular auth endpoints
    path('register/', RegisterView.as_view(), name='auth_register'),
    path('login/', LoginView.as_view(), name='auth_login'),
    path('refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('users/', UserListView.as_view(), name='user_list'),
    
    # Google auth endpoints
    path('google/login/', GoogleLoginRedirectView.as_view(), name='google_login'),
    path('google/callback', GoogleLoginCallbackView.as_view(), name='google_callback'),
    
    # LinkedIn auth endpoints
    path('linkedin/login/', LinkedInLoginRedirectView.as_view(), name='linkedin_login'),
    path('linkedin/callback', LinkedInLoginCallbackView.as_view(), name='linkedin_callback'),
    path('linkedin/token/', LinkedInTokenView.as_view(), name='linkedin_token'),
] 