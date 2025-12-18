"""
URL patterns for Upwork Proposal Generator API.
"""

from django.urls import path
from . import views

app_name = 'upwork_proposal_generator'

urlpatterns = [
    # Main endpoints - only create, list, and delete
    path(
        'proposals/', 
        views.create_upwork_proposal_api, 
        name='proposal-create'
    ),
    path(
        'proposals/<int:proposal_id>/', 
        views.get_upwork_proposal_api, 
        name='proposal-get'
    ),
    
    # Management endpoints
    path('list/', views.list_upwork_proposals_api, name='list_upwork_proposals_api'),
    path('delete/', views.delete_upwork_proposals_api, name='delete_upwork_proposals_api'),
]
