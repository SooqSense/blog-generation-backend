from django.urls import path
from . import views

urlpatterns = [
    # Primary authentication endpoint - verifies Clerk JWT and syncs user to database
    path('verify/', views.verify_token_view, name='auth_verify'),
    
    # User profile and organization management
    path('profile/', views.profile_view, name='auth_profile'),
    path('switch-organization/', views.switch_organization_view, name='auth_switch_organization'),
]
