# Quick Start Guide

## File Structure

```
ticket-triage-agent/
├── app/                                    # FastAPI application
│   ├── __init__.py
│   ├── main.py                            # App initialization & startup
│   ├── schemas.py                         # Request/response models
│   └── routes/
│       ├── __init__.py
│       └── triage.py                      # HTTP endpoints
├── agent/                                  # Core orchestration
│   ├── __init__.py
│   ├── orchestrator.py                    # Main triage logic (KB + LLM)
│   ├── llm_client.py                      # LLM provider wrapper with retries
│   └── prompt_loader.py                   # Load prompts from disk
├── kb/                                     # Knowledge base
│   ├── __init__.py
│   ├── kb_loader.py                       # Load KB JSON
│   ├── search.py                          # Semantic/keyword search
│   └── sample_kb.json                     # 15 sample KB entries
├── cache/                                  # Caching layer
│   ├── __init__.py
│   └── redis_client.py                    # Redis connection + helpers
├── config/                                 # Configuration
│   ├── __init__.py
│   └── settings.py                        # Settings from .env / config
├── prompts/                                # Editable prompt templates
│   └── triage_prompt.txt                  # Edit this to change prompt
├── tests/                                  # Comprehensive test suite
│   ├── __init__.py
│   ├── conftest.py                        # Pytest fixtures
│   ├── test_kb_search.py                  # KB search tests
│   ├── test_edge_cases.py                 # Validation & error handling
│   ├── test_cache.py                      # Cache tests
│   ├── test_fallback.py                   # Fallback behavior tests
│   └── test_prompt_loader.py              # Prompt loading tests
├── docker/                                 # Docker configuration
│   ├── Dockerfile                         # Multi-stage Docker build
│   ├── docker-compose.yml                 # Docker Compose setup
│   └── .dockerignore                      # Docker build exclusions
├── .github/workflows/                     # CI/CD pipeline
│   └── ci.yml                             # GitHub Actions workflow
├── llm_provider.py                        # Provided LLM provider system
├── .env.example                           # Environment variables template
├── .gitignore                             # Git exclusions
├── .pre-commit-config.yaml                # Pre-commit hooks
├── pyproject.toml                         # Python project config
├── requirements.txt                       # Python dependencies
├── Makefile                               # Build & run targets
├── README.md                              # Main documentation
└── PRODUCTION_CONSIDERATIONS.md           # Production deployment guide
```

## Setup Instructions

### 1. Initial Setup

```bash
# Clone repository
cd ticket-triage-agent

# Copy environment template
cp .env.example .env

# Edit .env with your API keys
# (At minimum, set at least one of: GOOGLE_API_KEY, GROQ_API_KEY, OPENAI_API_KEY)
```

### 2. Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install black ruff mypy pytest pytest-cov pytest-mock
```

### 3. Run Locally

```bash
# Development mode with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or use make command
make run
```

### 4. Test the API

```bash
# Health check
curl http://localhost:8000/health

# Triage a ticket
curl -X POST http://localhost:8000/triage \
  -H "Content-Type: application/json" \
  -d '{"description": "Users report 500 errors on checkout page when using mobile devices"}'

# Purge cache (requires admin token)
curl -X POST http://localhost:8000/cache/purge \
  -H "Content-Type: application/json" \
  -d '{"token": "your-admin-token"}'
```

### 5. Run Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov=agent --cov=kb --cov=cache --cov-report=html

# Run specific test file
pytest tests/test_kb_search.py -v

# Or use make
make test
make test-cov
```

### 6. Linting & Formatting

```bash
# Check formatting
black --check .

# Format code
black .

# Lint
ruff check .

# Type checking
mypy app agent kb cache config

# Or use make
make lint
make format
```

## Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose -f docker/docker-compose.yml up

# Or build manually
docker build -f docker/Dockerfile -t ticket-triage:latest .
docker run -p 8000:8000 ticket-triage:latest
```

## Customization

### Edit Prompt Template

The prompt template is loaded from disk at runtime. To customize:

1. Open `prompts/triage_prompt.txt`
2. Edit the prompt text
3. Restart the service
4. Changes take effect immediately - no code changes needed!

### Add KB Entries

Edit `kb/sample_kb.json` to add new knowledge base entries:

```json
{
  "id": "CUSTOM-001",
  "title": "Your custom issue title",
  "category": "Bug",
  "symptoms": ["keyword1", "keyword2"],
  "snippet": "Short description",
  "full_text": "Full description",
  "recommended_action": "Suggested action"
}
```

### Configure LLM Providers

Edit `.env` to set provider preference:

```bash
# Try Groq first (free), then Google, then OpenAI
PROVIDER_PREFERENCE=groq,google_genai,openai,fallback
```

## Key Features

✅ **Multi-provider LLM support** with automatic fallbacks  
✅ **Redis caching** for high-volume scenarios  
✅ **Editable prompt templates** (no code changes needed)  
✅ **Semantic & keyword search** on knowledge base  
✅ **Comprehensive error handling** & fallback logic  
✅ **Production-ready** with logging, metrics, Docker  
✅ **>80% test coverage** with comprehensive tests  
✅ **Cross-platform** (Windows, Linux, macOS)  

## Example Response

```json
{
  "summary": "Mobile checkout experiencing intermittent 500 errors during payment processing",
  "category": "Bug",
  "severity": "High",
  "kb_matches": [
    {
      "id": "ISSUE-101",
      "title": "Checkout error 500 on mobile",
      "snippet": "Users report 500 errors when completing purchase on mobile devices.",
      "score": 0.95
    }
  ],
  "known_issue": true,
  "suggested_action": "Escalate to payments team; reference incident INC-2023-09-10",
  "meta": {
    "provider": "google_genai_gemini-1.5-flash",
    "latency_ms": 245,
    "cache_hit": false,
    "fallback_mode": false
  }
}
```

## Troubleshooting

### No LLM providers available
- Check you have at least one API key set (GOOGLE_API_KEY, GROQ_API_KEY, OPENAI_API_KEY)
- Check API key is valid and not expired
- Check network connectivity
- System will fall back to rule-based classification

### Redis connection fails
- Redis is optional - caching will be disabled gracefully
- To use Redis, start a local Redis: `redis-server`
- Or use Docker: `docker run -d -p 6379:6379 redis:latest`

### Tests failing
- Ensure pytest is installed: `pip install pytest pytest-cov pytest-mock`
- Check Python version: requires 3.11+
- Run with verbose output: `pytest tests/ -v -s`

## Production Deployment

See [PRODUCTION_CONSIDERATIONS.md](PRODUCTION_CONSIDERATIONS.md) for:
- Kubernetes/Docker orchestration
- Monitoring & observability
- Security best practices
- Scaling strategies
- Cost optimization
- Disaster recovery

## Support

- Check README.md for API documentation
- Review test files for usage examples
- See PRODUCTION_CONSIDERATIONS.md for deployment guidance
- Check logs for error details (JSON format)
