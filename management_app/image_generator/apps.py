from django.apps import AppConfig


class ImageGeneratorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'management_app.image_generator'
    label = 'image_generator'