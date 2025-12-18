from django.urls import path
from . import views

urlpatterns = [
    path("generate-image/", views.generate_image_api, name="generate_image_api"),
    path("edit-image/", views.edit_image_api, name="edit_image_api"),
    path("images/", views.list_images_api, name="list_images_api"),
    path("delete/", views.delete_images_api, name="delete_images_api"),
]
