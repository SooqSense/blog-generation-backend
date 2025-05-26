from rest_framework import serializers
from .models import User
import hashlib
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'linkedin_access_token', 'linkedin_profile_id', 'linkedin_token_expires_at']


class RegisterSerializer(serializers.ModelSerializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def create(self, validated_data):
        # Hash the password for storage
        hashed_password = hashlib.sha256(validated_data['password'].encode()).hexdigest()
        
        user = User.objects.create(
            username=validated_data['username'],
            email=validated_data['email'],
            password=hashed_password
        )
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True)


class CustomTokenObtainPairSerializer(serializers.Serializer):
    """
    Custom token serializer that validates against our User model
    """
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        if not email or not password:
            raise serializers.ValidationError({'error': 'Email and password are required'})
            
        # Hash the password for verification
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        
        try:
            user = User.objects.get(email=email, password=hashed_password)
        except User.DoesNotExist:
            raise serializers.ValidationError({'error': 'Invalid credentials'})
            
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UserSerializer(user).data
        }


class GoogleAuthSerializer(serializers.Serializer):
    """
    Serializer for handling Google auth code
    """
    code = serializers.CharField(required=False)
    error = serializers.CharField(required=False)
    state = serializers.CharField(required=False)
    
    # For handling Google token directly from frontend
    id_token = serializers.CharField(required=False)


class GoogleLoginRedirectSerializer(serializers.Serializer):
    """
    Serializer for Google login redirect - not actually used but needed for schema generation
    """
    auth_url = serializers.URLField(read_only=True)


class TokenRefreshResponseSerializer(serializers.Serializer):
    """
    Serializer for token refresh response
    """
    access = serializers.CharField()
    refresh = serializers.CharField(required=False)


class LinkedInAuthSerializer(serializers.Serializer):
    """
    Serializer for handling LinkedIn auth code
    """
    code = serializers.CharField(required=False)
    error = serializers.CharField(required=False)
    state = serializers.CharField(required=False)
    
    # For handling LinkedIn token directly from frontend
    access_token = serializers.CharField(required=False)


class LinkedInLoginRedirectSerializer(serializers.Serializer):
    """
    Serializer for LinkedIn login redirect
    """
    auth_url = serializers.URLField(read_only=True) 