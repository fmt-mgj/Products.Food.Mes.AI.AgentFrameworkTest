# Rollback Instructions

## Overview

This document provides step-by-step instructions for rolling back deployments of the BMAD → PocketFlow Generator & Runtime system. Each deployment is tagged with commit SHA for easy identification and rollback.

## Quick Reference

| Severity | Method | Time to Complete |
|----------|--------|------------------|
| **Emergency** | Platform Console | 2-5 minutes |
| **Standard** | Re-run GitHub Workflow | 5-10 minutes |
| **Planned** | New Deployment | 10-15 minutes |

## Emergency Rollback (2-5 minutes)

Use this when the current deployment is causing critical issues and immediate rollback is required.

### Railway Emergency Rollback

1. **Access Railway Dashboard**:
   - Go to [Railway Dashboard](https://railway.app/dashboard)
   - Navigate to your `bmad-pocketflow` service

2. **Select Previous Deployment**:
   - Click on "Deployments" tab
   - Find the last known working deployment
   - Click "Redeploy" next to that deployment

3. **Monitor Rollback**:
   - Watch deployment status in Railway dashboard
   - Verify application health at your deployment URL

### Fly.io Emergency Rollback

1. **Identify Target Image**:
   ```bash
   # List recent images
   flyctl image list --app your-app-name
   ```

2. **Deploy Previous Image**:
   ```bash
   # Replace with target image tag
   flyctl deploy --image ghcr.io/your-username/products.food.mes.ai.agentframeworktest:main-abc123 --app your-app-name
   ```

3. **Verify Rollback**:
   ```bash
   flyctl status --app your-app-name
   ```

### Google Cloud Run Emergency Rollback

1. **Access Cloud Console**:
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Navigate to Cloud Run → Services → bmad-pocketflow

2. **Deploy Previous Revision**:
   - Click "Manage Traffic" tab
   - Find previous working revision
   - Set traffic allocation to 100% for that revision
   - Click "Save"

3. **Verify Rollback**:
   - Check service URL for proper functionality

## Standard Rollback (5-10 minutes)

Use this method for planned rollbacks or when you have a few minutes to ensure proper deployment.

### Step 1: Identify Target Commit

1. **Find Working Commit**:
   ```bash
   # View recent commits
   git log --oneline -10
   
   # Example output:
   # abc123d Fix critical bug
   # def456e Add new feature (current - broken)
   # ghi789f Update documentation
   ```

2. **Verify Commit SHA**: Note the full commit SHA you want to rollback to

### Step 2: Re-run GitHub Workflow

1. **Access GitHub Actions**:
   - Go to your repository on GitHub
   - Click "Actions" tab
   - Click "Deploy to Production" workflow

2. **Find Target Workflow Run**:
   - Locate the workflow run for the target commit
   - Click on the workflow run

3. **Re-run Workflow**:
   - Click "Re-run all jobs" button
   - Confirm the re-run
   - Monitor progress in the Actions tab

### Step 3: Verify Rollback

1. **Check Deployment Status**:
   - Monitor the GitHub Actions workflow progress
   - Verify all jobs complete successfully

2. **Test Application**:
   - Visit your deployment URL
   - Verify core functionality works
   - Check health endpoint: `https://your-app.com/health`

## Planned Rollback (10-15 minutes)

Use this method when you want to create a new deployment with rollback changes.

### Step 1: Create Rollback Branch

```bash
# Create rollback branch from target commit
git checkout -b rollback-to-abc123 abc123d

# Push rollback branch
git push origin rollback-to-abc123
```

### Step 2: Create Pull Request

1. **Open Pull Request**:
   - Create PR from rollback branch to main
   - Title: "Rollback to commit abc123d - Fix critical bug"
   - Description: Explain reason for rollback

2. **Review and Merge**:
   - Have team review the rollback
   - Merge PR to main branch
   - Automatic deployment will trigger

### Step 3: Clean Up

```bash
# After successful rollback, delete rollback branch
git branch -d rollback-to-abc123
git push origin --delete rollback-to-abc123
```

## Image Tag Reference

Docker images are tagged with this pattern:
- `main` - Latest main branch deployment
- `main-{commit-sha}` - Specific commit deployment
- Example: `ghcr.io/username/repo:main-abc123d`

### Finding Image Tags

1. **GitHub Container Registry**:
   - Go to your repository
   - Click "Packages" tab
   - Click your container package
   - View all available tags

2. **Command Line**:
   ```bash
   # List all tags for your repository
   curl -H "Authorization: Bearer $GITHUB_TOKEN" \
        https://ghcr.io/v2/username/repo/tags/list
   ```

## Verification Checklist

After any rollback, verify:

- [ ] **Application Loads**: Main URL responds with 200 status
- [ ] **Health Check**: `/health` endpoint returns healthy status
- [ ] **Core Functionality**: Test primary user flows
- [ ] **API Endpoints**: Test `/docs` and `/redoc` endpoints
- [ ] **Logs**: Check application logs for errors
- [ ] **Performance**: Verify acceptable response times

## Common Rollback Scenarios

### Scenario 1: New Feature Broke Core Functionality

**Symptoms**: 500 errors, API endpoints not responding
**Solution**: Emergency rollback to last known working deployment
**Method**: Platform console rollback

### Scenario 2: Performance Degradation

**Symptoms**: Slow response times, timeouts
**Solution**: Standard rollback with monitoring
**Method**: Re-run GitHub workflow

### Scenario 3: Security Issue Discovered

**Symptoms**: Security vulnerability in new code
**Solution**: Immediate emergency rollback
**Method**: Platform console + hotfix deployment

### Scenario 4: Dependency Issue

**Symptoms**: Import errors, missing packages
**Solution**: Rollback to stable dependencies
**Method**: Planned rollback with proper testing

## Rollback Testing

### Pre-rollback Validation

```bash
# Test target commit locally
git checkout abc123d
python scripts/bmad2pf.py --src ./bmad --out ./generated
pytest tests/ -v
uvicorn generated.app:app --port 8000
```

### Post-rollback Testing

```bash
# Health check
curl -f https://your-app.com/health

# API documentation
curl -f https://your-app.com/docs

# Core endpoint
curl -f https://your-app.com/run \
  -H "Content-Type: application/json" \
  -d '{"flow":"default","input":"test","story_id":"test"}'
```

## Prevention Best Practices

### Before Deployment
- Run full test suite locally
- Test in staging environment if available
- Have rollback plan ready
- Notify team of deployment

### During Deployment
- Monitor deployment logs
- Test immediately after deployment
- Have team member available for verification

### After Deployment
- Monitor for 30 minutes after deployment
- Check error logs
- Verify key metrics remain stable

## Contact Information

For rollback assistance:
- **Emergency**: Contact on-call engineer
- **Standard**: Create issue in repository
- **Questions**: Refer to CI/CD process documentation

## Rollback History

Keep track of rollbacks for analysis:

| Date | Reason | Method | Duration | Success |
|------|--------|--------|----------|---------|
| [Date] | [Reason] | [Method] | [Time] | [Y/N] |

---

*These rollback instructions are part of the BMAD → PocketFlow deployment process. Keep this document updated with any changes to rollback procedures.*