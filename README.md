# Support Ticket Triage Agent

An intelligent support ticket classification and routing system that uses LLM and knowledge base matching to automatically triage support tickets. The system classifies tickets, determines severity, matches against known issues, and recommends next actions for the support team.

## Features

- **Intelligent Classification**: Automatically categorizes tickets as Bug, Billing, Login, Performance, Question, or Other
- **Severity Assessment**: Determines ticket severity (Low, Medium, High, Critical)
- **Knowledge Base Matching**: Semantic and keyword search against known issues
- **LLM Integration**: Multi-provider support (Google Gemini, Groq, OpenAI, HuggingFace) with automatic fallbacks
- **Caching**: Redis-backed caching for high-volume scenarios
- **Extensible Prompts**: Edit prompts on disk without code changes
- **Production Ready**: Structured logging, error handling, Docker support, comprehensive tests
- **Cross-Platform**: Works on Windows, Linux, macOS

## Quick Start

### Prerequisites

- Python 3.11+
- Redis (optional, for caching)
- Docker (optional, for containerized deployment)

### Local Development - Easiest Method

**Windows**: Just double-click `run-server.bat` in the project folder!

**Mac/Linux**:
```bash
bash run-server.sh
```

**Python** (All platforms):
```bash
python start_server.py
```

**Using Make** (if installed):
```bash
make server
```

### Manual Setup

1. **Clone and setup**:
   ```bash
   cd ticket-triage-agent
   cp .env.example .env
   # Edit .env with your API keys
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the app**:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

4. **Access the app**:
   - Web UI: http://localhost:8000/ui
   - API Docs: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health

5. **Test the API**:
   ```bash
   curl -X POST http://localhost:8000/triage \
     -H "Content-Type: application/json" \
     -d '{"description": "Users cannot log in with their credentials"}'
   ```

### Docker Deployment

1. **Using Docker Compose** (recommended):
   ```bash
   docker-compose -f docker/docker-compose.yml up
   ```

2. **Or build and run manually**:
   ```bash
   docker build -f docker/Dockerfile -t ticket-triage:latest .
   docker run -p 8000:8000 -e REDIS_URL=redis://host.docker.internal:6379/0 ticket-triage:latest
   ```

3. **Access the app**:
   - Web UI: http://localhost:8000/ui
   - API Docs: http://localhost:8000/docs

## Web User Interface

The system includes a modern, responsive web UI for ticket triage.

**Access**: http://localhost:8000/ui

**Features**:
- Clean, intuitive interface with glassmorphism design
- Real-time ticket classification
- Severity assessment display
- Related KB matches
- JSON response viewer
- Responsive design (works on desktop, tablet, mobile)

## Server Startup Options

For convenience, multiple startup methods are available:

| Method | Command | Platform |
|--------|---------|----------|
| **Easiest** | Double-click `run-server.bat` | Windows |
| **PowerShell** | `.\run-server.ps1` | Windows |
| **Python** | `python start_server.py` | All |
| **Bash** | `bash run-server.sh` | Mac/Linux |
| **Make** | `make server` | All |
| **Manual** | `uvicorn app.main:app --reload` | All |

All methods start the server at **http://localhost:8000**

## API Endpoints

### `POST /triage`

Triage a support ticket.

**Request**:
```json
{
  "description": "Users report 500 errors when completing purchase on mobile"
}
```

**Response**:
```json
{
  "summary": "Mobile checkout experiencing 500 errors",
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

### `GET /health`

Health check endpoint.

```bash
curl http://localhost:8000/health
```

**Response**:
```json
{
  "status": "healthy",
  "redis": "connected",
  "llm_provider": "google_genai_gemini-1.5-flash",
  "llm_available": true
}
```

### `POST /cache/purge`

Purge cache (admin only).

**Request**:
```json
{
  "key": "triage:v1:abc123def456",
  "token": "your-admin-token"
}
```

To purge all cache:
```json
{
  "token": "your-admin-token"
}
```

## Configuration

All configuration is externalized via environment variables. See `.env.example` for all available options.

### Key Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `API_HOST` | `0.0.0.0` | API host address |
| `API_PORT` | `8000` | API port |
| `LLM_TEMPERATURE` | `0.1` | LLM temperature (0-1) |
| `PROVIDER_PREFERENCE` | `google_genai,groq,huggingface,openai,fallback` | LLM provider priority |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `CACHE_TTL_SECONDS` | `3600` | Cache TTL in seconds |
| `KB_PATH` | `kb/sample_kb.json` | Knowledge base file path |
| `ADMIN_TOKEN` | - | Admin token for cache purge |
| `LOG_LEVEL` | `INFO` | Logging level |
| `SENTRY_DSN` | - | Sentry error tracking URL (optional) |

### API Keys

Set these environment variables for LLM providers:

- `OPENAI_API_KEY` - OpenAI API key
- `GOOGLE_API_KEY` - Google Gemini API key
- `GROQ_API_KEY` - Groq API key
- `HUGGINGFACE_API_KEY` - HuggingFace API key

The system will automatically try providers in the order specified by `PROVIDER_PREFERENCE` and fall back to the next available provider.

## Editing Prompt Templates

Prompts are stored on disk and loaded at runtime. This allows developers to edit prompts without changing code.

**Default location**: `prompts/triage_prompt.txt`

The template supports these variables:
- `{description}` - The ticket description
- `{kb_matches}` - Formatted KB matches
- `{config_summary}` - Configuration summary

**Example**: To adjust the prompt:
1. Open `prompts/triage_prompt.txt`
2. Edit the prompt text and variables
3. Restart the service
4. The new prompt takes effect immediately

## Knowledge Base

KB entries are stored in JSON format at `kb/sample_kb.json`.

**Entry schema**:
```json
{
  "id": "ISSUE-001",
  "title": "Issue title",
  "category": "Bug|Billing|Login|Performance|Question|Other",
  "symptoms": ["keyword1", "keyword2"],
  "snippet": "Short description",
  "full_text": "Detailed description",
  "recommended_action": "Suggested action for support team"
}
```

**Adding new entries**:
1. Edit `kb/sample_kb.json`
2. Add a new entry object
3. Save the file
4. Restart the service or call the triage endpoint (it will reload)

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=app --cov=agent --cov=kb --cov=cache --cov-report=html

# Run specific test file
pytest tests/test_kb_search.py -v

# Run tests matching pattern
pytest tests/ -k "test_cache" -v
```

### Test Coverage

Current coverage target: >80%

Tested components:
- KB search and matching (keyword + embeddings)
- Triage orchestration and LLM integration
- Cache behavior and Redis integration
- Error handling and fallbacks
- Input validation and edge cases
- Prompt loading and formatting

## Running Linting and Formatting

```bash
# Check formatting
black --check .

# Format code
black .

# Lint
ruff check .

# Type check
mypy app agent kb cache config

# Or use Make
make lint
make format
```

## Production Considerations

See [PRODUCTION_CONSIDERATIONS.md](PRODUCTION_CONSIDERATIONS.md) for detailed deployment guidance.

### Key Points

1. **Secrets Management**:
   - Use environment variables from secrets manager (AWS Secrets Manager, HashiCorp Vault, etc.)
   - Never commit `.env` files
   - Rotate API keys regularly

2. **Scaling**:
   - Deploy behind load balancer (Nginx, HAProxy)
   - Use Redis cluster for high-volume caching
   - Monitor LLM provider rate limits and costs
   - Consider request queuing for burst traffic

3. **Monitoring**:
   - Enable structured JSON logging
   - Integrate with Sentry for error tracking
   - Set up Prometheus metrics for monitoring
   - Monitor cache hit rates and latency

4. **High Availability**:
   - Run multiple app instances
   - Use managed Redis (AWS ElastiCache, Azure Cache)
   - Set up database backup and recovery
   - Implement circuit breakers for external services

5. **Security**:
   - Use HTTPS/TLS in production
   - Implement rate limiting
   - Protect admin endpoints with authentication
   - Validate and sanitize all inputs
   - Run container with read-only filesystem

## Architecture

```
ticket-triage/
├── app/                          # FastAPI application
│   ├── main.py                  # App initialization & startup
│   ├── routes/
│   │   └── triage.py            # HTTP endpoints
│   └── schemas.py               # Request/response models
├── agent/                        # Core orchestration & LLM integration
│   ├── orchestrator.py          # Main triage logic
│   ├── llm_client.py            # LLM provider wrapper with retries
│   ├── llm_provider.py          # Multi-provider LLM system (Google, Groq, OpenAI, HF)
│   └── prompt_loader.py         # YAML/text prompt template loading
├── kb/                           # Knowledge base
│   ├── kb_loader.py             # KB file loading
│   ├── search.py                # KB search (keyword + semantic)
│   └── sample_kb.json           # Sample KB entries
├── cache/                        # Caching layer
│   └── redis_client.py          # Redis integration (optional)
├── config/                       # Configuration
│   └── settings.py              # Settings & env vars
├── prompts/                      # Prompt templates
│   ├── triage_prompt.yaml       # Production YAML config (NEW)
│   └── triage_prompt.txt        # Text template (fallback)
├── tests/                        # Test suite
│   ├── test_prompt_loader.py
│   ├── test_production_edge_cases.py
│   ├── test_edge_cases.py
│   ├── test_cache.py
│   └── test_fallback.py
├── docker/                       # Docker configuration
│   ├── Dockerfile
│   └── docker-compose.yml
├── docs/                         # Documentation
│   └── YAML_PROMPT_SYSTEM.md    # Detailed YAML prompt system guide
├── Makefile                      # Build & run targets
├── README.md                     # This file
└── requirements.txt              # Python dependencies
```

## Error Handling & Fallbacks

The system implements comprehensive error handling:

1. **LLM Failures**: Automatic retry with exponential backoff, fallback to next provider
2. **Cache Failures**: Gracefully disable caching if Redis unavailable
3. **KB Search Failures**: Fall back from embeddings to keyword search
4. **JSON Parse Errors**: Use rule-based classification as fallback
5. **Validation Errors**: Return 400 with detailed error messages

## Logging

All events are logged with:
- Request ID for tracing
- Timestamp and severity
- Component and operation name
- Latency and provider info
- Error details and stack traces

Logs are output to stdout in JSON format for easy ingestion by log aggregation systems.

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make changes and add tests
4. Run linting and tests: `make lint test`
5. Commit with clear messages
6. Submit a pull request

## License

This project is open source and available under the MIT License.

## Support

For issues and questions:
1. Check [PRODUCTION_CONSIDERATIONS.md](PRODUCTION_CONSIDERATIONS.md)
2. Review test files for usage examples
3. Check logs for error details
4. Open an issue with detailed reproduction steps
