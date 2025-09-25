from django.urls import path
from . import views

urlpatterns = [
    path("upload-pdf/", views.upload_pdf_api, name="upload_pdf_api"),
]
