# AI Blog Generator - Django Application

This directory contains the Django web application implementation of the AI Blog Generator system. The application provides a RESTful API for generating blog posts, LinkedIn content, weekly AI news, and images - all stored in a PostgreSQL database.

## Project Overview

```
AI-Blog-Generator/
├── management_app/            # Django web application
│   ├── api/                   # API application
│   │   ├── migrations/        # Database migration files
│   │   ├── models.py          # Database models
│   │   ├── serializers.py     # API request/response serializers
│   │   ├── views.py           # API endpoints implementation
│   │   └── urls.py            # API routing
│   │
│   ├── config/                # Main Django project settings
│   │   ├── settings.py        # Project configuration
│   │   ├── urls.py            # Main URL routing
│   │   └── wsgi.py            # WSGI configuration
│   │
│   ├── generated_blogs/       # Output directory for generated content
│   │   └── api_generated_images/ # Generated images storage
│   │
│   ├── manage.py              # Django management command
│   └── .env                   # Environment variables (create this file)
│
├── tools/                     # Shared tools and utilities
│   ├── ai/                    # AI tools and generators
│   │   ├── blog_generator/    # Blog generation functionality
│   │   │   ├── blog_writer.py # CrewAI blog generation
│   │   │   └── configuration/ # YAML configurations folder
│   │   │
│   │   └── linkedin_post_generator/ # LinkedIn post generation
│   │       └── linkedin_post_generator.py # LinkedIn post generator
│   │
│   └── README.md              # Tools documentation
```

- **Blog Posts**: Generate detailed articles on any topic with customizable parameters
- **Weekly AI News**: Create summaries of the latest trends and developments in AI
- **LinkedIn Posts**: Craft professional social media content
- **AI-Generated Images**: Create images using DALL-E 3
- **Trend Analysis**: Fetch related topics and analyze keyword trends

All generated content is stored in a PostgreSQL database for easy access and management.

## Directory Structure Explanation

- **api/**: Contains the core API functionality
  - **models.py**: Defines database tables for storing generated content
  - **views.py**: Implements API endpoints handling content generation requests
  - **urls.py**: Maps URLs to view functions
  - **serializers.py**: Handles request validation and response formatting
  - **migrations/**: Contains database schema changes

- **config/**: Project configuration 
  - **settings.py**: Main configuration file with database, auth, and API settings
  - **urls.py**: Root URL configuration
  
- **authentication/**: User authentication system
  - Handles user registration, login, and token-based authentication

## How the System Works

1. **Content Generation Flow**:
   - User sends a request to an API endpoint with parameters
   - The API validates the request using serializers 
   - The appropriate AI tool is invoked from the tools directory
   - Generated content is stored in the PostgreSQL database
   - Response is returned to the user

2. **Authentication Flow**:
   - User registers or logs in to receive a JWT token
   - Token is included in subsequent API requests
   - API validates the token before processing requests

3. **Database Storage**:
   - All generated content is stored in PostgreSQL tables
   - No local file storage is used for content
   - Images are stored in S3 if configured, with URLs in the database

## Useful Commands

### Server Management
- Start development server: `python manage.py runserver`
- Start server on custom port: `python manage.py runserver 0.0.0.0:8000`
- Production deployment with Gunicorn: `gunicorn config.wsgi:application`

### Database Management
- Create migrations: `python manage.py makemigrations`
- Apply migrations: `python manage.py migrate`
- Reset migrations: `python manage.py migrate api zero`
- Create superuser: `python manage.py createsuperuser`
- Access database shell: `python manage.py dbshell`

### Development Tools
- Run tests: `python manage.py test`
- Django shell: `python manage.py shell`
- Check project for problems: `python manage.py check`
- Generate schema: `python manage.py spectacular --file schema.yml`

### Environment Setup
- Create virtual environment: `python -m venv venv`
- Activate virtual environment: 
  - Windows: `venv\Scripts\activate`
  - Mac/Linux: `source venv/bin/activate`

## Common Workflows

### Creating New Content
1. Authenticate with the API to receive a JWT token
2. Send a POST request to the appropriate endpoint with required parameters
3. Receive the generated content in the response
4. Content is automatically saved in the database

### Troubleshooting Issues
1. Check server logs: `python manage.py runserver --traceback`
2. Verify database connection: `pg_isready`
3. Reset migrations if schema issues occur
4. Check environment variables in .env file

### Deployment Process
1. Configure environment variables for production
2. Set DEBUG=False in settings
3. Collect static files: `python manage.py collectstatic`
4. Start with Gunicorn
5. Configure Nginx/Apache as a reverse proxy

## Setup Instructions

### Prerequisites

- Python 3.10+
- PostgreSQL database
- OpenAI API key
- SerperDev API key
- Google API key (optional, for Gemini)
- AWS credentials (optional, for S3 image storage)

### Installation

1. Install required dependencies:

```bash
pip install -r requirements.txt
```

2. Create a `.env` file in the project root with the following configuration:

```
# API Keys
OPENAI_API_KEY=your_openai_api_key
SERPER_API_KEY=your_serper_api_key
GOOGLE_API_KEY=your_google_api_key

# AWS S3 Configuration (for image storage)
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
S3_BUCKET_NAME=your_bucket_name
AWS_REGION=us-east-1

# Database Configuration
DB_ENGINE=django.db.backends.postgresql
DB_NAME=ai_blog_generation
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432
```

3. Create the PostgreSQL database:

```bash
# Using psql CLI
createdb ai_blog_generation
```

4. Run database migrations:

```bash
python manage.py migrate
```

## API Endpoints

The API provides the following endpoints:

1. **Blog Generation**
   - `POST /api/generate-blog/`
   - Request: Topic, keywords, tone, length settings, and formatting options
   - Response: Generated blog post content stored in database

2. **Weekly AI News**
   - `GET /api/weekly-news/`
   - Response: Generated weekly AI news content stored in database

3. **LinkedIn Posts**
   - `POST /api/generate-linkedin-post/`
   - Request: Topic and optional keywords
   - Response: Generated LinkedIn post content stored in database

4. **Image Generation**
   - `POST /api/generate-image/`
   - Request: Prompt, keywords, and size parameters
   - Response: Generated image URL stored in database

5. **Related Topics**
   - `POST /api/fetch-related-topics/`
   - Request: Keywords, region, and limit
   - Response: Related topics data stored in database

## Authentication

The application uses JWT (JSON Web Token) authentication:

1. Register a user:
   - `POST /auth/register/`
   - Request: Username, email, and password

2. Login to get tokens:
   - `POST /auth/login/`
   - Request: Username and password
   - Response: Access token and refresh token

3. Use the access token in Authorization header:
   - `Authorization: Bearer access_token`

## Troubleshooting

### Database Connection Issues

If you encounter database connection problems:

1. Check PostgreSQL is running:
   ```bash
   pg_isready
   ```

2. Verify connection settings in `.env` file

3. Test connection with psql:
   ```bash
   psql -h localhost -U postgres -d ai_blog_generation
   ```

### Migration Issues

If you encounter migration problems:

```bash
# Reset migrations (caution: this loses all data)
python manage.py migrate api zero
python manage.py makemigrations api
python manage.py migrate
```

### ALLOWED_HOSTS Issues

If you get a "DisallowedHost" error when accessing the application:

1. Edit `config/settings.py` and add your host to the ALLOWED_HOSTS list:
   ```python
   ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0', 'your-domain.com']
   ```

## Deployment

For production deployment:

1. Update `config/settings.py`:
   - Set `DEBUG = False`
   - Configure `ALLOWED_HOSTS`
   - Use environment variables for sensitive settings

2. Set up a production-ready server:
   ```bash
   pip install gunicorn
   gunicorn config.wsgi:application
   ```

3. Configure a reverse proxy (Nginx/Apache)

4. Use a proper PostgreSQL production configuration 