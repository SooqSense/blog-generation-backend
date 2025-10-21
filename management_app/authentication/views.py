import logging
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiResponse
from django.contrib.auth import get_user_model
from .services.clerk_service import ClerkJWTAuthService, ClerkAPIService

User = get_user_model()
logger = logging.getLogger(__name__)


@extend_schema(
    request={
        'type': 'object',
        'properties': {
            'email': {
                'type': 'string',
                'format': 'email',
                'description': 'User email address'
            },
            'password': {
                'type': 'string',
                'description': 'User password'
            }
        },
        'required': ['email', 'password']
    },
    responses={
        200: OpenApiResponse(
            description="Login successful",
            examples={
                'application/json': {
                    'success': True,
                    'message': 'Login successful',
                    'token': 'jwt_token_here',
                    'user': {
                        'id': 1,
                        'username': 'user123',
                        'email': 'user@example.com',
                        'clerk_user_id': 'clerk_123'
                    }
                }
            }
        ),
        400: OpenApiResponse(
            description="Invalid credentials",
            examples={
                'application/json': {
                    'success': False,
                    'message': 'Invalid email or password'
                }
            }
        ),
        500: OpenApiResponse(
            description="Internal server error"
        )
    },
    description="Authenticate user with email and password, return Clerk JWT token"
)
@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """DEPRECATED: This endpoint should not be used with proper Clerk authentication.
    
    Proper Clerk workflow:
    1. Frontend authenticates with Clerk directly
    2. Clerk returns JWT token
    3. Frontend sends Clerk JWT to /auth/verify/ endpoint
    4. Backend verifies Clerk JWT and creates/updates local user
    """
    return Response({
        'success': False,
        'message': 'This endpoint is deprecated. Please use Clerk authentication on the frontend and send the JWT token to /auth/verify/ endpoint.',
        'instructions': {
            'step1': 'Authenticate with Clerk on frontend',
            'step2': 'Get JWT token from Clerk',
            'step3': 'Send JWT token to /auth/verify/ endpoint',
            'step4': 'Backend will verify token and create/update user'
        }
    }, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    request={
        'type': 'object',
        'properties': {
            'token': {
                'type': 'string',
                'description': 'JWT token to verify'
            }
        },
        'required': ['token']
    },
    responses={
        200: OpenApiResponse(
            description="Token verification successful",
            examples={
                'application/json': {
                    'success': True,
                    'message': 'Token is valid',
                    'user': {
                        'id': 1,
                        'username': 'user123',
                        'email': 'user@example.com',
                        'clerk_user_id': 'clerk_123',
                        'organization_id': 'org_123',
                        'organization_name': 'My Company',
                        'organization_role': 'admin'
                    }
                }
            }
        ),
        400: OpenApiResponse(
            description="Invalid token",
            examples={
                'application/json': {
                    'success': False,
                    'message': 'Invalid or expired token'
                }
            }
        )
    },
    description="Verify JWT token and return user information"
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
        
        clerk_auth = ClerkJWTAuthService()
        user = clerk_auth.authenticate_user(token)
        
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
            'message': 'Token is valid',
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
