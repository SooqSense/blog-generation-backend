from pathlib import Path
import os
from dotenv import load_dotenv
import sys

# Django Setup Guard - Prevent premature setup during configuration
# This prevents conflicts when Django configuration is being read
_DJANGO_SETTINGS_LOADING = True

# Load environment variables from .env file
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Add the project root directory to Python path for tools module imports
PROJECT_ROOT = BASE_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
    print(f"📁 Added project root to Python path: {PROJECT_ROOT}")

SECRET_KEY = "django-insecure-dummy-key"  # Replace with a real secret key

DEBUG = True

ALLOWED_HOSTS = ["*"]

AUTH_USER_MODEL = "authentication.User"

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Modular apps
    "blog_generator",
    "ai_news",
    "image_generator",
    "linkedin_post_generator",
    "schedule_linkedin_post",
    "ai_trends",
    "knowledge_base",
    "chatbot",
    "authentication",  # Authentication app
    "upwork_proposal_generator",  # Upwork proposal generator app
    # Integration apps
    "langsmith_integration",  # LangSmith integration for AI cost tracking
    "pinecone_integration",  # Pinecone integration for vector search
    # Third-party apps
    "rest_framework",
    "drf_spectacular",
    "rest_framework_simplejwt",  # JWT token authentication
    "social_django",  # Social auth
    "corsheaders",  # CORS headers
    "django_celery_beat",  # Celery beat for scheduled tasks
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",  # CORS middleware - must be before CommonMiddleware
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases
DATABASES = {
    "default": {
        "ENGINE": os.environ.get("DB_ENGINE", "django.db.backends.postgresql"),
        "NAME": os.environ.get("DB_NAME", "ai_blog_generation"),
        "USER": os.environ.get("DB_USER", "postgres"),
        "PASSWORD": os.environ.get("DB_PASSWORD", "postgres"),
        "HOST": os.environ.get("DB_HOST", "localhost"),
        "PORT": os.environ.get("DB_PORT", "5432"),
    }
}

# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/
STATIC_URL = "static/"

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Custom setting for tools directory
TOOLS_DIR = os.path.join(Path(__file__).resolve().parent.parent.parent, "tools")

# Directory to store generated blogs
GENERATED_BLOGS_DIR = os.path.join(BASE_DIR, "generated_blogs")
# Removed the automatic directory creation to prevent it from being created on server startup
# os.makedirs(GENERATED_BLOGS_DIR, exist_ok=True)

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "AI Blog Generator",
    "DESCRIPTION": """
    This API generates complete, high-quality blog posts in Markdown format using a multi-agent AI system.
    
    **How it works:**
    1. You provide a blog topic
    2. Our system activates multiple AI agents to collaboratively create your blog:
       - The **Planner** agent researches and outlines the structure
       - The **Writer** agent drafts the content based on the plan
       - The **Editor** agent refines and improves the final text
       - The **Designer** agent creates a banner image
    3. The complete blog is saved as a Markdown file with the embedded image
    4. You receive the path to the finished blog post
    
    Just enter your topic and click Execute!
    
    **Authentication:**
    - Use JWT tokens for authentication
    - Register via /auth/register/ endpoint
    - Login via /auth/login/ endpoint
    - Also supports Google and LinkedIn authentication
    """,
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,
        "displayOperationId": False,
        "defaultModelsExpandDepth": -1,
        "defaultModelExpandDepth": 1,
        "docExpansion": "list",
        "filter": False,
        "displayRequestDuration": True,
        "tryItOutEnabled": True,
    },
    "COMPONENT_SPLIT_REQUEST": True,
    "SECURITY": [{"Bearer": []}],
    "SECURITY_DEFINITIONS": {
        "Bearer": {
            "type": "apiKey",
            "in": "header",
            "name": "Authorization",
            "description": "Enter: **Bearer <JWT token>**",
        }
    },
}

# Logging Configuration for Development
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            # Set console handler level to DEBUG so it CAN show debug messages if a logger allows them
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "root": {
        "handlers": ["console"],
        # Set root level higher (e.g., INFO) to avoid DEBUG from all libraries
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
        "crewai": {  # Keep CrewAI logs verbose if desired
            "handlers": ["console"],
            "level": "DEBUG",  # Allow DEBUG level from crewai specifically
            "propagate": False,  # Prevent crewai DEBUG messages from going to root logger if root is INFO
        },
        "httpcore": {  # Silence DEBUG messages from httpcore
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "httpx": {  # Silence DEBUG messages from httpx (often used with httpcore)
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "litellm": {  # Set LiteLLM's default to INFO unless DEBUG is needed
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        # Add other specific loggers here if needed
    },
}

# JWT Settings
from datetime import timedelta

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": False,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "VERIFYING_KEY": None,
    "AUDIENCE": None,
    "ISSUER": None,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
    "JTI_CLAIM": "jti",
    "SLIDING_TOKEN_REFRESH_EXP_CLAIM": "refresh_exp",
    "SLIDING_TOKEN_LIFETIME": timedelta(days=1),
    "SLIDING_TOKEN_REFRESH_LIFETIME": timedelta(days=7),
}

# Social Authentication Settings
AUTHENTICATION_BACKENDS = (
    "social_core.backends.google.GoogleOAuth2",
    "social_core.backends.linkedin.LinkedinOAuth2",
    "django.contrib.auth.backends.ModelBackend",
)

# Define which fields to get from the user's profile after authentication
SOCIAL_AUTH_PIPELINE = (
    "social_core.pipeline.social_auth.social_details",
    "social_core.pipeline.social_auth.social_uid",
    "social_core.pipeline.social_auth.auth_allowed",
    "social_core.pipeline.social_auth.social_user",
    "social_core.pipeline.user.get_username",
    "social_core.pipeline.user.create_user",
    "social_core.pipeline.social_auth.associate_user",
    "social_core.pipeline.social_auth.load_extra_data",
    "social_core.pipeline.user.user_details",
)

# CORS settings
CORS_ALLOW_ALL_ORIGINS = True  # Allow all origins
CORS_ALLOW_CREDENTIALS = True  # Allow cookies to be sent with requests
CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]

# Celery Configuration
# For Docker: use redis service name, for local: use localhost
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# Override with Docker-friendly URLs if we're in Docker environment
if os.environ.get("DOCKER_ENV") == "true":
    REDIS_URL = "redis://redis:6379/0"

CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", REDIS_URL)


CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_ENABLE_UTC = True
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60  # 25 minutes
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000

# Celery Beat Configuration (for scheduled tasks) - Use database scheduler
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# Environment Configuration (needed for other configs below)
DJANGO_ENVIRONMENT = os.getenv("DJANGO_ENVIRONMENT", "development")

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Pinecone Configuration
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
# Set Pinecone index name based on environment, with explicit override capability
_default_index = (
    "artilence-staging" if DJANGO_ENVIRONMENT == "staging" else "artilence-development"
)
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", _default_index)

# Serper API Configuration (for web search)
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

# FAL AI Configuration (for FLUX AI image generation)
FAL_KEY = os.getenv("FAL_KEY")

# Google OAuth Configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv(
    "GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback"
)

# LinkedIn OAuth Configuration
LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
LINKEDIN_REDIRECT_URI = os.getenv(
    "LINKEDIN_REDIRECT_URI", "http://localhost:8000/auth/linkedin/callback"
)

# AWS S3 Configuration
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

# Clerk Authentication Configuration
CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY")
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY = os.getenv("NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY")
CLERK_BACKEND_AVAILABLE = os.getenv("CLERK_BACKEND_AVAILABLE", "https://api.clerk.com")

# Streamlit App Configuration
STREAMLIT_APP_URL = os.getenv("STREAMLIT_APP_URL", "http://localhost:8501")

# LangSmith Configuration for AI Cost Tracking
LANGSMITH_TRACING = os.getenv("LANGSMITH_TRACING", "false").lower() == "true"
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "sooqsense-blog-generation")
LANGSMITH_ENDPOINT = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
LANGSMITH_WORKSPACE_ID = os.getenv("LANGSMITH_WORKSPACE_ID")

# Set environment variables for langchain/langsmith integration
if LANGSMITH_TRACING and LANGSMITH_API_KEY:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = LANGSMITH_API_KEY
    os.environ["LANGCHAIN_PROJECT"] = LANGSMITH_PROJECT
    os.environ["LANGCHAIN_ENDPOINT"] = LANGSMITH_ENDPOINT

# Social Auth Keys - Use consistent variable names with credentials defined above
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = GOOGLE_CLIENT_ID
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = GOOGLE_CLIENT_SECRET

SOCIAL_AUTH_LINKEDIN_OAUTH2_KEY = LINKEDIN_CLIENT_ID
SOCIAL_AUTH_LINKEDIN_OAUTH2_SECRET = LINKEDIN_CLIENT_SECRET
