from pathlib import Path
import os
from dotenv import load_dotenv

# Django Setup Guard - Prevent premature setup during configuration
# This prevents conflicts when Django configuration is being read
_DJANGO_SETTINGS_LOADING = True

# Load environment variables from .env file
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "django-insecure-dummy-key")

DEBUG = True

ALLOWED_HOSTS = ["*"]

AUTH_USER_MODEL = "authentication.User"

# Application definition
INSTALLED_APPS = [
    "daphne",  # MUST be first for ASGI/WebSocket support
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Modular apps
    "management_app.blog_generator",
    "management_app.ai_news",
    "management_app.image_generator",
    "management_app.linkedin_post_generator",
    "management_app.schedule_linkedin_post",
    "management_app.ai_trends",
    "management_app.knowledge_base",
    "management_app.chatbot",
    "management_app.authentication",  # Authentication app
    "management_app.upwork_proposal_generator",  # Upwork proposal generator app
    # Integration apps
    "management_app.langsmith_integration",  # LangSmith integration for AI cost tracking
    "management_app.pinecone_integration",  # Pinecone integration for vector search
    # Third-party apps
    "rest_framework",
    "drf_spectacular",
    "corsheaders",  # CORS headers
    "django_celery_beat",  # Celery beat for scheduled tasks
    "channels",  # WebSocket support
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",  # CORS middleware - must be before CommonMiddleware
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "management_app.authentication.middleware.ClerkJWTAuthenticationMiddleware",  # Clerk JWT authentication
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "management_app.config.urls"

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

WSGI_APPLICATION = "management_app.config.wsgi.application"
ASGI_APPLICATION = "management_app.config.asgi.application"

# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases
DATABASES = {
    "default": {
        "ENGINE": os.environ.get("DB_ENGINE", "django.db.backends.postgresql"),
        "NAME": os.environ.get("DB_NAME"),
        "USER": os.environ.get("DB_USER"),
        "PASSWORD": os.environ.get("DB_PASSWORD"),
        "HOST": os.environ.get("DB_HOST"),
        "PORT": os.environ.get("DB_PORT"),
        "OPTIONS": {"connect_timeout": 10},
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
        "management_app.authentication.authentication.ClerkJWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

SPECTACULAR_SETTINGS = {
    "TITLE": "AI Blog Generator API",
    "DESCRIPTION": """
    **Backend API for AI-powered content generation with Clerk Authentication**
    
    This API provides endpoints for generating blog posts, LinkedIn content, AI news, and images.
    
    ## Authentication
    
    This API uses **Clerk** for authentication. Follow these steps:
    
    1. **Authenticate with Clerk** on your frontend using Clerk's SDK
    2. **Get JWT token** from Clerk after successful authentication
    3. **Send token to `/auth/verify/`** endpoint to sync user with backend
    4. **Use the same JWT token** in the Authorization header for all subsequent requests
    
    ### How to Authorize in Swagger UI:
    
    1. Click the **"Authorize"** button (lock icon) at the top right
    2. In the "Value" field, enter: `Bearer YOUR_CLERK_JWT_TOKEN`
    3. Click "Authorize" and then "Close"
    4. Now you can test all protected endpoints
    
    **Note:** Replace `YOUR_CLERK_JWT_TOKEN` with the actual JWT token from Clerk.
    
    ## Getting Started
    
    1. First, call `POST /auth/verify/` with your Clerk JWT token to sync your user
    2. Then use the same token in the Authorization header for other endpoints
    3. Generate blogs, LinkedIn posts, images, and more!
    """,
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,
        "displayOperationId": False,
        "defaultModelsExpandDepth": -1,
        "defaultModelExpandDepth": 1,
        "docExpansion": "list",
        "filter": True,
        "displayRequestDuration": True,
        "tryItOutEnabled": True,
        "persistAuthorization": True,  # Keep authorization between page refreshes
    },
    "COMPONENT_SPLIT_REQUEST": True,
    # OpenAPI 3.0 Security Scheme
    "APPEND_COMPONENTS": {
        "securitySchemes": {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "Enter your Clerk JWT token. The token will be automatically prefixed with 'Bearer '."
            }
        }
    },
    "SECURITY": [{"BearerAuth": []}],
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

# Clerk Authentication Configuration
CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY")
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY = os.getenv("NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY")
CLERK_API_URL = os.getenv("CLERK_API_URL", "https://api.clerk.com")
CLERK_JWKS_URL = os.getenv("CLERK_JWKS_URL")
CLERK_FRONTEND_URL = os.getenv("CLERK_FRONTEND_URL")

# Development SSL settings
if DEBUG:
    import ssl
    import urllib3

    # Disable SSL verification for development
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    ssl._create_default_https_context = ssl._create_unverified_context

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
    "x-selected-organization",  # Custom header for organization selection
]

# Celery Configuration
# For Docker: use redis service name, for local: use localhost
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# Override with Docker-friendly URLs if we're in Docker environment
if os.environ.get("DOCKER_ENV") == "true":
    REDIS_URL = "redis://redis:6379/0"
    # Force Celery to use the Docker Redis URL, ignoring .env values which might be localhost
    os.environ["CELERY_BROKER_URL"] = REDIS_URL
    os.environ["CELERY_RESULT_BACKEND"] = REDIS_URL

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

# Redis Configuration for direct connections (Pub/Sub)
REDIS_HOST = os.environ.get("REDIS_HOST", "redis" if os.environ.get("DOCKER_ENV") == "true" else "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))

# Environment Configuration (needed for other configs below)

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Pinecone Configuration
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
# Set Pinecone index name based on environment, with explicit override capability
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")

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

# Google API Configuration (for Gemini AI)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

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

# LangSmith Configuration for AI Cost Tracking
LANGSMITH_TRACING = os.getenv("LANGSMITH_TRACING", "false").lower() == "true"
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "sooqsense-blog-generation")
LANGSMITH_ENDPOINT = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
LANGSMITH_WORKSPACE_ID = os.getenv("LANGSMITH_WORKSPACE_ID")

BACKEND_API_BASE_URL = os.getenv("BACKEND_API_BASE_URL", "http://localhost:8000")

# Channels Configuration for WebSocket support
import ssl


def get_redis_config():
    # Use the REDIS_URL defined earlier (which handles Docker env correctly)
    redis_url = REDIS_URL

    if redis_url.startswith("rediss://"):
        # For SSL Redis connections (like Upstash)
        return {
            "hosts": [redis_url],
            "ssl_cert_reqs": None,  # Disable SSL certificate verification
        }
    else:
        # For non-SSL Redis connections
        return {
            "hosts": [redis_url],
        }


CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": get_redis_config(),
    },
}
