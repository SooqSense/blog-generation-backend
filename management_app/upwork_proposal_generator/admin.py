from django.contrib import admin
from .models import UpworkProposal


@admin.register(UpworkProposal)
class UpworkProposalAdmin(admin.ModelAdmin):
    """Django admin configuration for UpworkProposal model."""
    
    list_display = [
        'id',
        'company_name', 
        'client_name',
        'title',
        'status',
        'user',
        'created_at'
    ]
    
    list_filter = [
        'status',
        'created_at',
        'updated_at'
    ]
    
    search_fields = [
        'company_name',
        'client_name', 
        'title',
        'requirements'
    ]
    
    readonly_fields = [
        'created_at',
        'updated_at',
        'proposal_content'
    ]
    
    fieldsets = [
        ('Client Information', {
            'fields': ['client_name', 'company_name', 'company_website_links']
        }),
        ('Project Details', {
            'fields': ['title', 'requirements']
        }),
        ('Your Personal Information', {
            'fields': ['your_name', 'upwork_profile_link', 'contact_information'],
            'description': 'Personal information used in proposal signatures'
        }),
        ('Generated Content', {
            'fields': ['proposal_content']
        }),
        ('Status & Metadata', {
            'fields': ['status', 'error_message', 'user', 'created_at', 'updated_at']
        }),
    ]
    
    def get_queryset(self, request):
        """Show all proposals to superusers, only own proposals to regular users."""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user)
