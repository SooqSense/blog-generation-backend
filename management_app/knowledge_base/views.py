from django.utils import timezone
from rest_framework.decorators import api_view, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
import logging
import uuid

# Import models
from .models import Directory, PDFDocument

# Import serializers
from .serializers import DirectorySerializer, PDFDocumentSerializer, PDFDocumentListSerializer

# Import organization access control
from management_app.authentication.services.access_control import require_sooqsense_organization

# Set up logging
logger = logging.getLogger(__name__)

# Import local services
from .service.pdf_extractor.pdf_extractor import document_extractor
from .service.s3_service.s3_service import s3_service

# Import Pinecone service with error handling
try:
    from .service.pinecone_indexing.pinecone_indexing import pinecone_service
    PINECONE_AVAILABLE = True
    logger.info("✅ Pinecone service initialized successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize Pinecone service: {str(e)}")
    pinecone_service = None
    PINECONE_AVAILABLE = False


def _is_sooqsense_admin(user):
    """Check if user is admin of sooqsense organization."""
    if not user or not user.is_authenticated:
        return False
    
    # Check new multi-organization structure first
    user_orgs = getattr(user, 'organization_names', [])
    user_roles = getattr(user, 'organization_roles', [])
    
    if user_orgs and user_roles:
        # Find sooqsense organization index
        try:
            sooqsense_index = None
            for i, org_name in enumerate(user_orgs):
                if org_name.lower() == 'sooqsense':
                    sooqsense_index = i
                    break
            
            if sooqsense_index is not None and sooqsense_index < len(user_roles):
                role = user_roles[sooqsense_index].lower().strip()
                # Handle both 'admin' and 'org:admin' formats
                return role == 'admin' or role == 'org:admin' or role.endswith(':admin')
        except (IndexError, TypeError):
            pass
    
    # Fallback to legacy single organization structure
    current_org = getattr(user, 'organization_name', '').lower()
    if current_org == 'sooqsense':
        org_role = getattr(user, 'organization_role', '').lower().strip()
        # Handle both 'admin' and 'org:admin' formats
        return org_role == 'admin' or org_role == 'org:admin' or org_role.endswith(':admin')
    
    return False


def _ensure_default_directories():
    """Ensure default directories exist in the database."""
    default_directories = [
        {
            'name': 'artilence_projects',
            'description': 'Projects developed by Artilence team',
            'is_default': True
        },
        {
            'name': 'client_projects',
            'description': 'Client projects and case studies',
            'is_default': True
        }
    ]
    
    for dir_data in default_directories:
        directory, created = Directory.objects.get_or_create(
            name=dir_data['name'],
            defaults={
                'description': dir_data['description'],
                'is_default': dir_data['is_default']
            }
        )
        
        if created:
            logger.info(f"✅ Created default directory: {directory.name}")
        else:
            logger.debug(f"📁 Default directory already exists: {directory.name}")


# =====================================================
# DIRECTORY MANAGEMENT ENDPOINTS
# =====================================================

@extend_schema(
    responses={
        200: DirectorySerializer(many=True),
        500: OpenApiResponse(description="Internal Server Error")
    },
    description="Get list of all directories. Automatically creates default directories (artilence_projects, client_projects) if they don't exist."
)
@api_view(["GET"])
@require_sooqsense_organization
def list_directories_api(request):
    """Get list of all directories. Creates default directories if they don't exist."""
    try:
        # Ensure default directories exist
        _ensure_default_directories()
        
        directories = Directory.objects.all()
        serializer = DirectorySerializer(directories, many=True)
        
        return Response({
            "status": "success",
            "directories": serializer.data,
            "total": len(serializer.data)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error listing directories: {type(e).__name__} - {e}")
        return Response(
            {"error": f"An error occurred: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    request=DirectorySerializer,
    responses={
        201: DirectorySerializer,
        400: OpenApiResponse(description="Bad Request"),
        403: OpenApiResponse(description="Admin privileges required"),
        500: OpenApiResponse(description="Internal Server Error")
    },
    description="Create a new directory. Only sooqsense organization administrators can create custom directories."
)
@api_view(["POST"])
@require_sooqsense_organization
def create_directory_api(request):
    """Create a new directory."""
    # Check if user is admin of sooqsense organization
    if not _is_sooqsense_admin(request.user):
        return Response(
            {"error": "Admin privileges required", "detail": "Only sooqsense organization administrators can create directories."},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        # Add created_by_user_id to the data
        data = request.data.copy()
        data['created_by_user_id'] = request.user.id
        
        serializer = DirectorySerializer(data=data)
        
        if serializer.is_valid():
            directory = serializer.save()
            logger.info(f"Created directory: {directory.name} by user {request.user.username}")
            
            return Response({
                "status": "success",
                "message": f"Directory '{directory.name}' created successfully",
                "directory": DirectorySerializer(directory).data
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                "error": "Validation failed",
                "details": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Error creating directory: {type(e).__name__} - {e}")
        return Response(
            {"error": f"An error occurred: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@extend_schema(
    responses={
        200: OpenApiResponse(description="Directory deleted successfully"),
        400: OpenApiResponse(description="Cannot delete default directories"),
        404: OpenApiResponse(description="Directory not found"),
        500: OpenApiResponse(description="Internal Server Error")
    },
    description="Delete a directory. Cannot delete default directories. All documents in the directory must be deleted first."
)
@api_view(["DELETE"])
@require_sooqsense_organization
def delete_directory_api(request, directory_id):
    """Delete a directory."""
    # Check if user is admin of sooqsense organization
    if not _is_sooqsense_admin(request.user):
        return Response(
            {"error": "Admin privileges required", "detail": "Only sooqsense organization administrators can delete directories."},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        directory = Directory.objects.get(id=directory_id)
        
        # Check if it's a default directory
        if directory.is_default:
            return Response({
                "error": "Cannot delete default directories"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if directory has documents
        if directory.documents.exists():
            return Response({
                "error": f"Cannot delete directory. It contains {directory.documents.count()} documents. Please delete all documents first."
            }, status=status.HTTP_400_BAD_REQUEST)
        
        directory_name = directory.name
        directory.delete()
        logger.info(f"Deleted directory: {directory_name} by user {request.user.username}")
        
        return Response({
            "status": "success",
            "message": f"Directory '{directory_name}' deleted successfully"
        }, status=status.HTTP_200_OK)
        
    except Directory.DoesNotExist:
        return Response({
            "error": "Directory not found"
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error deleting directory: {type(e).__name__} - {e}")
        return Response(
            {"error": f"An error occurred: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# =====================================================
# DOCUMENT UPLOAD ENDPOINT
# =====================================================

@extend_schema(
    request={
        'multipart/form-data': {
            'type': 'object',
            'properties': {
                'file': {
                    'type': 'string',
                    'format': 'binary',
                    'description': 'Document file to upload. Supported formats: PDF, DOCX, MD, TXT. Maximum size: 50MB.'
                },
                'directory_id': {
                    'type': 'integer',
                    'description': 'ID of the directory where the file should be uploaded.'
                }
            },
            'required': ['file', 'directory_id']
        }
    },
    responses={
        200: OpenApiResponse(description="Document uploaded and processed successfully."),
        400: OpenApiResponse(description="Bad Request - Invalid file or processing error."),
        500: OpenApiResponse(description="Internal Server Error / Processing Failed.")
    },
    description="Upload a document to a specific directory. The file will be extracted, indexed in Pinecone, and stored in S3 within the selected directory."
)
@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
@require_sooqsense_organization
def upload_document_api(request):
    """Upload and process document files to a specific directory."""
    # Check if user is admin of sooqsense organization
    if not _is_sooqsense_admin(request.user):
        return Response(
            {"error": "Admin privileges required", "detail": "Only sooqsense organization administrators can upload documents."},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        # Ensure default directories exist
        _ensure_default_directories()
        
        if 'file' not in request.FILES:
            return Response(
                {"error": "No file provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        if 'directory_id' not in request.data:
            return Response(
                {"error": "No directory_id provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        file = request.FILES['file']
        directory_id = request.data['directory_id']
        
        # Get directory
        try:
            directory = Directory.objects.get(id=directory_id)
        except Directory.DoesNotExist:
            return Response(
                {"error": f"Directory with id {directory_id} not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        
        logger.info(f"Starting document upload for user: {request.user.username}, file: {file.name}, directory: {directory.name}")

        # Read file content
        file_content = file.read()
        file_size = len(file_content)
        
        # Validate file size (50MB limit)
        if file_size > 50 * 1024 * 1024:
            return Response(
                {"error": f"File size ({file_size / (1024*1024):.2f} MB) exceeds maximum (50 MB)"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate file using document extractor
        validation_result = document_extractor.validate_file(file_content, file.name)
        if not validation_result['valid']:
            return Response(
                {"error": validation_result['error']},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Extract content using document extractor
        extraction_result = document_extractor.extract_content(file_content, file.name)
        
        if not extraction_result['success']:
            logger.error(f"Content extraction failed: {extraction_result['error']}")
            return Response(
                {"error": f"Content extraction failed: {extraction_result['error']}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        logger.info(f"Successfully extracted content from {file.name}: {extraction_result['word_count']} words")

        # Generate a unique document ID
        document_id = str(uuid.uuid4())
        
        # Upload to S3 with directory support
        s3_result = s3_service.upload_file(
            file_content=file_content,
            filename=file.name,
            directory_name=directory.name,
            content_type=file.content_type or 'application/octet-stream'
        )
        
        if not s3_result['success']:
            logger.error(f"S3 upload failed: {s3_result.get('error')}")
            uploaded_url = f"https://placeholder.s3.amazonaws.com/knowledge-base/{directory.name}/{file.name}"
            s3_error = s3_result.get('error', 'S3 upload failed')
        else:
            uploaded_url = s3_result['url']
            s3_error = None
            logger.info(f"✅ Successfully uploaded {file.name} to S3: {uploaded_url}")
        
        # Initialize Pinecone indexing variables
        pinecone_indexed = False
        pinecone_index_id = None
        pinecone_namespace = None
        chunks_indexed = 0
        pinecone_error = None

        # Index document to Pinecone if service is available
        if PINECONE_AVAILABLE and pinecone_service and pinecone_service.is_available():
            try:
                logger.info(f"Indexing document {file.name} to Pinecone in directory: {directory.name}...")
                
                pinecone_result = pinecone_service.index_document(
                    document_id=document_id,
                    file_name=file.name,
                    file_type=extraction_result['file_type'],
                    content=extraction_result['content'],
                    user_id=request.user.id,
                    username=request.user.username,
                    file_url=uploaded_url,
                    directory_name=directory.name,
                    document_links=extraction_result.get('links', [])
                )
                
                if pinecone_result['success']:
                    pinecone_indexed = True
                    pinecone_index_id = document_id
                    pinecone_namespace = pinecone_result.get('namespace', 'PDFS')
                    chunks_indexed = pinecone_result['chunks_indexed']
                    logger.info(f"✅ Successfully indexed {file.name} to Pinecone with {chunks_indexed} chunks in single PDFS namespace")
                else:
                    pinecone_error = pinecone_result.get('error', 'Unknown Pinecone error')
                    logger.error(f"❌ Pinecone indexing failed: {pinecone_error}")
                    
            except Exception as e:
                pinecone_error = str(e)
                logger.error(f"❌ Pinecone indexing error: {pinecone_error}")
        else:
            pinecone_error = "Pinecone service not available"
            logger.warning(f"⚠️ Pinecone service not available for {file.name}")

        # Save to database
        pdf_document = PDFDocument(
            directory=directory,
            user_id=request.user.id,
            username=request.user.username,
            email=request.user.email,
            file_name=file.name,
            file_type=extraction_result['file_type'],
            content=extraction_result['content'],
            uploaded_url=uploaded_url,
            processing_status="completed",
            pinecone_indexed=pinecone_indexed,
            pinecone_index_id=pinecone_index_id,
            pinecone_namespace=pinecone_namespace,
            file_size=file_size,
            word_count=extraction_result['word_count'],
            created_at=timezone.now(),
        )
        pdf_document.save()
        logger.info(f"Saved document to database with ID: {pdf_document.id}")

        # Prepare response
        response_data = {
            "status": "success",
            "message": f"Document '{file.name}' uploaded and processed successfully to directory '{directory.name}'!",
            "document_id": str(pdf_document.id),
            "directory_id": directory.id,
            "directory_name": directory.name,
            "file_name": file.name,
            "file_type": extraction_result['file_type'],
            "file_size": file_size,
            "word_count": extraction_result['word_count'],
            "uploaded_url": uploaded_url,
            "content_extraction_completed": True,
            "pinecone_indexed": pinecone_indexed,
            "pinecone_namespace": pinecone_namespace,
            "chunks_indexed": chunks_indexed,
            "processing_status": "completed",
            "extraction_method": extraction_result.get('method', 'unknown'),
            "database_record_id": pdf_document.id,
            "created_at": pdf_document.created_at,
        }

        # Add errors if any
        if pinecone_error:
            response_data["pinecone_error"] = pinecone_error
        if s3_error:
            response_data["s3_error"] = s3_error

        return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Unexpected error in document upload: {type(e).__name__} - {e}")
        import traceback
        traceback.print_exc()
        return Response(
            {"error": f"An unexpected error occurred: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# =====================================================
# DOCUMENT LISTING ENDPOINT
# =====================================================

@extend_schema(
    parameters=[
        OpenApiParameter(
            name='directory_id',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Filter documents by directory ID. If not provided, returns all documents.',
            required=False
        )
    ],
    responses={
        200: PDFDocumentListSerializer(many=True),
        404: OpenApiResponse(description="Directory not found"),
        500: OpenApiResponse(description="Internal Server Error")
    },
    description="List documents. Optionally filter by directory_id to get documents from a specific directory."
)
@api_view(["GET"])
@require_sooqsense_organization
def list_documents_api(request):
    """List documents, optionally filtered by directory."""
    try:
        directory_id = request.query_params.get('directory_id', None)
        
        if directory_id:
            # Filter by directory
            try:
                directory = Directory.objects.get(id=directory_id)
                documents = PDFDocument.objects.filter(directory=directory, user_id=request.user.id)
                filter_info = f"directory '{directory.name}'"
            except Directory.DoesNotExist:
                return Response({
                    "error": f"Directory with id {directory_id} not found"
                }, status=status.HTTP_404_NOT_FOUND)
        else:
            # Get all documents for user
            documents = PDFDocument.objects.filter(user_id=request.user.id)
            filter_info = "all directories"
        
        serializer = PDFDocumentListSerializer(documents, many=True)
        
        return Response({
            "status": "success",
            "documents": serializer.data,
            "total": len(serializer.data),
            "filter": filter_info
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error listing documents: {type(e).__name__} - {e}")
        return Response(
            {"error": f"An error occurred: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# =====================================================
# DOCUMENT DELETION ENDPOINT
# =====================================================

@extend_schema(
    responses={
        200: OpenApiResponse(description="Document deleted successfully from database, S3, and Pinecone"),
        404: OpenApiResponse(description="Document not found"),
        500: OpenApiResponse(description="Internal Server Error")
    },
    description="Delete a document completely. This removes the document from the database, S3 bucket, and Pinecone vector index."
)
@api_view(["DELETE"])
@require_sooqsense_organization
def delete_document_api(request, document_id):
    """Delete a document from database, S3, and Pinecone."""
    # Check if user is admin of sooqsense organization
    if not _is_sooqsense_admin(request.user):
        return Response(
            {"error": "Admin privileges required", "detail": "Only sooqsense organization administrators can delete documents."},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        # Get the document
        try:
            document = PDFDocument.objects.get(id=document_id, user_id=request.user.id)
        except PDFDocument.DoesNotExist:
            return Response({
                "error": f"Document with id {document_id} not found or you don't have permission to delete it"
            }, status=status.HTTP_404_NOT_FOUND)
        
        file_name = document.file_name
        directory_name = document.directory.name
        deletion_results = {
            "database": False,
            "s3": False,
            "pinecone": False
        }
        errors = []
        
        # 1. Delete from Pinecone
        if document.pinecone_indexed and PINECONE_AVAILABLE and pinecone_service:
            try:
                logger.info(f"Deleting document {document.pinecone_index_id} (file: {file_name}) from Pinecone...")
                pinecone_result = pinecone_service.delete_document(
                    document_id=document.pinecone_index_id,
                    namespace='PDFS',  # Always use single PDFS namespace
                    file_name=file_name
                )
                
                if pinecone_result['success']:
                    deletion_results['pinecone'] = True
                    logger.info(f"✅ Deleted {pinecone_result.get('vectors_deleted', 0)} vectors from Pinecone")
                else:
                    errors.append(f"Pinecone deletion failed: {pinecone_result.get('error')}")
                    logger.warning(f"⚠️ Pinecone deletion had issues: {pinecone_result.get('error')}")
            except Exception as e:
                errors.append(f"Pinecone deletion error: {str(e)}")
                logger.error(f"❌ Error deleting from Pinecone: {e}")
        else:
            deletion_results['pinecone'] = True  # Mark as success if not indexed
        
        # 2. Delete from S3
        s3_key = document.get_s3_key()
        if s3_key and s3_service.is_available():
            try:
                logger.info(f"Deleting file from S3: {s3_key}...")
                s3_result = s3_service.delete_file(s3_key)
                
                if s3_result['success']:
                    deletion_results['s3'] = True
                    logger.info(f"✅ Deleted file from S3: {s3_key}")
                else:
                    errors.append(f"S3 deletion failed: {s3_result.get('error')}")
                    logger.warning(f"⚠️ S3 deletion failed: {s3_result.get('error')}")
            except Exception as e:
                errors.append(f"S3 deletion error: {str(e)}")
                logger.error(f"❌ Error deleting from S3: {e}")
        else:
            deletion_results['s3'] = True  # Mark as success if no S3 key or service unavailable
        
        # 3. Delete from database
        try:
            document.delete()
            deletion_results['database'] = True
            logger.info(f"✅ Deleted document from database: {file_name}")
        except Exception as e:
            errors.append(f"Database deletion error: {str(e)}")
            logger.error(f"❌ Error deleting from database: {e}")
            return Response({
                "error": "Failed to delete document from database",
                "details": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Prepare response
        response_data = {
            "status": "success",
            "message": f"Document '{file_name}' deleted successfully from directory '{directory_name}'",
            "file_name": file_name,
            "directory_name": directory_name,
            "deletion_summary": {
                "database": "✅ Deleted" if deletion_results['database'] else "❌ Failed",
                "s3_bucket": "✅ Deleted" if deletion_results['s3'] else "❌ Failed",
                "pinecone_index": "✅ Deleted" if deletion_results['pinecone'] else "❌ Failed"
            }
        }
        
        if errors:
            response_data['warnings'] = errors
            response_data['partial_deletion'] = True
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Unexpected error deleting document: {type(e).__name__} - {e}")
        import traceback
        traceback.print_exc()
        return Response(
            {"error": f"An unexpected error occurred: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
