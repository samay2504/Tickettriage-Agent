# System Architecture & Flow

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         API Client                                  │
│                    (curl/Postman/SDK)                              │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      FastAPI Application                           │
│ ┌────────────────────────────────────────────────────────────────┐ │
│ │ POST /triage                                                  │ │
│ │ GET /health                                                   │ │
│ │ POST /cache/purge (admin)                                     │ │
│ └────────────────────────────────────────────────────────────────┘ │
└────────────────────────┬───────────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │ Orchestrator │ │  Logger      │ │  Schemas     │
    │ (Main Logic) │ │  (JSON)      │ │  (Validation)│
    └──────────────┘ └──────────────┘ └──────────────┘
        │
        ├─────────────────────────┬─────────────────────────┐
        │                         │                         │
        ▼                         ▼                         ▼
    ┌──────────────┐         ┌──────────────┐         ┌──────────────┐
    │ KB Search    │         │ LLM Client   │         │ Redis Cache  │
    │ (Keywords +  │         │ (Multi-      │         │              │
    │  Embeddings) │         │   Provider)  │         └──────────────┘
    └──────────────┘         └──────────────┘
        │                         │
        ▼                         ▼
    ┌──────────────┐         ┌──────────────┐
    │ sample_kb.   │         │ llm_provider.│
    │ json         │         │ py           │
    │ (15 entries) │         │              │
    └──────────────┘         └──────────────┘
```

## Request Flow Diagram

```
1. Client sends POST /triage with description
                    │
                    ▼
2. Validation Layer
   - Check min/max length
   - UTF-8 validation
                    │
                    ▼
3. Check Cache
   - Compute SHA256(normalized_description)
   - Try Redis get
   - If hit → Return cached response (fast path)
                    │ (cache miss)
                    ▼
4. KB Search
   - Query search engine with description
   - Get top-K matches with scores
   - Format matches for prompt
                    │
                    ▼
5. Load Prompt Template
   - Read from prompts/triage_prompt.txt
   - Inject variables:
     * {description}
     * {kb_matches}
     * {config_summary}
                    │
                    ▼
6. Call LLM Provider
   ┌─────────────────────────────────────┐
   │ Try Provider 1 (Google Gemini)      │
   ├─────────────────────────────────────┤
   │ If fails → Try Provider 2 (Groq)    │
   ├─────────────────────────────────────┤
   │ If fails → Try Provider 3 (OpenAI)  │
   ├─────────────────────────────────────┤
   │ If fails → Try Provider 4 (HF)      │
   ├─────────────────────────────────────┤
   │ If all fail → Use Fallback LLM      │
   └─────────────────────────────────────┘
                    │
                    ▼
7. Parse LLM Response
   - Extract JSON from response
   - Validate fields (category, severity)
   - Normalize to valid values
                    │
                    ▼
8. Enrich Response
   - Add KB match details
   - Extract KB IDs from LLM response
   - Filter KB matches
                    │
                    ▼
9. Cache Response
   - Serialize to JSON
   - Store in Redis with TTL
   - Include metadata (provider, timestamp)
                    │
                    ▼
10. Return Response
   - HTTP 200
   - JSON with all fields
   - Meta information
```

## Component Interactions

### 1. Orchestrator & KB Search
```
Orchestrator
    │
    └─► KB Search.search(description, top_k=3)
            │
            ├─► Try embedding-based search
            │   └─► If LangChain available
            │
            └─► Fall back to keyword search
                ├─► Tokenize query
                ├─► Tokenize each KB entry
                ├─► Compute BM25-like score
                ├─► Sort by score
                └─► Return top_k results
```

### 2. Orchestrator & LLM Client
```
Orchestrator
    │
    └─► LLM Client.invoke(prompt)
            │
            └─► Retry with backoff
                ├─► Attempt 1 (immediate)
                ├─► Attempt 2 (2s delay)
                ├─► Attempt 3 (4s delay)
                │
                └─► If all fail → LLM Provider.invoke() → Fallback
```

### 3. LLM Provider Chain (from llm_provider.py)
```
create_llm_provider(config)
    │
    ├─► Try Google Gemini
    │   ├─► Test connection
    │   ├─► Try multiple models
    │   └─► On quota error → Skip to next
    │
    ├─► Try Groq
    │   ├─► Validate API key
    │   ├─► Try multiple models
    │   └─► On error → Continue
    │
    ├─► Try OpenAI
    │   ├─► Validate credentials
    │   └─► Try multiple models
    │
    ├─► Try HuggingFace
    │   └─► Validate token
    │
    └─► Fallback
        └─► Return deterministic response
```

### 4. Caching System
```
Client Request
    │
    ├─► Cache.compute_key(description)
    │   └─► SHA256(normalize(description))
    │
    ├─► Redis.get(cache_key)
    │   ├─► If found → Return cached response
    │   └─► If not → Proceed to triage
    │
    └─► After triage
        └─► Redis.set(cache_key, response, ttl=3600)
            └─► Response stored with timestamp
```

## Data Flow Example

### Request
```json
{
  "description": "Users cannot log in with their credentials on mobile"
}
```

### Processing Steps

**Step 1: Validation**
```json
{
  "normalized": "users cannot log in with their credentials on mobile",
  "length": 58,
  "valid": true
}
```

**Step 2: Cache Key**
```
cache_key = "triage:v1:a1b2c3d4e5f6..."
```

**Step 3: KB Search Results**
```json
[
  {
    "id": "ISSUE-102",
    "title": "Password reset email not received",
    "score": 0.87
  },
  {
    "id": "ISSUE-106",
    "title": "Two-factor authentication not working",
    "score": 0.72
  }
]
```

**Step 4: Prompt Sent to LLM**
```
You are a Support Triage assistant...
Input: users cannot log in with their credentials on mobile
KB matches:
- [ISSUE-102] Password reset email not received (0.87)
- [ISSUE-106] Two-factor authentication not working (0.72)
Configuration: temperature=0.1, top_k=3
...
```

**Step 5: LLM Response**
```json
{
  "summary": "Mobile login failure - possible credential or authentication issue",
  "category": "Login",
  "severity": "High",
  "known_issue": true,
  "kb_ids": ["ISSUE-102"],
  "suggested_action": "Check email delivery provider logs; verify email service configuration"
}
```

**Step 6: Final Response**
```json
{
  "summary": "Mobile login failure - possible credential or authentication issue",
  "category": "Login",
  "severity": "High",
  "kb_matches": [
    {
      "id": "ISSUE-102",
      "title": "Password reset email not received",
      "snippet": "Users report not receiving password reset emails.",
      "score": 0.87
    }
  ],
  "known_issue": true,
  "suggested_action": "Check email delivery provider logs; verify email service configuration",
  "meta": {
    "provider": "google_genai_gemini-1.5-flash",
    "latency_ms": 342,
    "cache_hit": false,
    "fallback_mode": false
  }
}
```

## Error Handling Paths

### Path 1: LLM Provider Fails
```
Request
  │
  └─► Try Provider 1 ─ Fail
       └─► Try Provider 2 ─ Fail
            └─► Try Provider 3 ─ Fail
                 └─► Try Provider 4 ─ Fail
                      └─► Use Fallback LLM
                           └─► Return rule-based response
```

### Path 2: Invalid LLM Response
```
LLM Response (invalid JSON)
  │
  └─► Parse Error
       └─► Log error with raw response
            └─► Use fallback classification
                 └─► Return partial response
```

### Path 3: Redis Unavailable
```
Request
  │
  ├─► Redis.get() ─ Fail
  │    └─► Continue without cache
  │
  └─► After triage
       └─► Redis.set() ─ Fail
            └─► Log warning
                 └─► Continue (cache disabled for request)
```

## Configuration Example

**.env file:**
```bash
# API
API_HOST=0.0.0.0
API_PORT=8000

# LLM
LLM_TEMPERATURE=0.1
PROVIDER_PREFERENCE=google_genai,groq,openai,fallback

# API Keys
GOOGLE_API_KEY=sk-xxx...
GROQ_API_KEY=gsk-xxx...
OPENAI_API_KEY=sk-xxx...

# Redis
REDIS_URL=redis://localhost:6379/0
CACHE_TTL_SECONDS=3600

# Admin
ADMIN_TOKEN=secure-token-123
```

## Performance Characteristics

### Latency Distribution

```
Cache Hit:           ~100-200ms    (fast)
KB Search Only:      ~50-100ms
LLM Call:            ~1-3s         (network dependent)
Full Triage:         ~1.5-3.5s
P99:                 ~5s
```

### Memory Usage

```
Base Application:    ~150MB
KB + Embeddings:     ~50MB
Redis (optional):    ~100-500MB (configurable)
Per Request:         ~1-5MB
```

### Throughput

```
Without cache:       ~5-20 req/s (LLM limited)
With cache:          >100 req/s (cache hits)
Cache hit rate:      70-90% typical
Concurrent requests: 10-50 (configurable)
```

## Deployment Topology

### Development
```
Client
  │
  └─► FastAPI (uvicorn)
       ├─► Redis (optional, localhost:6379)
       ├─► LLM Providers (cloud APIs)
       └─► KB + Prompts (local files)
```

### Production
```
Load Balancer (Nginx)
  │
  ├─► App Instance 1
  ├─► App Instance 2
  ├─► App Instance 3
  │
  ├─► Redis Cluster (3+ nodes)
  └─► Log Aggregation (ELK/Datadog)
```

### Kubernetes
```
Load Balancer Service
  │
  ├─► Deployment (ticket-triage)
  │   ├─► Pod 1
  │   ├─► Pod 2
  │   └─► Pod 3
  │
  └─► Redis StatefulSet (3 nodes)
```

---

This architecture ensures:
- ✅ High availability through multiple LLM providers
- ✅ Fast responses with intelligent caching
- ✅ Graceful degradation on failures
- ✅ Easy scaling horizontally
- ✅ Comprehensive observability
- ✅ Production-ready security
