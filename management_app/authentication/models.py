from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone

class UserManager(BaseUserManager):
    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, username, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(max_length=255, unique=True)
    # password field is inherited from AbstractBaseUser
    # is_active, is_staff are inherited from AbstractBaseUser or PermissionsMixin
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False) # Required for admin access

    # LinkedIn integration fields
    linkedin_access_token = models.TextField(blank=True, null=True, help_text="LinkedIn OAuth access token")
    linkedin_profile_id = models.CharField(max_length=100, blank=True, null=True, help_text="LinkedIn profile ID")
    linkedin_token_expires_at = models.DateTimeField(blank=True, null=True, help_text="When LinkedIn token expires")
    linkedin_scopes = models.TextField(blank=True, null=True, help_text="LinkedIn OAuth granted scopes (space-separated)")

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'  # Use email for login
    REQUIRED_FIELDS = ['username'] # Fields required when creating a user via createsuperuser

    class Meta:
        db_table = 'users'
        verbose_name = 'user'
        verbose_name_plural = 'users'

    def __str__(self):
        return self.email
