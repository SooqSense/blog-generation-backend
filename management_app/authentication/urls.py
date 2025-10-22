from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='auth_login'),
    path('verify/', views.verify_token_view, name='auth_verify'),
    path('profile/', views.profile_view, name='auth_profile'),
    path('switch-organization/', views.switch_organization_view, name='auth_switch_organization'),
]
