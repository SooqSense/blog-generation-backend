# AI Blog Generator

A multi-agent system for automated blog content creation leveraging CrewAI and large language models.

## Overview

The AI Blog Generator is a sophisticated system that employs multiple AI agents to collaboratively produce high-quality blog posts:

- **Content Planner**: Researches and plans the blog post structure
- **Content Writer**: Drafts the blog content based on the plan
- **Editor**: Refines and polishes the content for publication
- **Banner Designer** (optional): Creates prompts for banner image generation

The system can also generate banner images for blog posts using DALL-E 3.

## How to Start

### Prerequisites

- Python 3.10+
- OpenAI API key for GPT models and DALL-E image generation
- Google API key (optional, for Gemini models)
- SerperDev API key for search capabilities
- Docker and Docker Compose (for containerized deployment)

### Installation

#### Local Development

```bash
# Clone the repository
git clone https://github.com/SooqSense/blog-generation-backend.git
cd blog-generation-backend

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys and configuration
```

#### Docker Setup

```bash
# Build and run using Docker Compose for development
docker compose -f docker-compose.yml --profile development up

# Build and run using Docker Compose for staging
docker compose -f docker-compose.yml --profile staging up

# Build and run using Docker Compose for production
docker compose -f docker-compose.yml --profile production up
```

#### Manual Docker Commands

```bash
# Build the Docker image for staging
docker build --target staging -t blog-generation-backend:staging .

# Run the Docker container
docker run -p 8000:8000 --env-file .env --name blog-staging blog-generation-backend:staging

# Push to Docker Hub
docker tag blog-generation-backend:staging sohaibanwaar/blog-generation-backend:staging
docker push sohaibanwaar/blog-generation-backend:staging
```

## Deployment

### Render Deployment

The application is configured for deployment on Render using Docker:

1. Create a new Web Service in Render
2. Choose "Deploy an existing image from a registry"
3. Use the Docker image: `docker.io/sohaibanwaar/blog-generation-backend:staging`
4. Set the environment variables from your `.env` file
5. Set the environment variable `PORT=8000`
6. Add a health check path if needed

### CI/CD Pipeline

The repository includes a GitHub Actions workflow for CI/CD in `.github/workflows/staging.yml`. It:

1. Builds the Docker image on push to the staging branch
2. Pushes the image to Docker Hub
3. Triggers deployment on Render via a deploy hook

Required GitHub Secrets:

- `DOCKER_PASSWORD`: Docker Hub password
- `RENDER_DEPLOY_HOOK`: Render deploy hook URL

## API Endpoints

The API is available at:

- Staging: https://api.staging.sooqsense.com/
- API Documentation: https://api.staging.sooqsense.com/docs/
- API Schema: https://api.staging.sooqsense.com/api/schema/

## Tools and Technologies

- **Django**: Web framework for building the API
- **PostgreSQL**: Database for storing content
- **Docker**: Containerization for deployment
- **CrewAI**: Framework for orchestrating multiple AI agents
- **LangChain**: For integrating with various language models
- **OpenAI's GPT-3.5/4**: For content generation
- **Google's Gemini**: Alternative LLM option
- **DALL-E 3**: For generating banner images
- **SerperDev**: For web search capabilities

## 🔑 API Keys

To use this system, you'll need to obtain the following API keys:

1. **OpenAI API Key** (Required for LLM and image generation)

   - Sign up at [platform.openai.com](https://platform.openai.com)
   - Navigate to API Keys section and create a new secret key
   - Add credit to your account for API usage

2. **Serper API Key** (Required for web search capabilities)

   - Sign up at [serper.dev](https://serper.dev)
   - Create an API key from your dashboard
   - Free tier available, paid tiers for more requests

3. **Google API Key** (Optional, for Gemini LLM)
   - Sign up at [AI Studio](https://makersuite.google.com/app/apikey)
   - Create a new API key
   - Enable the Generative Language API

## 💡 How It Works

The system follows a collaborative workflow that mimics a real content creation team:

1. **Planning Phase**: The Content Planner agent researches the given topic using the Serper search tool, identifies key points, trends, and target audience information, and creates a detailed content outline.

2. **Writing Phase**: The Content Writer agent takes the outline from the Planner and crafts a complete blog post, focusing on structure, flow, and engaging content.

3. **Editing Phase**: The Editor agent reviews the draft from the Writer, improving style, checking facts, and ensuring the content aligns with best practices.

4. **Image Generation** (Optional): The system generates a customized banner image using DALL-E 3, based on the blog post content.

5. **Output**: The final blog post is saved as a Markdown file with the banner image embedded.

## 🌟 Use Cases

- **Content Marketing**: Generate blog posts for your company's website
- **Personal Blogging**: Create drafts for your personal blog on various topics
- **Educational Content**: Produce informative articles on complex subjects
- **SEO Content**: Generate search-optimized content with relevant keywords
- **Research Summaries**: Create comprehensive summaries of research topics

## 🔮 Architectural Concept

The Blog Writer Multi-Agent system demonstrates an emerging paradigm in AI application development: specialized AI agents collaborating to complete complex tasks. This approach offers several advantages:

- **Specialization**: Each agent excels at a specific part of the content creation process
- **Modularity**: Easily add or remove agents to customize the workflow
- **Quality Control**: Multiple review stages ensure higher content quality
- **Emergent Capabilities**: The combined system achieves results beyond individual agents

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Elevating AI creativity—one image at a time! 🌟**
