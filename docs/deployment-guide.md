# Comprehensive Deployment Guide

## Overview
This guide provides step-by-step instructions for deploying the BMAD PocketFlow application to Railway, Fly.io, and Google Cloud Run platforms.

## Prerequisites
- Docker installed locally
- Application code with `Dockerfile`
- Platform-specific CLI tools (optional for manual deployment)

## Platform-Specific Setup

### Railway Deployment

#### Prerequisites
- Railway account
- Optional: Railway CLI (`npm install -g @railway/cli`)

#### Step-by-Step Setup
1. **Create Railway Project**
   ```bash
   railway login
   railway init
   ```

2. **Configure Environment Variables**
   - Go to Railway dashboard
   - Select your project
   - Navigate to Variables tab
   - Add required variables:
     ```
     OPENAI_API_KEY=your_api_key
     MEMORY_BACKEND=file
     LOG_LEVEL=info
     ```

3. **Deploy Using railway.toml**
   - Ensure `deployment/railway.toml` exists in your repo
   - Push to main branch (auto-deploy enabled)
   - Or manual deploy: `railway up`

4. **Verify Deployment**
   - Check logs: Railway dashboard → Logs
   - Test health endpoint: `https://your-app.railway.app/health`

#### Scaling Configuration
Railway handles autoscaling automatically based on traffic.

### Fly.io Deployment

#### Prerequisites
- Fly.io account
- Fly CLI: `curl -L https://fly.io/install.sh | sh`

#### Step-by-Step Setup
1. **Login to Fly.io**
   ```bash
   flyctl auth login
   ```

2. **Create Fly App**
   ```bash
   flyctl apps create bmad-pocketflow
   ```

3. **Set Environment Variables**
   ```bash
   flyctl secrets set OPENAI_API_KEY=your_api_key
   flyctl secrets set MEMORY_BACKEND=file
   ```

4. **Deploy Using fly.toml**
   ```bash
   flyctl deploy --config deployment/fly.toml
   ```

5. **Verify Deployment**
   ```bash
   flyctl status
   flyctl logs
   curl https://bmad-pocketflow.fly.dev/health
   ```

#### Scaling Configuration
- Configured in `fly.toml`
- Auto-scaling based on concurrency
- Manual scaling: `flyctl scale count 2`

### Google Cloud Run Deployment

#### Prerequisites
- Google Cloud Project
- Google Cloud CLI: `gcloud` installed
- Container Registry or Artifact Registry enabled

#### Step-by-Step Setup
1. **Authenticate**
   ```bash
   gcloud auth login
   gcloud config set project your-project-id
   ```

2. **Enable Required APIs**
   ```bash
   gcloud services enable run.googleapis.com
   gcloud services enable cloudbuild.googleapis.com
   ```

3. **Create Service Account**
   ```bash
   gcloud iam service-accounts create bmad-pocketflow-sa \
     --description="Service account for BMAD PocketFlow" \
     --display-name="BMAD PocketFlow"
   ```

4. **Create Secrets**
   ```bash
   echo "your_openai_api_key" | gcloud secrets create openai-api-key --data-file=-
   
   gcloud secrets add-iam-policy-binding openai-api-key \
     --member="serviceAccount:bmad-pocketflow-sa@your-project.iam.gserviceaccount.com" \
     --role="roles/secretmanager.secretAccessor"
   ```

5. **Build and Push Container**
   ```bash
   gcloud builds submit --tag gcr.io/your-project/bmad-pocketflow
   ```

6. **Deploy Using YAML Configuration**
   ```bash
   # Update PROJECT_ID in deployment/cloud-run-service.yaml
   sed -i 's/PROJECT_ID/your-project-id/g' deployment/cloud-run-service.yaml
   
   # Deploy
   gcloud run services replace deployment/cloud-run-service.yaml \
     --region=us-central1
   ```

7. **Verify Deployment**
   ```bash
   gcloud run services describe bmad-pocketflow --region=us-central1
   curl https://bmad-pocketflow-hash.run.app/health
   ```

#### Scaling Configuration
- Configured in `cloud-run-service.yaml`
- Auto-scaling: 0-10 instances
- Manual scaling: Update YAML and redeploy

## CI/CD Deployment

### GitHub Actions Setup
The repository includes automated deployment via GitHub Actions.

#### Environment Setup
1. **Repository Secrets**
   - `RAILWAY_TOKEN`: Railway API token
   - `FLY_API_TOKEN`: Fly.io API token
   - `GCP_CREDENTIALS`: Google Cloud service account JSON

2. **Repository Variables**
   - `DEPLOY_TARGET`: Choose `railway`, `flyio`, or `cloudrun`
   - `DEPLOY_URL`: Your deployed app URL for verification

#### Deployment Process
1. Push to main branch
2. Automated testing runs
3. Docker image builds and pushes
4. Platform-specific deployment executes
5. Health check verification

## Environment Variable Management

### Required Variables
| Variable | Description | Example |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | `sk-...` |
| `MEMORY_BACKEND` | Memory storage backend | `file` or `redis` |
| `LOG_LEVEL` | Logging level | `info`, `debug` |
| `PORT` | Application port | `8000` |

### Platform-Specific Commands

#### Railway
```bash
railway variables set OPENAI_API_KEY=sk-xxx
railway variables set MEMORY_BACKEND=file
```

#### Fly.io
```bash
flyctl secrets set OPENAI_API_KEY=sk-xxx
flyctl secrets set MEMORY_BACKEND=file
```

#### Cloud Run
```bash
gcloud secrets create openai-api-key --data-file=-
gcloud run services update bmad-pocketflow \
  --set-env-vars MEMORY_BACKEND=file
```

## Rollback Procedures

### Railway Rollback
1. Go to Railway dashboard
2. Select your service
3. Navigate to Deployments
4. Click "Rollback" on previous deployment

### Fly.io Rollback
```bash
# List releases
flyctl releases

# Rollback to specific release
flyctl releases rollback v2
```

### Cloud Run Rollback
```bash
# List revisions
gcloud run revisions list --service=bmad-pocketflow --region=us-central1

# Rollback to specific revision
gcloud run services update-traffic bmad-pocketflow \
  --to-revisions=bmad-pocketflow-00001-xxx=100 \
  --region=us-central1
```

## Troubleshooting

### Common Issues

#### Deployment Fails
1. **Check build logs** in platform dashboard
2. **Verify Dockerfile** builds locally
3. **Check environment variables** are set correctly
4. **Verify platform limits** (memory, CPU, timeout)

#### Health Check Fails
1. **Test endpoint locally**: `curl localhost:8000/health`
2. **Check application startup** in logs
3. **Verify port configuration** matches platform settings
4. **Check timeout settings** in platform config

#### High Memory Usage
1. **Monitor application logs** for memory leaks
2. **Adjust container memory limits**
3. **Check for large file operations**
4. **Review caching strategies**

#### Slow Response Times
1. **Check database connections** (if applicable)
2. **Review external API calls**
3. **Monitor CPU usage**
4. **Consider horizontal scaling**

### Getting Help

#### Railway
- Documentation: https://docs.railway.app
- Community: Discord server
- Support: help@railway.app

#### Fly.io
- Documentation: https://fly.io/docs
- Community: https://community.fly.io
- Support: support@fly.io

#### Google Cloud Run
- Documentation: https://cloud.google.com/run/docs
- Support: Google Cloud Support Console

## Best Practices

1. **Use platform-specific configurations** for optimal performance
2. **Set appropriate resource limits** to control costs
3. **Configure health checks** for reliability
4. **Set up monitoring and alerts** for production
5. **Test deployments** in staging environment first
6. **Document environment variables** and their purposes
7. **Implement proper logging** for debugging
8. **Use secrets management** for sensitive data
9. **Regular security updates** for base images
10. **Monitor costs** and optimize resource usage