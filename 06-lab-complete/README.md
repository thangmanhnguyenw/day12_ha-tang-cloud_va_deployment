# Lab 12 — Complete Production Agent

Kết hợp TẤT CẢ concepts Day 12 trong một project production-ready.

## Cấu trúc

```
06-lab-complete/
├── app/
│   ├── main.py           # FastAPI entry point
│   ├── config.py         # 12-factor config
│   ├── auth.py           # API Key authentication
│   ├── rate_limiter.py   # Redis sliding window (10 req/min)
│   ├── cost_guard.py     # Monthly budget ($10/user)
│   └── storage.py        # Redis conversation history
├── utils/
│   └── mock_llm.py       # Mock LLM (no API key needed)
├── Dockerfile            # Multi-stage, < 500 MB
├── docker-compose.yml    # Nginx + Agent + Redis
├── nginx.conf            # Load balancer
├── railway.toml          # Railway deploy
├── render.yaml           # Render deploy
├── .env.example
├── .dockerignore
└── requirements.txt
```

## Chạy local

```bash
cd 06-lab-complete
cp .env.example .env
# Sửa AGENT_API_KEY trong .env

# Full stack với load balancer (3 agent instances)
docker compose up --build --scale agent=3
```

## Test endpoints

```bash
# Health (qua Nginx)
curl http://localhost/health

# Readiness
curl http://localhost/ready

# Ask (cần API key từ .env)
curl -H "X-API-Key: dev-key-change-me-in-production" \
     -X POST http://localhost/ask \
     -H "Content-Type: application/json" \
     -d '{"question": "What is Docker?", "user_id": "user1"}'

# Không có key → 401
curl -X POST http://localhost/ask \
     -H "Content-Type: application/json" \
     -d '{"question": "Hello"}'
```

## Kiểm tra production readiness

```bash
cd 06-lab-complete
python check_production_ready.py
```

## Deploy

**Railway:** `railway init` → set `AGENT_API_KEY`, `REDIS_URL` → `railway up`

**Render:** Push GitHub → New Blueprint → connect repo → set secrets trong dashboard
