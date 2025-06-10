from django.shortcuts import render, redirect
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication
import hashlib
import requests
import json
import os
from django.urls import reverse
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv
from django.db import transaction

# Reload .env file to ensure fresh environment variables
# Get the base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent
# Load environment variables from .env file
load_dotenv(os.path.join(BASE_DIR, '.env'))

from .models import User
from .serializers import (
    UserSerializer, RegisterSerializer, LoginSerializer,
    CustomTokenObtainPairSerializer, TokenRefreshResponseSerializer,
    GoogleAuthSerializer, GoogleLoginRedirectSerializer,
    LinkedInAuthSerializer, LinkedInLoginRedirectSerializer
)

# Google OAuth settings - these should be set in environment variables
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')
GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI', '')

LINKEDIN_CLIENT_ID = os.environ.get('LINKEDIN_CLIENT_ID', '')
LINKEDIN_CLIENT_SECRET = os.environ.get('LINKEDIN_CLIENT_SECRET', '')
LINKEDIN_REDIRECT_URI = os.environ.get('LINKEDIN_REDIRECT_URI', '')
print(LINKEDIN_REDIRECT_URI)

class UserListView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    
    def get(self, request, *args, **kwargs):
        user = request.user
        serializer = self.get_serializer(user)
        return Response(serializer.data)

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        return Response({
            'success': True,
            'message': 'User registered successfully',
            'username': user.username,
            'email': user.email
        }, status=status.HTTP_201_CREATED)

class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = CustomTokenObtainPairSerializer
    
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            # Get validated data from serializer
            validated_data = serializer.validated_data
            
            # Get the user from the request data to save tokens
            email = request.data.get('email')
            user = User.objects.get(email=email)
            
            # Save JWT tokens to database
            access_token = validated_data['access']
            refresh_token = validated_data['refresh']
            
            # Calculate token expiration (JWT access tokens typically expire in 5 minutes by default)
            from rest_framework_simplejwt.settings import api_settings
            access_token_lifetime = api_settings.ACCESS_TOKEN_LIFETIME
            token_expires_at = timezone.now() + access_token_lifetime
            
            # Update user with tokens
            user.simple_login_access_token = access_token
            user.simple_login_refresh_token = refresh_token
            user.simple_login_token_expires_at = token_expires_at
            user.save(update_fields=['simple_login_access_token', 'simple_login_refresh_token', 'simple_login_token_expires_at'])
            
            # Refresh user data to get updated token fields
            user.refresh_from_db()
            
            # Create custom response with updated user data
            response_data = {
                'success': True,
                'message': 'Login successful',
                'refresh': refresh_token,
                'access': access_token,
                'user': UserSerializer(user).data  # Use fresh user data with tokens
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'success': False,
                'message': 'Login failed',
                'error': str(e)
            }, status=status.HTTP_401_UNAUTHORIZED)

class GoogleLoginRedirectView(APIView):
    """
    Redirect user to Google OAuth login page
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = GoogleLoginRedirectSerializer
    
    def get(self, request):
        # Construct Google OAuth URL
        google_auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
        params = {
            "client_id": GOOGLE_CLIENT_ID,
            "redirect_uri": GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": "email profile",
            "access_type": "offline",
            "prompt": "consent"
        }
        
        # Construct full URL with parameters
        auth_url = f"{google_auth_url}?{'&'.join([f'{key}={value}' for key, value in params.items()])}"
        
        # Return the URL for frontend to redirect
        return Response({
            "auth_url": auth_url
        })

class GoogleLoginCallbackView(APIView):
    """
    Handle callback from Google OAuth login
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = GoogleAuthSerializer
    
    def get(self, request):
        serializer = self.serializer_class(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        
        code = serializer.validated_data.get('code')
        error = serializer.validated_data.get('error')
        
        if error:
            return Response({
                'success': False,
                'message': 'Google login failed',
                'error': error
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not code:
            return Response({
                'success': False,
                'message': 'Google login failed',
                'error': 'No authorization code provided'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Exchange code for tokens
        try:
            token_url = "https://oauth2.googleapis.com/token"
            token_data = {
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code"
            }
            
            token_response = requests.post(token_url, data=token_data)
            token_json = token_response.json()
            
            if 'error' in token_json:
                return Response({
                    'success': False,
                    'message': 'Google login failed',
                    'error': token_json.get('error_description', token_json['error'])
                }, status=status.HTTP_400_BAD_REQUEST)
                
            # Get user info from Google
            id_token = token_json.get('id_token')
            user_info_url = "https://www.googleapis.com/oauth2/v3/userinfo"
            user_info_response = requests.get(
                user_info_url,
                headers={"Authorization": f"Bearer {token_json['access_token']}"}
            )
            user_info = user_info_response.json()
            
            # Get or create user
            email = user_info.get('email')
            google_profile_id = user_info.get('sub')  # Google's user ID
            
            if not email:
                return Response({
                    'success': False,
                    'message': 'Google login failed',
                    'error': 'Email not provided by Google'
                }, status=status.HTTP_400_BAD_REQUEST)
                
            # Check if user exists
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                # Create a new user
                username = user_info.get('name', email.split('@')[0])
                user = User.objects.create(
                    username=username,
                    email=email,
                    # Use a random hashed password since user will login via Google
                    password=hashlib.sha256(os.urandom(32).hex().encode()).hexdigest()
                )
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            jwt_access_token = str(refresh.access_token)
            jwt_refresh_token = str(refresh)
            
            # Calculate JWT token expiration
            from rest_framework_simplejwt.settings import api_settings
            access_token_lifetime = api_settings.ACCESS_TOKEN_LIFETIME
            jwt_token_expires_at = timezone.now() + access_token_lifetime
            
            # Save JWT tokens and profile ID to database in Google-specific fields
            user.google_login_access_token = jwt_access_token
            user.google_login_refresh_token = jwt_refresh_token
            user.google_login_token_expires_at = jwt_token_expires_at
            user.google_profile_id = google_profile_id
            user.save(update_fields=['google_login_access_token', 'google_login_refresh_token', 'google_login_token_expires_at', 'google_profile_id'])
            
            # Return tokens
            response_data = {
                'success': True,
                'message': 'Google login successful',
                'refresh': jwt_refresh_token,
                'access': jwt_access_token,
                'user': UserSerializer(user).data
            }
            
            # For APIs, return the response
            if request.accepted_renderer.format == 'json':
                return Response(response_data)
                
            # For browser flow, redirect to frontend with tokens
            frontend_url = os.environ.get('FRONTEND_URL')
            redirect_url = f"{frontend_url}/login/success?access={jwt_access_token}&refresh={jwt_refresh_token}"
            return redirect(redirect_url)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': 'Google login failed',
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

class CustomTokenRefreshView(TokenRefreshView):
    """
    Custom token refresh view with our response serializer
    """
    serializer_class = TokenRefreshResponseSerializer

class LinkedInLoginRedirectView(APIView):
    """
    Redirect user to LinkedIn OAuth login page
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = LinkedInLoginRedirectSerializer
    
    def get(self, request):
        # Construct LinkedIn OAuth URL
        linkedin_auth_url = "https://www.linkedin.com/oauth/v2/authorization"
        params = {
            "client_id": LINKEDIN_CLIENT_ID,
            "redirect_uri": LINKEDIN_REDIRECT_URI,
            "response_type": "code",
            "scope": "openid profile w_member_social email",
            "state": hashlib.sha256(os.urandom(32).hex().encode()).hexdigest()
        }
        
        # Construct full URL with parameters
        auth_url = f"{linkedin_auth_url}?{'&'.join([f'{key}={value}' for key, value in params.items()])}"
        
        # Return the URL for frontend to redirect
        return Response({
            "auth_url": auth_url
        })

class LinkedInLoginCallbackView(APIView):
    """
    Handle callback from LinkedIn OAuth login
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = LinkedInAuthSerializer
    
    def get(self, request):
        print("🔥 LinkedIn callback called!")
        print(f"Query params: {request.query_params}")
        
        serializer = self.serializer_class(data=request.query_params)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'message': 'Invalid callback parameters',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        code = serializer.validated_data.get('code')
        error = serializer.validated_data.get('error')
        
        if error:
            return Response({
                'success': False,
                'message': 'LinkedIn login failed',
                'error': error,
                'error_description': request.query_params.get('error_description', '')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not code:
            return Response({
                'success': False,
                'message': 'LinkedIn login failed',
                'error': 'No authorization code provided'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Exchange code for tokens
        try:
            token_url = "https://www.linkedin.com/oauth/v2/accessToken"
            token_data = {
                "code": code,
                "client_id": LINKEDIN_CLIENT_ID,
                "client_secret": LINKEDIN_CLIENT_SECRET,
                "redirect_uri": LINKEDIN_REDIRECT_URI,
                "grant_type": "authorization_code"
            }
            
            token_response = requests.post(token_url, data=token_data)
            
            if token_response.status_code != 200:
                return Response({
                    'success': False,
                    'message': 'LinkedIn token exchange failed',
                    'error': f'HTTP {token_response.status_code}: {token_response.text}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            token_json = token_response.json()
            
            if 'error' in token_json:
                return Response({
                    'success': False,
                    'message': 'LinkedIn login failed',
                    'error': token_json.get('error_description', token_json['error'])
                }, status=status.HTTP_400_BAD_REQUEST)
                
            # Get user profile from LinkedIn
            access_token = token_json.get('access_token')
            expires_in = token_json.get('expires_in', 5184000)  # Default to 60 days
            
            # Extract the granted scopes from the token response
            # LinkedIn returns the granted scopes in the token response
            granted_scopes = token_json.get('scope', 'openid profile email')  # Default scopes if not provided
            
            print(f"🔍 TOKEN RESPONSE DEBUG:")
            print(f"   Full token response: {token_json}")
            print(f"   Granted scopes: {granted_scopes}")
            print(f"   Access token: {access_token[:20]}..." if access_token else "No access token")
            
            # Calculate token expiration time
            token_expires_at = timezone.now() + timedelta(seconds=expires_in)
            
            # Get user profile - using userinfo endpoint for OpenID Connect flow
            profile_url = "https://api.linkedin.com/v2/userinfo"
            
            profile_response = requests.get(
                profile_url,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if profile_response.status_code != 200:
                return Response({
                    'success': False,
                    'message': 'Failed to fetch LinkedIn profile',
                    'error': f'HTTP {profile_response.status_code}: {profile_response.text}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            profile_data = profile_response.json()
            print(f"LinkedIn profile data received: {profile_data}")
            
            # Extract profile info using OpenID Connect fields
            try:
                # OpenID Connect provides standardized fields
                name = profile_data.get('name', '')
                email = profile_data.get('email', '')
                linkedin_id = profile_data.get('sub', '') # 'sub' is the standard ID field in OpenID Connect
                
                print(f"Extracted data - Name: {name}, Email: {email}, LinkedIn ID: {linkedin_id}")
                print(f"Access token received: {access_token[:20]}..." if access_token else "No access token")
                
                if not linkedin_id:
                    return Response({
                        'success': False,
                        'message': 'LinkedIn login failed',
                        'error': 'Failed to retrieve LinkedIn ID'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                # If email wasn't provided, generate one
                if not email:
                    email = f"linkedin_{linkedin_id}@linkedin.com"
                
                # Generate a username if needed
                username = name if name else f"linkedin_{linkedin_id}"
                
            except (KeyError, IndexError):
                return Response({
                    'success': False,
                    'message': 'LinkedIn login failed',
                    'error': 'Failed to retrieve user information'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if user exists - use explicit transaction handling
            user = None
            try:
                # First try to find by our constructed email
                user = User.objects.get(email=email)
                print(f"✅ Found existing user: {user.email}")
                
                # Update existing user's LinkedIn token info
                print(f"🔄 Updating user with LinkedIn data...")
                print(f"   Token: {access_token[:20]}...")
                print(f"   Profile ID: {linkedin_id}")
                print(f"   Expires: {token_expires_at}")
                
                user.linkedin_access_token = access_token
                user.linkedin_profile_id = linkedin_id
                user.linkedin_token_expires_at = token_expires_at
                user.linkedin_scopes = granted_scopes
                
                # Force save with update_fields to ensure the fields are updated
                user.save(update_fields=['linkedin_access_token', 'linkedin_profile_id', 'linkedin_token_expires_at', 'linkedin_scopes'])
                print(f"✅ User updated successfully")
                
            except User.DoesNotExist:
                print(f"➕ Creating new user: {email}")
                
                # Create a new user
                user = User.objects.create(
                    username=username,
                    email=email,
                    # Use a random hashed password
                    password=hashlib.sha256(os.urandom(32).hex().encode()).hexdigest(),
                    # Store LinkedIn token info
                    linkedin_access_token=access_token,
                    linkedin_profile_id=linkedin_id,
                    linkedin_token_expires_at=token_expires_at,
                    linkedin_scopes=granted_scopes
                )
                print(f"✅ Created new user with ID: {user.id}")
            
            # Ensure the data is committed to database
            if user:
                user.save(update_fields=['linkedin_access_token', 'linkedin_profile_id', 'linkedin_token_expires_at', 'linkedin_scopes'])
                print(f"🔄 Final save completed for user {user.id}")
            
            # Verify the token was saved
            user.refresh_from_db()
            print(f"🔍 VERIFICATION:")
            print(f"   User ID: {user.id}")
            print(f"   Email: {user.email}")
            print(f"   Token in DB: {user.linkedin_access_token[:20] + '...' if user.linkedin_access_token else '❌ NOT SAVED'}")
            print(f"   Profile ID in DB: {user.linkedin_profile_id or '❌ NOT SAVED'}")
            print(f"   Expires at in DB: {user.linkedin_token_expires_at or '❌ NOT SAVED'}")
            print(f"   Scopes in DB: {user.linkedin_scopes or '❌ NOT SAVED'}")
            
            if not user.linkedin_access_token:
                print("🚨 ERROR: LinkedIn token was not saved to database!")
                # Try to save again with full save (not just update_fields)
                user.linkedin_access_token = access_token
                user.linkedin_profile_id = linkedin_id
                user.linkedin_token_expires_at = token_expires_at
                user.linkedin_scopes = granted_scopes
                user.save()  # Full save without update_fields
                user.refresh_from_db()
                print(f"🔄 Retry save result: {user.linkedin_access_token[:20] + '...' if user.linkedin_access_token else '❌ STILL NOT SAVED'}")
                
                # If still not saved, try raw SQL
                if not user.linkedin_access_token:
                    print("🚨 Trying raw SQL update...")
                    from django.db import connection
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "UPDATE users SET linkedin_access_token = %s, linkedin_profile_id = %s, linkedin_token_expires_at = %s, linkedin_scopes = %s WHERE id = %s",
                            [access_token, linkedin_id, token_expires_at, granted_scopes, user.id]
                        )
                        print(f"🔄 Raw SQL executed, affected rows: {cursor.rowcount}")
                    
                    user.refresh_from_db()
                    print(f"🔄 After raw SQL: {user.linkedin_access_token[:20] + '...' if user.linkedin_access_token else '❌ STILL NOT SAVED'}")
            
            # Final verification before generating tokens
            user.refresh_from_db()
            print(f"🔍 FINAL VERIFICATION BEFORE TOKEN GENERATION:")
            print(f"   Token in DB: {user.linkedin_access_token[:20] + '...' if user.linkedin_access_token else '❌ NOT SAVED'}")
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            # Return tokens
            response_data = {
                'success': True,
                'message': 'LinkedIn login successful',
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': UserSerializer(user).data
            }
            
            print(f"🔍 RESPONSE DATA PREPARED:")
            print(f"   User data in response: {response_data['user']}")
            
            # For APIs, return the response
            if request.accepted_renderer.format == 'json':
                print("🔄 Returning JSON response")
                return Response(response_data)
                
            # For browser flow, redirect to frontend with tokens
            frontend_url = os.environ.get('FRONTEND_URL')
            redirect_url = f"{frontend_url}/login/success?access={str(refresh.access_token)}&refresh={str(refresh)}"
            print(f"🔄 Redirecting to: {redirect_url}")
            return redirect(redirect_url)
            
        except Exception as e:
            print(f"🚨 EXCEPTION in LinkedIn callback: {type(e).__name__} - {e}")
            import traceback
            traceback.print_exc()
            return Response({
                'success': False,
                'message': 'LinkedIn login failed',
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class LinkedInTokenView(APIView):
    """
    Get the current user's LinkedIn access token for API calls
    """
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    
    def get(self, request):
        user = request.user
        
        if not user.linkedin_access_token:
            return Response({
                'success': False,
                'message': 'No LinkedIn access token found. Please login with LinkedIn first.',
                'has_token': False
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Check if token is expired
        if user.linkedin_token_expires_at and user.linkedin_token_expires_at < timezone.now():
            return Response({
                'success': False,
                'message': 'LinkedIn access token has expired. Please login with LinkedIn again.',
                'has_token': False,
                'expired': True
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        return Response({
            'success': True,
            'message': 'LinkedIn access token retrieved successfully',
            'has_token': True,
            'linkedin_access_token': user.linkedin_access_token,
            'linkedin_profile_id': user.linkedin_profile_id,
            'expires_at': user.linkedin_token_expires_at,
            'expired': False
        }, status=status.HTTP_200_OK)

