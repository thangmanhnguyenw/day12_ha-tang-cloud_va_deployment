# Delivery Checklist — Day 12 Lab Submission

> **Student Name:** _________________________  
> **Student ID:** _________________________  
> **Date:** _________________________

---

# Day 12 Lab - Mission Answers

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found

1. API key hardcode trong code
2. Không có health check endpoint
3. Debug mode bật cứng
4. Không xử lý SIGTERM gracefully
5. Config không đến từ environment

### Exercise 1.3: Comparison table


| Feature      | Develop                 | Production                             | Why Important? |
| ------------ | ----------------------- | -------------------------------------- | -------------- |
| Config       | Hardcode trong code     | Đọc từ env vars                        |                |
| Secrets      | `api_key = "sk-abc123"` | `os.getenv("OPENAI_API_KEY")`          |                |
| Port         | Cố định `8000`          | Từ `PORT` env var                      |                |
| Health check | Không có                | `GET /health`                          |                |
| Shutdown     | Tắt đột ngột            | Graceful — hoàn thành request hiện tại |                |
| Logging      | `print()`               | Structured JSON logging                |                |


---

## Part 2: Docker

### Exercise 2.1: Dockerfile questions

1. Base image: `python:3.11`
2. Working directory: WORKDIR /app

...

### Exercise 2.3: Image size comparison

- Develop: 1.66 GB 
- Production: [Y] 236 MB
- Difference: [Z]%

## Part 3: Cloud Deployment

### Exercise 3.1: Railway deployment

- URL: [https://your-app.railway.app](https://your-app.railway.app)
- Screenshot:E:\ai\day12_ha-tang-cloud_va_deployment\03-cloud-deployment\e50cfc2b-083b-49da-bd5e-c37c73faabff.png

## Part 4: API Security

### Exercise 4.1-4.3: Test results

{"detail":"Missing API key. Include header: X-API-Key: "}

{"detail":"Invalid API key."}

{"question":"Explain JWT","answer":"Tôi là AI agent được deploy lên cloud. Câu hỏi của bạn đã được nhận.","usage":{"requests_remaining":9,"budget_remaining_usd":1.9e-05}}

{"access_token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJzdHVkZW50Iiwicm9sZSI6InVzZXIiLCJpYXQiOjE3ODEyNTYzMjcsImV4cCI6MTc4MTI1OTkyN30.WYxe2UYF9t8IJssA4utA98hA0XVOa7bD1udqrNY8UaE","token_type":"bearer","expires_in_minutes":60,"hint":"Include in header: Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."}

{"question":"Explain JWT","answer":"Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé.","usage":{"requests_remaining":9,"budget_remaining_usd":1.6e-05}} 

{"question":"Test 1","answer":"Đây là câu trả lời từ AI agent (mock). Trong production, 

đây sẽ là response từ OpenAI/Anthropic.","usage":{"requests_remaining":8,"budget_remaining_usd":3.7e-05}}

{"question":"Test 2","answer":"Tôi là AI agent được deploy lên cloud. Câu hỏi của bạn đã được nhận.","usage":{"requests_remaining":7,"budget_remaining_usd":5.6e-05}}

{"question":"Test 3","answer":"Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé.","usage":{"requests_remaining":6,"budget_remaining_usd":7.2e-05}}

{"question":"Test 4","answer":"Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé.","usage":{"requests_remaining":5,"budget_remaining_usd":8.8e-05}}

{"question":"Test 5","answer":"Tôi là AI agent được deploy lên cloud. Câu hỏi của bạn đã được nhận.","usage":{"requests_remaining":4,"budget_remaining_usd":0.000107}}

{"question":"Test 6","answer":"Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé.","usage":{"requests_remaining":3,"budget_remaining_usd":0.000123}}

{"question":"Test 7","answer":"Đây là câu trả lời từ AI agent (mock). Trong production, 

đây sẽ là response từ OpenAI/Anthropic.","usage":{"requests_remaining":2,"budget_remaining_usd":0.000144}}

{"question":"Test 8","answer":"Agent đang hoạt động tốt! (mock response) Hỏi thêm câu hỏi đi nhé.","usage":{"requests_remaining":1,"budget_remaining_usd":0.00016}}

{"question":"Test 9","answer":"Đây là câu trả lời từ AI agent (mock). Trong production, 

đây sẽ là response từ OpenAI/Anthropic.","usage":{"requests_remaining":0,"budget_remaining_usd":0.000181}}

{"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":32}}

{"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":32}}

{"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":31}}

{"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":31}}

{"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":31}}

{"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":30}}

{"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":30}}

{"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":30}}

{"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":29}}

{"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":29}}

{"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":29}}

### Exercise 4.4: Cost guard implementation

[Explain your approach]

Mỗi user có ngân sách **$10/tháng** cho LLM API. Chi phí được lưu trong **Redis** (không dùng in-memory) để nhiều instance app cùng đọc/ghi một nguồn dữ liệu.

## Part 5: Scaling & Reliability

### Exercise 5.1: Health checks

**Implementation** (`05-scaling-reliability/develop/app.py`):

- `GET /health` — **Liveness probe**: trả `200` với `status`, `uptime_seconds`, `version`, memory check
- `GET /ready` — **Readiness probe**: trả `503` khi `_is_ready=False` (đang startup/shutdown), ngược lại `200`

**Phân biệt:**


| Endpoint  | Mục đích               | Ai gọi                              |
| --------- | ---------------------- | ----------------------------------- |
| `/health` | Process còn sống?      | Platform restart container nếu fail |
| `/ready`  | Sẵn sàng nhận traffic? | Load balancer ngừng route nếu `503` |


**Test results:**

```json
{"status":"ok","uptime_seconds":4.5,"version":"1.0.0","environment":"development","checks":{"memory":{"status":"ok","used_percent":76.5}}}
{"ready":true,"in_flight_requests":0}
```

### Exercise 5.2: Graceful shutdown

**Implementation:**

- `lifespan()` shutdown: set `_is_ready=False` → chờ `_in_flight_requests == 0` (tối đa 30s)
- Middleware `track_requests` đếm request đang xử lý
- `signal.signal(SIGTERM/SIGINT, handle_sigterm)` — uvicorn tự trigger lifespan shutdown
- `timeout_graceful_shutdown=30` khi chạy uvicorn

**Flow:**

```
SIGTERM → _is_ready=False (/ready trả 503, từ chối traffic mới)
        → chờ in-flight requests hoàn thành
        → exit sạch
```

**Test:** Gửi request đang xử lý → `kill -SIGTERM <pid>` → request vẫn trả `200`, log hiện `Graceful shutdown initiated...` → `Shutdown complete`.

### Exercise 5.3: Stateless design

**Anti-pattern:** `conversation_history = {}` trong memory — scale 2+ instances → session mất khi request vào instance khác.

**Correct** (`05-scaling-reliability/production/app.py`):

- Session lưu Redis: key `session:{session_id}`, TTL 1 giờ
- `append_to_history()` / `load_session()` — mọi instance đọc/ghi cùng Redis
- Fallback in-memory chỉ khi Redis không có (dev local, không scalable)

```python
# Redis-backed
history = load_session(session_id).get("history", [])
save_session(session_id, {"history": history})
```

### Exercise 5.4: Load balancing

**Kết quả:**

```
production-agent-1   Up (healthy)
production-agent-2   Up (healthy)
production-agent-3   Up (healthy)
production-nginx-1   0.0.0.0:8080->80/tcp
production-redis-1   Up (healthy)
```

```bash
curl http://localhost:8080/health
```

```json
{"status":"ok","instance_id":"instance-aabbf8","storage":"redis","redis_connected":true}
```

Nginx round-robin phân tán request; `proxy_next_upstream` chuyển traffic nếu 1 instance die.

### Exercise 5.5: Test stateless

**Kết quả:**

```
Session ID: 4ec33178-9c66-4b05-8064-86d48e76d2a4

Request 1: [instance-0a5ae8]
Request 2: [instance-aabbf8]
Request 3: [instance-a2a9f2]
Request 4: [instance-0a5ae8]
Request 5: [instance-aabbf8]

Instances used: {instance-0a5ae8, instance-aabbf8, instance-a2a9f2}
✅ All requests served despite different instances!

Total messages: 10
✅ Session history preserved across all instances via Redis!
```

**Kết luận:** Dù 5 request được phục vụ bởi 3 instance khác nhau, conversation history vẫn liên tục nhờ state lưu trong Redis — chứng minh stateless design hoạt động đúng khi scale ngang.

```

---

### 2. Full Source Code - Lab 06 Complete (60 points)

Your final production-ready agent with all files:

```

your-repo/
├── app/
│   ├── main.py              # Main application
│   ├── config.py            # Configuration
│   ├── auth.py              # Authentication
│   ├── rate_limiter.py      # Rate limiting
│   └── cost_guard.py        # Cost protection
├── utils/
│   └── mock_llm.py          # Mock LLM (provided)
├── Dockerfile               # Multi-stage build
├── docker-compose.yml       # Full stack
├── requirements.txt         # Dependencies
├── .env.example             # Environment template
├── .dockerignore            # Docker ignore
├── railway.toml             # Railway config (or render.yaml)
└── README.md                # Setup instructions

```

**Requirements:**

- All code runs without errors
- Multi-stage Dockerfile (image < 500 MB)
- API key authentication
- Rate limiting (10 req/min)
- Cost guard ($10/month)
- Health + readiness checks
- Graceful shutdown
- Stateless design (Redis)
- No hardcoded secrets

---

### 3. Service Domain Link

Create a file `DEPLOYMENT.md` with your deployed service information:

```markdown
# Deployment Information

## Public URL
https://day12-production-8379.up.railway.app

## Platform
Railway 

## Test Commands

### Health Check
```bash
curl https://your-agent.railway.app/health
# Expected: {"status": "ok"}
```

### API Test (with authentication)

```bash
curl -X POST https://your-agent.railway.app/ask \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test", "question": "Hello"}'
```

## Environment Variables Set

- PORT
- REDIS_URL
- AGENT_API_KEY
- LOG_LEVEL

## Screenshots

- [Deployment dashboard](screenshots/dashboard.png)
- [Service running](screenshots/running.png)
- [Test results](screenshots/test.png)

```

##  Pre-Submission Checklist

- [ ] Repository is public (or instructor has access)
- [ ] `MISSION_ANSWERS.md` completed with all exercises
- [ ] `DEPLOYMENT.md` has working public URL
- [ ] All source code in `app/` directory
- [ ] `README.md` has clear setup instructions
- [ ] No `.env` file committed (only `.env.example`)
- [ ] No hardcoded secrets in code
- [ ] Public URL is accessible and working
- [ ] Screenshots included in `screenshots/` folder
- [ ] Repository has clear commit history

---

##  Self-Test

Before submitting, verify your deployment:

```bash
# 1. Health check
curl https://your-app.railway.app/health

# 2. Authentication required
curl https://your-app.railway.app/ask
# Should return 401

# 3. With API key works
curl -H "X-API-Key: YOUR_KEY" https://your-app.railway.app/ask \
  -X POST -d '{"user_id":"test","question":"Hello"}'
# Should return 200

# 4. Rate limiting
for i in {1..15}; do 
  curl -H "X-API-Key: YOUR_KEY" https://your-app.railway.app/ask \
    -X POST -d '{"user_id":"test","question":"test"}'; 
done
# Should eventually return 429
```

---

