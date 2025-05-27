# AI Blog Generator - Django Application

This directory contains the Django web application implementation of the AI Blog Generator system. The application provides a RESTful API for generating blog posts, LinkedIn content, weekly AI news, and images - all stored in a PostgreSQL database.

## Directory Structure

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

## Database Models

The application uses PostgreSQL to store all generated content:

1. **BlogGeneral** - Stores generated blog posts

   - `user_id` - User identifier
   - `topic` - Blog topic
   - `content` - Full blog content
   - `created_at` - Timestamp

2. **BlogAiNews** - Stores weekly AI news summaries

   - `news_week_start` - Start date of the news week
   - `summary` - Short summary
   - `content` - Full news content
   - `created_at` - Timestamp

3. **LinkedinPost** - Stores LinkedIn posts

   - `user_id` - User identifier
   - `topic` - Post topic
   - `content` - Full post content
   - `created_at` - Timestamp

4. **ImageGeneration** - Stores generated images
   - `user_id` - User identifier
   - `prompt` - Image generation prompt
   - `image_url` - Path to generated image
   - `created_at` - Timestamp

## Setup Instructions

### Prerequisites

- Python 3.10+
- PostgreSQL database
- OpenAI API key
- SerperDev API key
- Google API key (optional, for Gemini)

### Installation

1. Install required dependencies:

```bash
pip install django djangorestframework psycopg2-binary python-dotenv drf-spectacular
pip install openai requests crewai crewai-tools langchain-google-genai langchain-openai
```

2. Create a `.env` file in the project root with the following configuration:

```
# API Keys
OPENAI_API_KEY=your_openai_api_key
SERPER_API_KEY=your_serper_api_key
GOOGLE_API_KEY=your_google_api_key

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

   - `POST /api/blogs/`
   - Request: `{"topic": "Blog Topic", "keywords": "optional,keywords"}`
   - Response: Generated blog post content and file path

2. **Weekly AI News**

   - `GET /api/news/`
   - Response: Generated weekly AI news content and file path

3. **LinkedIn Posts**

   - `POST /api/linkedin/`
   - Request: `{"topic": "LinkedIn Post Topic"}`
   - Response: Generated LinkedIn post content

4. **Image Generation**
   - `POST /api/images/`
   - Request: `{"prompt": "Image Description", "keywords": "optional,keywords"}`
   - Response: Generated image file path

## Running the Server

To start the development server:

```bash
# Standard development server
python manage.py runserver

# Specify host and port
python manage.py runserver 0.0.0.0:8001
```

Access the API documentation at: http://localhost:8001/api/schema/swagger-ui/

## Development Guidelines

### Adding New Endpoints

1. Define the model in `api/models.py`
2. Create serializers in `api/serializers.py`
3. Implement the view in `api/views.py`
4. Add URL patterns in `api/urls.py`
5. Run migrations:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

### Database Access

The application automatically stores generated content in the PostgreSQL database using Django's ORM. To query the data:

```python
# Example: Retrieve the latest 10 blog posts
from api.models import BlogGeneral
recent_blogs = BlogGeneral.objects.order_by('-created_at')[:10]
```

### Environment Configuration

The application uses python-dotenv to load environment variables. All settings in `.env` are accessible via:

```python
import os
api_key = os.environ.get('OPENAI_API_KEY')
```

### Accessing AI Tools

The Django application now accesses the AI tools from the `/tools` directory. This modular approach allows:

1. Better separation of concerns between the web application and AI functionality
2. Ability to use the AI tools in other contexts outside of the Django app
3. Easier maintenance of AI-specific functionality

Example of importing tools:

```python
# In views.py
from tools.ai.blog_generator.blog_writer import BlogWriter, generate_image
from tools.ai.linkedin_post_generator.linkedin_post_generator import LinkedInPostGenerator
```

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

## Docker Setup

The application includes Docker support for development, staging, and production environments, making it easy to run consistently across different systems.

### Docker Directory Structure

```
AI-Blog-Generator/
├── Dockerfile              # Multi-stage Dockerfile for different environments
├── docker-compose.yml      # Docker Compose configuration
├── docker-README.md        # Docker-specific documentation
└── sample.env              # Template for .env file
```

### Prerequisites

- Docker
- Docker Compose

### Environment Setup

Before running the containers, create your `.env` file:

```bash
# Copy the sample environment file
cp sample.env .env

# Edit the file with your actual values and API keys
nano .env
```

### Running with Docker Compose

The application uses Docker Compose profiles to manage different environments:

#### Development Environment

```bash
# Run the development environment
docker-compose --profile development up

# Run in detached mode
docker-compose --profile development up -d
```

Features:

- Django development server
- Debug mode enabled
- Hot reloading of code changes

#### Staging Environment

```bash
# Run the staging environment
docker-compose --profile staging up
```

Features:

- Gunicorn web server
- Debug mode enabled
- Similar to production but with debugging capabilities

#### Production Environment

```bash
# Run the production environment
docker-compose --profile production up
```

Features:

- Gunicorn web server
- Debug mode disabled
- Running as non-root user for improved security
- Optimized resource limits

### Managing Docker Containers

```bash
# Stop running containers
docker-compose down

# View logs
docker-compose logs -f

# Rebuild images after changes to Dockerfile
docker-compose build [development|staging|production]
```

### Running Commands Inside Containers

```bash
# For Django management commands
docker-compose exec development python django_app/manage.py makemigrations
docker-compose exec development python django_app/manage.py migrate

# Access Django shell
docker-compose exec development python django_app/manage.py shell

# For bash access
docker-compose exec development bash
```

### Database Management with Docker

The application can use either:

- The PostgreSQL database configured in your .env file
- A dockerized PostgreSQL instance (can be added to docker-compose.yml)

### Troubleshooting Docker Issues

If you encounter issues:

1. Check container logs:

   ```bash
   docker-compose logs -f
   ```

2. Verify environment variables are correctly set in .env

3. Ensure ports are not already in use on your host machine

4. Rebuild the image if dependencies have changed:
   ```bash
   docker-compose build --no-cache [development|staging|production]
   ```