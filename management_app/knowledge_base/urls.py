from django.urls import path
from . import views

urlpatterns = [
    # Directory management endpoints
    path("directories/", views.list_directories_api, name="list_directories"),
    path("directories/create/", views.create_directory_api, name="create_directory"),
    path("directories/<int:directory_id>/delete/", views.delete_directory_api, name="delete_directory"),
    
    # Document management endpoints
    path("upload-document/", views.upload_document_api, name="upload_document"),
    path("documents/", views.list_documents_api, name="list_documents"),
    path("documents/<int:document_id>/delete/", views.delete_document_api, name="delete_document"),
    
    # Legacy endpoint (for backward compatibility)
    path("upload-pdf/", views.upload_document_api, name="upload_pdf_api"),
]
