from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from drf_spectacular.utils import extend_schema, OpenApiResponse
import logging

# Import models
from .models import PDFDocument

# Set up logging
logger = logging.getLogger(__name__)

# Import local services
from .service.pdf_extractor.pdf_extractor import document_extractor

# Import Pinecone service with error handling
try:
    from .service.pinecone_indexing.pinecone_indexing import PineconeService
    pinecone_service = PineconeService()
    PINECONE_AVAILABLE = True
    logger.info("✅ Pinecone service initialized successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize Pinecone service: {str(e)}")
    pinecone_service = None
    PINECONE_AVAILABLE = False


@extend_schema(
    request={
        'multipart/form-data': {
            'type': 'object',
            'properties': {
                'file': {
                    'type': 'string',
                    'format': 'binary',
                    'description': 'Document file to upload. Supported formats: PDF, DOCX, MD, TXT. Maximum size: 50MB.'
                }
            },
            'required': ['file']
        }
    },
    responses={
        200: OpenApiResponse(
            description="Document uploaded and processed successfully.",
        ),
        400: OpenApiResponse(
            description="Bad Request - Invalid file or processing error."
        ),
        500: OpenApiResponse(
            description="Internal Server Error / Processing Failed."
        ),
    },
    description="Upload a document (PDF, DOCX, MD, TXT), extract its content, index it in Pinecone for searchability, and store it in S3. The document will be available for querying through the chat API.",
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def upload_pdf_api(request):
    """Upload and process document files (PDF, DOCX, MD, TXT)."""
    try:
        if 'file' not in request.FILES:
            return Response(
                {"error": "No file provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        file = request.FILES['file']
        logger.info(f"Starting document upload for user: {request.user.username}, file: {file.name}")

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
        import uuid
        document_id = str(uuid.uuid4())
        
        # For now, we'll simulate S3 upload (you can integrate actual S3 upload here)
        uploaded_url = f"https://s3.amazonaws.com/bucket/documents/{document_id}/{file.name}"
        
        # Initialize Pinecone indexing variables
        pinecone_indexed = False
        pinecone_index_id = None
        chunks_indexed = 0
        pinecone_error = None

        # Index document to Pinecone if service is available
        if PINECONE_AVAILABLE and pinecone_service and pinecone_service.is_available():
            try:
                logger.info(f"Indexing document {file.name} to Pinecone...")
                
                pinecone_result = pinecone_service.index_document(
                    document_id=document_id,
                    file_name=file.name,
                    file_type=extraction_result['file_type'],
                    content=extraction_result['content'],
                    user_id=request.user.id,
                    username=request.user.username,
                    file_url=uploaded_url,
                    document_links=extraction_result.get('links', [])
                )
                
                if pinecone_result['success']:
                    pinecone_indexed = True
                    pinecone_index_id = document_id
                    chunks_indexed = pinecone_result['chunks_indexed']
                    logger.info(f"✅ Successfully indexed {file.name} to Pinecone with {chunks_indexed} chunks")
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
            file_size=file_size,
            word_count=extraction_result['word_count'],
            created_at=timezone.now(),
        )
        pdf_document.save()
        logger.info(f"Saved document to database with ID: {pdf_document.id}")

        # Prepare response
        response_data = {
            "status": "success",
            "message": f"Document '{file.name}' uploaded and processed successfully!",
            "document_id": str(pdf_document.id),
            "file_name": file.name,
            "file_type": extraction_result['file_type'],
            "file_size": file_size,
            "word_count": extraction_result['word_count'],
            "uploaded_url": uploaded_url,
            "content_extraction_completed": True,
            "pinecone_indexing_completed": pinecone_indexed,
            "chunks_indexed": chunks_indexed,
            "processing_status": "completed",
            "extraction_method": extraction_result.get('method', 'unknown'),
            "database_record_id": pdf_document.id,
            "created_at": pdf_document.created_at,
        }

        # Add Pinecone error if indexing failed
        if pinecone_error:
            response_data["pinecone_error"] = pinecone_error

        return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Unexpected error in document upload: {type(e).__name__} - {e}")
        import traceback
        traceback.print_exc()
        return Response(
            {"error": f"An unexpected error occurred: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
