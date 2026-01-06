from django.contrib import admin

from .models import BlogAPIKey

@admin.register(BlogAPIKey)
class BlogAPIKeyAdmin(admin.ModelAdmin):
    list_display = ("name", "prefix", "organization_name", "is_active", "created_at")
    list_filter = ("is_active", "organization_name")
    search_fields = ("name", "prefix")
    readonly_fields = ("prefix", "hashed_key", "created_at")
