import logging
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiResponse
from django.contrib.auth import get_user_model
from .services.clerk_services import ClerkUserService

User = get_user_model()
logger = logging.getLogger(__name__)


@extend_schema(
    request={
        'type': 'object',
        'properties': {
            'token': {
                'type': 'string',
                'description': 'Clerk JWT token from frontend authentication'
            }
        },
        'required': ['token']
    },
    responses={
        200: OpenApiResponse(
            description="Authentication successful - User verified and synced with database",
            examples={
                'application/json': {
                    'success': True,
                    'message': 'User authenticated successfully',
                    'user': {
                        'id': 1,
                        'username': 'user123',
                        'email': 'user@example.com',
                        'first_name': 'John',
                        'last_name': 'Doe',
                        'clerk_user_id': 'user_2abc123xyz',
                        'organization_ids': ['org_123', 'org_456'],
                        'organization_names': ['sooqsense', 'acme-corp'],
                        'organization_roles': ['admin', 'member'],
                        'organization_id': 'org_123',
                        'organization_name': 'sooqsense',
                        'organization_role': 'admin',
                        'created_at': '2024-01-01T00:00:00Z'
                    }
                }
            }
        ),
        400: OpenApiResponse(
            description="Invalid or missing token",
            examples={
                'application/json': {
                    'success': False,
                    'message': 'Token is required'
                }
            }
        ),
        401: OpenApiResponse(
            description="Invalid or expired token",
            examples={
                'application/json': {
                    'success': False,
                    'message': 'Invalid or expired token'
                }
            }
        ),
        500: OpenApiResponse(
            description="Internal server error"
        )
    },
    description="""
    **Primary Authentication Endpoint for Clerk Integration**
    
    This endpoint verifies Clerk JWT tokens and synchronizes user data with the backend database.
    
    **Authentication Flow:**
    1. Frontend authenticates user with Clerk (using Clerk's SDK)
    2. Clerk returns a JWT token to the frontend
    3. Frontend sends the JWT token to this endpoint via POST request
    4. Backend verifies the token with Clerk's JWKS
    5. Backend creates or updates the user in the database
    6. Backend returns the user data to the frontend
    
    **Token Format:**
    Send the token in the request body as:
    ```json
    {
        "token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
    }
    ```
    
    **Response:**
    Returns complete user profile including organization memberships.
    The user data can be used to maintain session state on the frontend.
    
    **Note:** This endpoint does NOT require authentication (AllowAny).
    It's the entry point for establishing authenticated sessions.
    """
)
@api_view(['POST'])
@permission_classes([AllowAny])
def verify_token_view(request):
    """Verify JWT token and return user information"""
    try:
        token = request.data.get('token')
        
        if not token:
            return Response({
                'success': False,
                'message': 'Token is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        clerk_user_service = ClerkUserService()
        user = clerk_user_service.authenticate_user(token)
        
        if not user:
            logger.warning("Token verification failed - no user returned")
            return Response({
                'success': False,
                'message': 'Invalid or expired token'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user_data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'clerk_user_id': user.clerk_user_id,
            # Multiple organizations support
            'organization_ids': user.organization_ids or [],
            'organization_names': user.organization_names or [],
            'organization_roles': user.organization_roles or [],
            # Legacy fields for backward compatibility
            'organization_id': user.organization_id,
            'organization_name': user.organization_name,
            'organization_role': user.organization_role
        }
        
        logger.info("=" * 80)
        logger.info("VERIFY TOKEN VIEW - Returning user data to frontend:")
        logger.info("=" * 80)
        for key, value in user_data.items():
            logger.info(f"  {key}: {value}")
        logger.info("=" * 80)
        
        return Response({
            'success': True,
            'message': 'User authenticated successfully',
            'user': user_data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        return Response({
            'success': False,
            'message': 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    responses={
        200: OpenApiResponse(
            description="User profile retrieved successfully",
            examples={
                'application/json': {
                    'success': True,
                    'user': {
                        'id': 1,
                        'username': 'user123',
                        'email': 'user@example.com',
                        'clerk_user_id': 'clerk_123',
                        'organization_id': 'org_123',
                        'organization_name': 'My Company',
                        'organization_role': 'admin',
                        'created_at': '2024-01-01T00:00:00Z'
                    }
                }
            }
        ),
        401: OpenApiResponse(
            description="Unauthorized"
        )
    },
    description="Get current user profile information"
)
@api_view(['GET'])
def profile_view(request):
    """Get current user profile"""
    try:
        user = request.user
        
        return Response({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'clerk_user_id': user.clerk_user_id,
                # Multiple organizations support
                'organization_ids': user.organization_ids or [],
                'organization_names': user.organization_names or [],
                'organization_roles': user.organization_roles or [],
                # Legacy fields for backward compatibility
                'organization_id': user.organization_id,
                'organization_name': user.organization_name,
                'organization_role': user.organization_role,
                'created_at': user.created_at.isoformat()
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Profile error: {e}")
        return Response({
            'success': False,
            'message': 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    request={
        'type': 'object',
        'properties': {
            'organization_name': {
                'type': 'string',
                'description': 'Organization name to switch to'
            }
        },
        'required': ['organization_name']
    },
    responses={
        200: OpenApiResponse(
            description="Organization switched successfully",
            examples={
                'application/json': {
                    'success': True,
                    'message': 'Organization switched successfully',
                    'user': {
                        'id': 1,
                        'username': 'user123',
                        'email': 'user@example.com',
                        'organization_id': 'org_123',
                        'organization_name': 'sooqsense',
                        'organization_role': 'admin'
                    }
                }
            }
        ),
        400: OpenApiResponse(
            description="Invalid organization",
            examples={
                'application/json': {
                    'success': False,
                    'message': 'User is not a member of this organization'
                }
            }
        ),
        401: OpenApiResponse(
            description="Unauthorized"
        )
    },
    description="Switch user's active organization context"
)
@api_view(['POST'])
def switch_organization_view(request):
    """Switch user's active organization context"""
    try:
        user = request.user
        organization_name = request.data.get('organization_name')
        
        if not organization_name:
            return Response({
                'success': False,
                'message': 'Organization name is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if user is a member of this organization
        user_orgs = user.organization_names or []
        
        if organization_name not in user_orgs:
            logger.warning(f"User {user.username} tried to switch to unauthorized org: {organization_name}")
            return Response({
                'success': False,
                'message': 'User is not a member of this organization',
                'available_organizations': user_orgs
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get the index of the organization
        org_index = user_orgs.index(organization_name)
        
        # Update user's current organization context
        org_ids = user.organization_ids or []
        org_roles = user.organization_roles or []
        
        if org_index < len(org_ids):
            user.organization_id = org_ids[org_index]
        if org_index < len(org_roles):
            user.organization_role = org_roles[org_index]
        
        user.organization_name = organization_name
        user.save()
        
        logger.info(f"✅ User {user.username} switched to organization: {organization_name}")
        
        return Response({
            'success': True,
            'message': 'Organization switched successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'clerk_user_id': user.clerk_user_id,
                # Multiple organizations support
                'organization_ids': user.organization_ids or [],
                'organization_names': user.organization_names or [],
                'organization_roles': user.organization_roles or [],
                # Current active organization
                'organization_id': user.organization_id,
                'organization_name': user.organization_name,
                'organization_role': user.organization_role
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Organization switch error: {e}")
        return Response({
            'success': False,
            'message': 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
