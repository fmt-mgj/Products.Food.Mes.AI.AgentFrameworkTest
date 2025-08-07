# Monitoring and Logging Guide

## Overview
This guide covers monitoring and logging access for each deployment platform.

## Railway

### Logging
- **Access**: Railway dashboard → Service → Logs tab
- **Features**: 
  - Real-time log streaming
  - Log filtering by level
  - Search functionality
  - Download logs

### Metrics
- **Access**: Railway dashboard → Service → Metrics tab
- **Available Metrics**:
  - CPU usage
  - Memory usage
  - Request count
  - Response times
  - Error rates

### Alerts
- **Configuration**: Settings → Notifications
- **Setup Steps**:
  1. Go to Railway dashboard
  2. Select your service
  3. Navigate to Settings → Notifications
  4. Configure alerts for:
     - High CPU usage (>80%)
     - High memory usage (>80%)
     - Error rate spikes
     - Service downtime

## Fly.io

### Logging
- **CLI Access**: `fly logs`
- **Dashboard Access**: dashboard.fly.io
- **Features**:
  - Real-time log tailing
  - Historical log search
  - Log aggregation across regions

### Metrics
- **CLI Access**: `fly status`
- **Dashboard**: Built-in metrics in dashboard
- **Available Metrics**:
  - Instance status
  - Request metrics
  - Resource usage
  - Geographic distribution

### Monitoring Integration
- **Datadog**: Set environment variable `DD_API_KEY`
- **New Relic**: Set environment variable `NEW_RELIC_LICENSE_KEY`
- **Configuration**:
  ```bash
  fly secrets set DD_API_KEY=your_datadog_key
  fly secrets set NEW_RELIC_LICENSE_KEY=your_newrelic_key
  ```

## Google Cloud Run

### Logging
- **Access**: Cloud Console → Cloud Run → Logs
- **Features**:
  - Structured logging
  - Log-based metrics
  - Integration with Cloud Logging
  - Advanced filtering and search

### Metrics
- **Access**: Cloud Console → Cloud Run → Metrics
- **Available Metrics**:
  - Request count
  - Request latencies
  - Container instance count
  - CPU utilization
  - Memory utilization
  - Billable time

### Monitoring
- **Cloud Monitoring**: Automatic integration
- **Features**:
  - Custom dashboards
  - Alerting policies
  - SLO monitoring
  - Error reporting

### Tracing
- **Cloud Trace**: Automatic integration
- **Features**:
  - Distributed tracing
  - Latency analysis
  - Performance insights

## Setting Up Monitoring

### Health Check Endpoint
All platforms use the `/health` endpoint for health checks:

```python
# In your FastAPI app
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}
```

### Structured Logging
Use structured logging for better observability:

```python
import logging
import json

# Configure structured logging
logging.basicConfig(
    format='%(asctime)s %(levelname)s %(message)s',
    level=logging.INFO
)

# Log structured data
logger.info(json.dumps({
    "event": "request_processed",
    "method": "POST",
    "path": "/run",
    "duration_ms": 150,
    "status": 200
}))
```

### Environment Variables for Monitoring

#### Railway
```bash
# Set via Railway dashboard or CLI
railway variables set LOG_LEVEL=info
railway variables set ENABLE_METRICS=true
```

#### Fly.io
```bash
# Set via fly CLI
fly secrets set LOG_LEVEL=info
fly secrets set ENABLE_METRICS=true
```

#### Cloud Run
```bash
# Set via gcloud or in cloud-run-service.yaml
gcloud run services update bmad-pocketflow \
  --set-env-vars LOG_LEVEL=info,ENABLE_METRICS=true
```

## Troubleshooting Common Issues

### High Memory Usage
1. Check for memory leaks in application logs
2. Monitor memory usage patterns
3. Adjust container memory limits if needed

### High CPU Usage
1. Identify CPU-intensive operations
2. Check for infinite loops or blocking operations
3. Consider horizontal scaling

### Request Timeouts
1. Check application response times
2. Verify health check endpoints
3. Review timeout configurations

### Service Downtime
1. Check deployment logs
2. Verify container startup
3. Review health check failures
4. Check resource limits

## Best Practices

1. **Set up alerts** for critical metrics across all platforms
2. **Use structured logging** for better searchability
3. **Monitor health checks** to catch issues early
4. **Set appropriate timeout values** for your workload
5. **Regular log review** to identify patterns and issues