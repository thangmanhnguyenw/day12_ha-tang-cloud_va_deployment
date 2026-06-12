# Deployment Information

## Public URL

https://day12-production-8379.up.railway.app

## Platform

Railway (project: `day12`, service: `day12` + Redis)

## Test Commands

### Health Check

```bash
curl https://day12-production-8379.up.railway.app/health
```

Expected: `{"status":"ok",...,"storage":"redis","redis_connected":true}`

### Readiness

```bash
curl https://day12-production-8379.up.railway.app/ready
```

### API Test (with authentication)

```bash
curl -X POST https://day12-production-8379.up.railway.app/ask \
  -H "X-API-Key: my-secret-key" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test", "question": "Hello"}'
```

### Without API key (expect 401)

```bash
curl -X POST https://day12-production-8379.up.railway.app/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello"}'
```

## Environment Variables Set

| Variable | Value |
|----------|-------|
| `ENVIRONMENT` | production |
| `AGENT_API_KEY` | my-secret-key |
| `REDIS_URL` | `${{Redis.REDIS_URL}}` (internal) |
| `RATE_LIMIT_PER_MINUTE` | 10 |
| `MONTHLY_BUDGET_USD` | 10.0 |
| `APP_VERSION` | 1.0.0 |

## Redeploy

```bash
cd e:\ai\day12_ha-tang-cloud_va_deployment
railway service link day12
railway up 06-lab-complete --path-as-root --detach -y --no-gitignore
```
