# Production Considerations

This document outlines production deployment patterns, monitoring, security, and scaling considerations for the Ticket Triage Agent.

## Deployment Architecture

### Recommended Setup

```
┌─────────────────────────────────────────────────────────────┐
│ Load Balancer (Nginx/HAProxy)                              │
│ - SSL/TLS termination                                       │
│ - Rate limiting                                             │
│ - Request routing                                           │
└────────────┬────────────────────────────────────────────────┘
             │
    ┌────────┴───────────┬──────────────────┐
    │                    │                  │
┌───▼──────┐        ┌───▼──────┐      ┌───▼──────┐
│ Triage   │        │ Triage   │      │ Triage   │
│ Instance │        │ Instance │      │ Instance │
│ (Docker) │        │ (Docker) │      │ (Docker) │
└───┬──────┘        └───┬──────┘      └───┬──────┘
    │                   │                  │
    └───────────┬───────┴──────────┬───────┘
                │                  │
         ┌──────▼────────┐   ┌─────▼──────────┐
         │ Redis Cluster │   │ Log Aggregator │
         │ (3+ nodes)    │   │ (ELK/Datadog)  │
         └───────────────┘   └────────────────┘
```

### Container Orchestration

**Kubernetes**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ticket-triage
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ticket-triage
  template:
    metadata:
      labels:
        app: ticket-triage
    spec:
      containers:
      - name: ticket-triage
        image: ticket-triage:latest
        ports:
        - containerPort: 8000
        env:
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: redis-url
        - name: GOOGLE_API_KEY
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: google-api-key
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
```

### Environment-Specific Configuration

**Development**:
```bash
API_DEBUG=true
LOG_LEVEL=DEBUG
CACHE_ENABLED=false
LLM_TEMPERATURE=0.3  # Higher for exploration
```

**Staging**:
```bash
API_DEBUG=false
LOG_LEVEL=INFO
CACHE_ENABLED=true
CACHE_TTL_SECONDS=1800
LLM_TEMPERATURE=0.1
```

**Production**:
```bash
API_DEBUG=false
LOG_LEVEL=INFO
CACHE_ENABLED=true
CACHE_TTL_SECONDS=3600
LLM_TEMPERATURE=0.1
RATE_LIMIT_ENABLED=true
ADMIN_TOKEN=<secure-random-token>
SENTRY_DSN=<sentry-url>
```

## Secrets Management

### Best Practices

1. **Never commit secrets**:
   - Add `.env` to `.gitignore`
   - Use `.env.example` as template
   - Review all commits with `git diff --cached`

2. **Use secrets manager**:

   **AWS**:
   ```python
   import boto3
   client = boto3.client('secretsmanager')
   secret = client.get_secret_value(SecretId='ticket-triage/api-keys')
   ```

   **Azure**:
   ```python
   from azure.identity import DefaultAzureCredential
   from azure.keyvault.secrets import SecretClient
   credential = DefaultAzureCredential()
   client = SecretClient(vault_url="https://<vault>.vault.azure.net/", credential=credential)
   secret = client.get_secret("api-key")
   ```

   **HashiCorp Vault**:
   ```python
   import hvac
   client = hvac.Client(url='http://127.0.0.1:8200', token='mytoken')
   secret = client.secrets.kv.read_secret_version(path='ticket-triage')
   ```

3. **Rotate secrets regularly**:
   - Rotate API keys monthly
   - Update database credentials quarterly
   - Review access logs for suspicious activity

## Scaling Considerations

### Horizontal Scaling

The application is stateless and scales horizontally. Deploy behind a load balancer:

**Request Distribution**:
- Use round-robin or least-connections
- Enable connection pooling
- Set appropriate timeouts (30s for LLM calls)

**Database/Cache Scaling**:
- Use Redis cluster for multi-node setup
- Configure appropriate eviction policies: `maxmemory-policy allkeys-lru`
- Monitor memory usage and set alerts

### LLM Provider Rate Limits

Monitor and respect provider limits:

**OpenAI**:
- Tier 1: 3,500 RPM, $5/month
- Tier 2: 90,000 RPM, $100/month
- Higher tiers available

**Google Gemini**:
- Free: 60 req/min
- Standard: 1,500 req/min with API key

**Groq**:
- Community: No limit
- Pro: Custom limits

**Response to limits**:
1. Implement request queuing
2. Use exponential backoff (built-in via tenacity)
3. Switch to next provider in preference list
4. Use fallback mode if all providers exhausted

### Performance Optimization

**Caching Strategy**:
```
Cache hit rate target: >70%
TTL settings:
- Exact matches: 3600 seconds (1 hour)
- Similar requests: 1800 seconds (30 min)
- KB searches: 600 seconds (10 min)
```

**Database Query Performance**:
- Index KB by category and symptoms
- Pre-compute embeddings if using semantic search
- Use connection pooling

**Response Time Targets**:
- P50: <500ms (cache hit)
- P95: <2000ms (LLM call)
- P99: <5000ms (worst case)

## Monitoring & Observability

### Structured Logging

All logs are JSON-formatted with:
- `request_id` - unique request identifier
- `timestamp` - ISO 8601 format
- `level` - severity level
- `logger` - component name
- `message` - log message
- `provider` - LLM provider used
- `latency_ms` - request latency
- `cache_hit` - cache status
- `error` - error message if applicable

**Log aggregation setup** (ELK stack):

```python
# Send logs to Elasticsearch
import logging
from pythonjsonlogger import jsonlogger

logger = logging.getLogger()
handler = logging.FileHandler('ticket-triage.json')
formatter = jsonlogger.JsonFormatter()
handler.setFormatter(formatter)
logger.addHandler(handler)
```

### Metrics & Alerting

Key metrics to track:

```
# Request metrics
triage_requests_total (Counter)
triage_request_duration_ms (Histogram)
triage_cache_hits (Counter)
triage_cache_misses (Counter)

# LLM metrics
llm_requests_total (Counter)
llm_errors_total (Counter)
llm_latency_ms (Histogram)
llm_provider_switches (Counter)

# System metrics
redis_connection_errors (Counter)
llm_provider_unavailable (Counter)
fallback_mode_activated (Counter)
```

**Alert thresholds**:
- Error rate > 5% → Page oncall
- P95 latency > 5s → Warning
- Cache hit rate < 50% → Investigate
- Any provider unavailable > 30min → Alert

### Sentry Integration

Enable error tracking:

```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    integrations=[FastApiIntegration()],
    traces_sample_rate=0.1,
    environment=os.getenv("ENVIRONMENT", "production"),
)
```

### Health Checks

Implement comprehensive health checks:

```bash
# Basic health
GET /health
→ 200 OK with status

# Readiness check
GET /readiness
→ 200 only if all dependencies available

# Liveness check
GET /live
→ 200 always (pod restart if false)
```

## Security

### API Security

1. **Authentication & Authorization**:
   - Use OAuth2/JWT for API access
   - Implement API key rotation
   - Require HTTPS/TLS for all traffic

2. **Rate Limiting**:
   ```python
   # Per IP
   RATE_LIMIT_REQUESTS_PER_MINUTE=60
   
   # Per API key
   RATE_LIMIT_KEY_RPM=1000
   
   # Burst protection
   RATE_LIMIT_BURST=10
   ```

3. **Input Validation**:
   - Max description length: 10,000 chars
   - Prevent SQL injection (parameterized queries)
   - Validate JSON structure
   - Sanitize output

### Container Security

```dockerfile
# Run as non-root user
RUN useradd -m -u 1000 appuser
USER appuser

# Read-only filesystem
RUN chmod 444 /app/kb/sample_kb.json

# No secrets in image
# Use environment variables or mounted secrets
```

**Scanning**:
```bash
# Scan image for vulnerabilities
trivy image ticket-triage:latest

# Scan dependencies
pip-audit -r requirements.txt
```

### Data Protection

1. **Data in transit**: TLS 1.3
2. **Data at rest**: Encrypt cache with Redis ACL
3. **Secrets**: Never log API keys, use masking
4. **Audit trails**: Log all cache purges, admin actions

## Disaster Recovery

### Backup Strategy

1. **Knowledge Base**:
   - Version control in Git
   - Daily backup to S3
   - Test restores weekly

2. **Redis Cache**:
   - Enable RDB snapshots (hourly)
   - Use Redis replication
   - Backup to S3

3. **Logs**:
   - Retain in log aggregation for 90 days
   - Archive to S3 for long-term retention

### Recovery Procedures

**Complete outage**:
1. Restore Redis from latest snapshot
2. Redeploy app instances from container registry
3. Verify health checks
4. Gradual traffic shift (canary deployment)

**Data corruption**:
1. Flush Redis cache
2. Verify KB integrity
3. Resume operations (cache will repopulate)

**Partial failure**:
1. Single instance failure → LB removes and restarts
2. Redis failure → Gracefully degrade without caching
3. LLM provider failure → Automatic failover to next provider

## Cost Optimization

### LLM API Costs

Estimate costs per 1M requests:

| Provider | Cost | Speed | Quality |
|----------|------|-------|---------|
| Groq (free) | $0 | Fastest | Good |
| Google Gemini | ~$0.50 | Fast | Excellent |
| OpenAI 3.5-turbo | ~$2 | Medium | Good |
| OpenAI 4o-mini | ~$0.15 | Medium | Excellent |

**Optimization strategies**:
- Use Groq for free tier
- Cache aggressively (>70% hit rate)
- Batch requests during off-peak hours
- Monitor token usage

### Infrastructure Costs

**AWS Example** (1000 req/day):
- 3× t3.small EC2: ~$50/month
- ElastiCache Redis: ~$30/month
- Data transfer: ~$10/month
- **Total: ~$90/month**

With volume discounts and reserved instances: ~$50-60/month

## Maintenance

### Regular Tasks

**Daily**:
- Monitor error rates and latency
- Review alerts and escalations
- Check disk space on log storage

**Weekly**:
- Review performance metrics
- Test backup restoration
- Update security patches

**Monthly**:
- Update dependencies
- Rotate secrets
- Review access logs
- Performance tuning

**Quarterly**:
- Penetration testing
- Disaster recovery drill
- Capacity planning

### Rollout Strategy

**Canary Deployment**:
```
1. Deploy to 5% of traffic (canary)
2. Monitor metrics for 1 hour
3. If good, roll to 25%, then 50%, then 100%
4. If issues, automatic rollback to previous version
```

**Blue-Green Deployment**:
```
Blue (current) → Green (new) → Test → Switch → Monitor
```

## Compliance & Auditing

### Requirements

- **GDPR**: Customer data encryption, right to deletion
- **SOC 2**: Access controls, audit logging
- **HIPAA**: If handling health data, additional encryption
- **CCPA**: Customer data requests, opt-out support

### Audit Logging

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "action": "triage",
  "user": "api-key-xxx",
  "resource": "TICKET-12345",
  "result": "SUCCESS",
  "details": {
    "category": "Bug",
    "severity": "High"
  }
}
```

## Support & Runbooks

### Common Issues

**High latency**:
1. Check LLM provider status
2. Monitor Redis connection pool
3. Review LLM response times
4. Check network latency

**Cache misses increasing**:
1. Review TTL settings
2. Monitor Redis memory usage
3. Check eviction policy
4. Analyze request patterns

**Provider failures**:
1. Check API key validity and quota
2. Review rate limit status
3. Check network connectivity
4. Verify provider status page

See README.md for API documentation and examples.

## References

- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [OWASP API Security](https://owasp.org/www-project-api-security/)
- [12-Factor App Principles](https://12factor.net/)
- [SRE Best Practices](https://sre.google/books/)
