"""
URL patterns for Upwork Proposal Generator API.
"""

from django.urls import path
from . import views

app_name = 'upwork_proposal_generator'

urlpatterns = [
    # Main CRUD endpoints
    path(
        'proposals/', 
        views.UpworkProposalListCreateView.as_view(), 
        name='proposal-list-create'
    ),
    path(
        'proposals/<int:pk>/', 
        views.UpworkProposalDetailView.as_view(), 
        name='proposal-detail'
    ),
    
    # Direct generation (without saving to database)
    path(
        'generate/', 
        views.generate_proposal_direct, 
        name='generate-direct'
    ),
    
    # Status and regeneration endpoints
    path(
        'proposals/<int:proposal_id>/status/', 
        views.proposal_status, 
        name='proposal-status'
    ),
    path(
        'proposals/<int:proposal_id>/regenerate/', 
        views.regenerate_proposal, 
        name='proposal-regenerate'
    ),
]
