from django.contrib import admin
from .models import BlogGeneral


@admin.register(BlogGeneral)
class BlogGeneralAdmin(admin.ModelAdmin):
    list_display = ('id', 'topic', 'username', 'email', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('topic', 'username', 'email')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)