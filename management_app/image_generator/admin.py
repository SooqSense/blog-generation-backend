from django.contrib import admin
from .models import ImageGeneration, ImageEditing


@admin.register(ImageGeneration)
class ImageGenerationAdmin(admin.ModelAdmin):
    list_display = ('id', 'prompt', 'images_count', 'generation_method', 'username', 'created_at')
    list_filter = ('generation_method', 'image_style', 'created_at')
    search_fields = ('prompt', 'username', 'email')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)


@admin.register(ImageEditing)
class ImageEditingAdmin(admin.ModelAdmin):
    list_display = ('id', 'prompt', 'edit_status', 'username', 'created_at')
    list_filter = ('edit_status', 'created_at')
    search_fields = ('prompt', 'username', 'email')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)