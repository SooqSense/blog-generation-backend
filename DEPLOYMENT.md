# Deployment Configuration

## Branch-Based Deployment Strategy

This project uses a **branch-based deployment strategy** where different branches deploy different services:

### 🌐 **Staging Branch** → **Streamlit Frontend**

- **Branch**: `staging`
- **Service**: `sooqsense-streamlit-staging`
- **URL**: Streamlit UI (Port 8501)
- **Purpose**: Frontend user interface
- **Workflow**: `.github/workflows/deploy-cloudrun-staging.yml`

### 🔧 **Next-Staging Branch** → **Django Backend**

- **Branch**: `next-staging`
- **Service**: `sooqsense-django-next-staging`
- **URL**: Django API (Port 8000)
- **Purpose**: Backend API and data management
- **Workflow**: `.github/workflows/deploy-django-next-staging.yml`

## Deployment Process

### 1. Deploy Streamlit (Frontend)

```bash
# Push to staging branch
git checkout staging
git add .
git commit -m "Update Streamlit frontend"
git push origin staging
```

**Result**: Streamlit deploys to Cloud Run with service name `sooqsense-streamlit-staging`

### 2. Deploy Django (Backend)

```bash
# Push to next-staging branch
git checkout next-staging
git add .
git commit -m "Update Django backend"
git push origin next-staging
```

**Result**: Django deploys to Cloud Run with service name `sooqsense-django-next-staging`

## Service Configuration

### Streamlit Service (staging branch)

- **Memory**: 2Gi
- **CPU**: 1
- **Timeout**: 1500 seconds
- **Max Instances**: 1
- **Min Instances**: 0
- **Concurrency**: 80

### Django Service (next-staging branch)

- **Memory**: 4Gi
- **CPU**: 2
- **Timeout**: 3000 seconds
- **Max Instances**: 5
- **Min Instances**: 0
- **Concurrency**: 100

## Environment Variables

Both services share the same environment variables from `.env`:

- Database connection (Neon PostgreSQL)
- AI service keys (OpenAI, Serper, Pinecone)
- Authentication (Clerk)
- Redis (Upstash)

## Integration

The Streamlit frontend connects to the Django backend through:

1. **Direct Django service imports** in Streamlit features
2. **Shared database** (PostgreSQL)
3. **Shared authentication** (Clerk + Django User model)
4. **Shared AI services** (OpenAI, Pinecone, etc.)

## URLs After Deployment

After both deployments:

- **Streamlit Frontend**: `https://sooqsense-streamlit-staging-[hash]-uc.a.run.app`
- **Django API**: `https://sooqsense-django-next-staging-[hash]-uc.a.run.app`
- **API Documentation**: `https://sooqsense-django-next-staging-[hash]-uc.a.run.app/docs/`
- **Admin Panel**: `https://sooqsense-django-next-staging-[hash]-uc.a.run.app/admin/`

## Next Steps

1. **Deploy Django**: Push to `next-staging` branch
2. **Update Streamlit**: Add Django API URL to Streamlit environment
3. **Test Integration**: Verify Streamlit can connect to Django API
4. **Monitor**: Check Cloud Run logs for both services
