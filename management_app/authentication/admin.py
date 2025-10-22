from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'clerk_user_id', 'organization_name', 'is_active', 'created_at')
    list_filter = ('is_active', 'is_staff', 'is_superuser', 'organization_name', 'created_at')
    search_fields = ('username', 'email', 'clerk_user_id', 'organization_name')
    ordering = ('-created_at',)
    
    fieldsets = UserAdmin.fieldsets + (
        ('Clerk Integration', {
            'fields': ('clerk_user_id',)
        }),
        ('Organization', {
            'fields': ('organization_id', 'organization_name', 'organization_role'),
        }),
        ('Additional Info', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
