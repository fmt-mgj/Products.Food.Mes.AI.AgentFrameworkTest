# CI/CD Process Documentation

## Overview

This document describes the automated Continuous Integration and Continuous Deployment (CI/CD) pipeline implemented for the BMAD → PocketFlow Generator & Runtime system.

## Workflow Description

The CI/CD pipeline is implemented using GitHub Actions and is located in `.github/workflows/deploy.yml`. It automatically runs on every push to the `main` branch.

## Pipeline Stages

### 1. Test Stage
**Purpose**: Validate code quality and functionality
**Steps**:
- Checkout repository code
- Set up Python 3.10 environment
- Generate PocketFlow code from BMAD sources using `bmad2pf.py`
- Install production and development dependencies
- Run unit tests with coverage reporting
- Run integration tests
- Upload coverage reports to Codecov

### 2. Build and Push Stage
**Purpose**: Create and publish Docker image
**Dependencies**: Requires test stage to pass
**Steps**:
- Checkout repository code
- Set up Docker Buildx for advanced caching
- Log in to GitHub Container Registry (ghcr.io)
- Extract image metadata and tags (branch name and commit SHA)
- Build Docker image with caching
- Push image to ghcr.io with multiple tags

### 3. Deploy Stage
**Purpose**: Deploy to configured platform
**Dependencies**: Requires build-and-push stage to pass
**Environment**: Production environment with manual approval
**Steps**:
- Platform-specific deployment based on `DEPLOY_TARGET` variable:
  - **Railway**: Deploy using Railway CLI action
  - **Fly.io**: Deploy using flyctl CLI
  - **Google Cloud Run**: Deploy using GCP action
- Health check verification after deployment

## Environment Variables

### Repository Variables
Configure these in GitHub repository settings → Variables:
- `DEPLOY_TARGET`: Target platform (`railway`, `flyio`, or `cloudrun`)
- `DEPLOY_URL`: Application URL for health checks

### Repository Secrets
Configure these in GitHub repository settings → Secrets:
- `GITHUB_TOKEN`: Auto-provided for GitHub Container Registry access
- `RAILWAY_TOKEN`: Railway deployment token (if using Railway)
- `FLY_API_TOKEN`: Fly.io API token (if using Fly.io)
- `GCP_CREDENTIALS`: Google Cloud service account JSON (if using Cloud Run)
- `OPENAI_API_KEY`: OpenAI API key for deployed application

## Image Tagging Strategy

Docker images are tagged with:
- Branch name (e.g., `main`)
- Commit SHA with branch prefix (e.g., `main-abc123`)

This enables:
- Easy identification of deployed versions
- Rollback to any previous commit
- Traceability between deployment and source code

## Deployment Platforms

### Railway
- **Configuration**: Uses Railway CLI GitHub Action
- **Features**: Automatic SSL, domain provisioning
- **Environment Variables**: Set in Railway dashboard

### Fly.io
- **Configuration**: Requires `fly.toml` in repository
- **Features**: Multi-region deployment, automatic scaling
- **Setup**: Create app with `flyctl apps create`

### Google Cloud Run
- **Configuration**: Uses Google Cloud Deploy action
- **Features**: Serverless, automatic scaling to zero
- **Permissions**: Requires service account with Cloud Run Admin role

## Rollback Strategy

### Automatic Rollback Options
- **Image Tags**: Each deployment is tagged with commit SHA
- **Platform Console**: Direct rollback via platform web console

### Manual Rollback Process
1. **Identify Target Commit**: Find the commit SHA to rollback to
2. **Re-run Workflow**: Navigate to GitHub Actions and re-run the workflow from the target commit
3. **Emergency Rollback**: Use platform-specific console to switch to previous image

### Emergency Procedures
- **Railway**: Use Railway dashboard to select previous deployment
- **Fly.io**: Run `flyctl deploy --image ghcr.io/repo:target-tag`
- **Cloud Run**: Use Google Cloud Console to deploy previous revision

## Performance Optimizations

### Build Speed
- **Docker Layer Caching**: Uses GitHub Actions cache for Docker layers
- **Parallel Jobs**: Test and build stages can run simultaneously where possible
- **Dependency Caching**: Pip dependencies cached between runs

### Cost Optimization
- **Skip CI**: Add `[skip ci]` to commit message to bypass pipeline
- **Conditional Deployment**: Only deploys on main branch after tests pass
- **Image Size**: Multi-stage Docker build minimizes final image size

## Monitoring and Observability

### Build Status
- **Status Badge**: Displays current build status in README.md
- **GitHub Actions Tab**: Detailed logs and history
- **Email Notifications**: Configured for build failures

### Health Checks
- **Endpoint**: `/health` endpoint verification after deployment
- **Timeout**: 30-second wait before health check
- **Failure Handling**: Pipeline fails if health check returns non-200

## Security Considerations

### Secrets Management
- **No Hardcoded Secrets**: All secrets stored in GitHub repository settings
- **Minimal Permissions**: GitHub tokens have minimal required permissions
- **Secret Rotation**: Regular rotation of API keys and tokens

### Container Security
- **Base Image**: Uses `python:3.10-slim` for security and size
- **Non-root User**: Container runs as non-privileged user
- **Dependency Scanning**: Automated vulnerability scanning of dependencies

## Troubleshooting

### Common Issues

#### Test Failures
- **Check Logs**: Review test output in GitHub Actions
- **Local Testing**: Run tests locally with same commands
- **Dependencies**: Ensure all required dependencies are installed

#### Build Failures
- **Docker Build**: Check Dockerfile and build context
- **Registry Access**: Verify GitHub Container Registry permissions
- **Image Size**: Monitor for image size limits

#### Deployment Failures
- **Platform Credentials**: Verify all required secrets are set
- **Service Configuration**: Check platform-specific configuration files
- **Resource Limits**: Ensure platform has sufficient resources

### Debug Steps
1. **Check Logs**: Review detailed logs in GitHub Actions
2. **Local Reproduction**: Try to reproduce the issue locally
3. **Platform Logs**: Check deployment platform logs
4. **Health Check**: Verify application health after deployment

## Maintenance

### Regular Tasks
- **Dependency Updates**: Monthly review of GitHub Action versions
- **Security Patches**: Immediate application of security updates
- **Performance Review**: Quarterly pipeline performance analysis

### Upgrade Path
- **GitHub Actions**: Keep actions updated to latest versions
- **Platform Tools**: Regular updates of deployment tools
- **Documentation**: Keep this document updated with changes

## Contact and Support

For issues with the CI/CD pipeline:
1. Check this documentation first
2. Review GitHub Actions logs
3. Check platform-specific documentation
4. Contact the development team

---

*This CI/CD process follows KISS (Keep It Simple, Stupid) principles while providing robust automated deployment capabilities.*