from django.urls import path
from .views import (
    RegisterView, LoginView, UserListView,
    CustomTokenRefreshView, GoogleLoginRedirectView,
    GoogleLoginCallbackView, 
    LinkedInLoginRedirectView, LinkedInLoginCallbackView,
    LinkedInTokenView,
    # Clerk authentication views
    ClerkAuthVerifyView, ClerkSessionCreateView,
    ClerkSessionStatusView, ClerkSessionLogoutView
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
    
    # Clerk auth endpoints
    path('clerk/verify/', ClerkAuthVerifyView.as_view(), name='clerk_verify'),
    path('clerk/session/create/', ClerkSessionCreateView.as_view(), name='clerk_session_create'),
    path('clerk/session/status/', ClerkSessionStatusView.as_view(), name='clerk_session_status'),
    path('clerk/session/logout/', ClerkSessionLogoutView.as_view(), name='clerk_session_logout'),
] 