# Modal Labs Deployment Guide with Memory Management

This guide provides step-by-step instructions for deploying MayaMCP to Modal Labs with the new memory management and session monitoring features.

## 📋 Prerequisites

1. **Modal Account**: Active Modal Labs account with billing configured
2. **Modal CLI**: Installed and authenticated (`pip install modal` and `modal setup`)
3. **Environment Variables**: Copy `.env.example` to `.env` and configure required variables
4. **Git Repository**: Clean working directory with committed changes

## 🚀 Quick Start Deployment

### 1. Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit with your configuration
nano .env
```

**Required Variables:**
```bash
# API Keys (server-side fallbacks)
GEMINI_API_KEY=your_gemini_api_key_here
CARTESIA_API_KEY=your_cartesia_api_key_here

# Modal Memory Management (NEW)
MAYA_SESSIONS_PER_CONTAINER=50       # Sessions per container
MAYA_DEFAULT_SESSION_MEMORY_MB=50     # Memory per session
MAYA_CONTAINER_MEMORY_THRESHOLD=0.8    # Memory pressure threshold
MAYA_SESSION_EXPIRY_SECONDS=3600       # Session timeout (1 hour)
MAYA_CLEANUP_INTERVAL_SECONDS=300      # Cleanup interval (5 minutes)

# Modal Container Configuration
MODAL_MEMORY_MB=4096                  # Read by deploy.py — project-defined, not automatically applied by Modal
MODAL_MAX_CONTAINERS=5                # Read by deploy.py — project-defined, not automatically applied by Modal
```

### 2. Deploy to Modal

```bash
# Development deployment (with hot reload)
modal serve deploy.py

# Production deployment
modal deploy deploy.py
```

### 3. Verify Deployment

```bash
# Check deployment status
modal app list

# Test health endpoint
curl https://your-workspace--mayamcp.modal.run/healthz

# Check metrics
curl https://your-workspace--mayamcp.modal.run/metrics
```

## 🔧 Advanced Configuration

### Memory Management Tuning

#### Small Deployment (Development)
```bash
# .env configuration
MAYA_SESSIONS_PER_CONTAINER=50
MAYA_DEFAULT_SESSION_MEMORY_MB=25
MAYA_CONTAINER_MEMORY_THRESHOLD=0.8
MODAL_MEMORY_MB=2048
MODAL_MAX_CONTAINERS=2
```

#### Medium Deployment (Production)
```bash
# .env configuration
MAYA_SESSIONS_PER_CONTAINER=50
MAYA_DEFAULT_SESSION_MEMORY_MB=50
MAYA_CONTAINER_MEMORY_THRESHOLD=0.8
MODAL_MEMORY_MB=4096
MODAL_MAX_CONTAINERS=5
```

#### Large Deployment (High Traffic)
```bash
# .env configuration
MAYA_SESSIONS_PER_CONTAINER=100
MAYA_DEFAULT_SESSION_MEMORY_MB=75
MAYA_CONTAINER_MEMORY_THRESHOLD=0.75
MODAL_MEMORY_MB=8192
MODAL_MAX_CONTAINERS=10
```

### Custom Modal Image Configuration

For production deployments, you may want to customize the Modal image:

```python
# deploy.py - Custom image configuration
image = (
    modal.Image.debian_slim()
    .pip_install_from_requirements("requirements.txt")
    .apt_install("curl")  # Additional system packages
    .env({"PYTHONPATH": "/root"})  # Environment variables
)

app = modal.App(name="mayamcp-production")

@app.function(
    image=image,
    secrets=[modal.Secret.from_name("maya-secrets")]
)
def some_function():
    pass
```

## 📊 Monitoring and Observability

### Health Checks

The deployment includes comprehensive health monitoring:

```bash
# Basic health check
curl https://your-workspace--mayamcp.modal.run/healthz

# Expected response (healthy)
{
  "status": "healthy",
  "checks": [],
  "timestamp": "2024-02-23T18:55:00Z"
}

# Expected response (memory pressure)
{
  "status": "unhealthy",
  "checks": ["Container memory pressure detected"],
  "timestamp": "2024-02-23T18:55:00Z"
}
```

### Metrics Endpoint

Comprehensive metrics available at `/metrics`:

```bash
# Get all metrics
curl https://your-workspace--mayamcp.modal.run/metrics

# Key metrics to monitor:
# - maya_container_memory_usage_bytes
# - maya_container_memory_utilization
# - maya_active_sessions
# - maya_session_utilization
# - maya_sessions_created_total
# - maya_sessions_rejected_total
# - maya_sessions_expired_total
```

### Grafana Dashboard Integration

```promql
# Example Prometheus queries for Grafana

# Container Memory Usage
maya_container_memory_utilization * 100

# Session Utilization
maya_session_utilization * 100

# Session Rejection Rate
rate(maya_sessions_rejected_total[5m]) * 60

# Memory Pressure Alerts
maya_container_memory_utilization > 0.8
```

## 🔒 Security Configuration

### Secret Management

You can define secrets directly in your deployment script using `modal.Secret.from_dict`:

```python
# Example of defining secrets in deploy.py
maya_secrets = modal.Secret.from_dict({
    "GEMINI_API_KEY": "your_production_gemini_key",
    "CARTESIA_API_KEY": "your_production_cartesia_key",
    "MAYA_MASTER_KEY": "your_encryption_key"
})
```

Alternatively, create them via the Modal CLI:
```bash
modal secret create maya-secrets GEMINI_API_KEY=... CARTESIA_API_KEY=... MAYA_MASTER_KEY=...
```

### Environment Variables Security

For production, use Modal secrets instead of `.env` file:

```python
# deploy.py - Secure configuration
app = modal.App(name="mayamcp-production")

@app.function(
    secrets=[modal.Secret.from_name("maya-secrets")]
)
def secure_function():
    pass
```

## 🚀 Deployment Strategies

### Blue-Green Deployment

```bash
# Deploy to staging
modal deploy deploy.py --name mayamcp-staging

# Test staging deployment
curl https://your-workspace--mayamcp-staging.modal.run/healthz

# Promote to production (redeploy with production name)
modal deploy deploy.py --name mayamcp-production
```

> [!NOTE]
> Modal CLI does not have a direct "update" or "promote" subcommand for `app`. Available `modal app` subcommands are limited to `list`, `logs`, `rollback`, `stop`, `history`, and `dashboard`. To promote a staging app to production, simply redeploy the same script with the production name using `modal deploy`.

### Canary Deployment

```bash
# Deploy canary with reduced traffic
modal deploy deploy.py --name mayamcp-canary

# Gradually increase traffic (requires load balancer)
# Monitor metrics for canary vs production
```

### Rollback Strategy

```bash
# List previous deployments
modal app list

# Rollback to previous version
modal app rollback mayamcp-production --to <previous-deployment-id>
```

## 🔍 Troubleshooting

### Common Issues

#### 1. Memory Pressure Errors

**Symptoms:**
- Health checks return "unhealthy"
- Sessions being rejected
- High memory utilization metrics

**Solutions:**
```bash
# Check current memory usage
curl https://your-workspace--mayamcp.modal.run/metrics | grep memory

# Reduce session memory allocation
export MAYA_DEFAULT_SESSION_MEMORY_MB=25
export MAYA_CONTAINER_MEMORY_THRESHOLD=0.7

# Increase container memory
# Edit deploy.py: memory=8192
modal deploy deploy.py
```

#### 2. Session Limit Reached

**Symptoms:**
- "Session limit reached" errors
- High session utilization metrics

**Solutions:**
```bash
# Increase session limit
export MAYA_SESSIONS_PER_CONTAINER=150

# Or increase container count
# Edit deploy.py: MODAL_MAX_CONTAINERS=10
modal deploy deploy.py
```

#### 3. Slow Container Startup

**Symptoms:**
- Cold start delays
- Timeout errors

**Solutions:**
```bash
# Use Modal's container keep-alive
# Edit deploy.py: min_containers=1
modal deploy deploy.py

# Or use persistent volumes for model caching
weights_cache = modal.Volume.from_name("model-cache", create_if_missing=True)
```

### Debug Mode

```bash
# Enable debug logging
export MAYA_LOG_LEVEL=DEBUG

# Deploy with debug
modal serve deploy.py --log-level debug

# View container logs
modal app logs mayamcp-production --follow
```

## 📈 Performance Optimization

### Memory Optimization

1. **Monitor Memory Patterns**
   ```bash
   # Track memory usage over time
   watch -n 5 'curl -s https://your-workspace--mayamcp.modal.run/metrics | grep memory'
   ```

2. **Optimize Session Memory**
   ```bash
   # Start with conservative limits
   MAYA_DEFAULT_SESSION_MEMORY_MB=25
   MAYA_CONTAINER_MEMORY_THRESHOLD=0.7
   
   # Gradually increase based on usage patterns
   ```

3. **Use Persistent Volumes**
   ```python
   # deploy.py - Add volume caching
   model_cache = modal.Volume.from_name("maya-model-cache", create_if_missing=True)
   
   @app.cls(volumes={"/cache": model_cache})
   class MayaApp:
       @modal.enter()
       def setup(self):
           # Cache models in persistent volume
           pass
   ```

### Scaling Optimization

1. **Horizontal Scaling**
   ```bash
   # Increase container count for traffic
   MODAL_MAX_CONTAINERS=10
   ```

2. **Vertical Scaling**
   ```bash
   # Increase container memory
   MODAL_MEMORY_MB=8192
   ```

3. **Auto-scaling Setup**
   ```python
   # deploy.py - Auto-scaling configuration
   @app.function(
       max_containers=20,
       min_containers=2,
       scaledown_window=300
   )
   ```

## 🔄 Maintenance

### Regular Maintenance Tasks

1. **Daily Health Checks**
   ```bash
   # Automated health check script
   #!/bin/bash
   HEALTH=$(curl -s https://your-workspace--mayamcp.modal.run/healthz | jq -r '.status')
   if [ "$HEALTH" != "healthy" ]; then
       echo "Alert: MayaMCP unhealthy!"
       # Send notification
   fi
   ```

2. **Weekly Metrics Review**
   ```bash
   # Export metrics for analysis
   curl -s https://your-workspace--mayamcp.modal.run/metrics > metrics-$(date +%Y%m%d).txt
   ```

3. **Monthly Updates**
   ```bash
   # Update direct dependencies in requirements.in first
   # Then regenerate requirements.txt using pip-compile (from pip-tools)
   pip-compile --upgrade requirements.in
   
   # Commit both files to maintain reproducible builds
   git add requirements.in requirements.txt
   git commit -m "Update dependencies using pip-compile"
   
   # Redeploy with updated dependencies
   modal deploy deploy.py
   ```

### Backup and Recovery

1. **Configuration Backup**
   ```bash
   # Backup environment configuration
   cp .env .env.backup.$(date +%Y%m%d)
   ```

2. **State Backup**
   ```bash
   # Modal automatically handles state persistence
   # For additional backup, export critical data
   modal volume list
   ```

## 📚 Additional Resources

- [Modal Documentation](https://modal.com/docs)
- [Modal Python API](https://modal.com/docs/reference)
- [MayaMCP Repository](https://github.com/MOK-5-ha/MayaMCP)
- [Memory Implementation Details](./MODAL_MEMORY_IMPLEMENTATION_SUMMARY.md)

## 🆘 Support

For deployment issues:

1. Check [troubleshooting section](#-troubleshooting)
2. Review Modal logs: `modal app logs mayamcp-production`
3. Check metrics: `/metrics` endpoint
4. Contact support with deployment ID and error logs

---

**Deployment Success!** 🎉

Your MayaMCP application is now running with advanced memory management and session monitoring on Modal Labs. Monitor the metrics dashboard and health checks to ensure optimal performance.
