# Groq Integration - Quick Reference Card

## Setup (1 minute)

```bash
# 1. Get API key from console.groq.com
# 2. Set environment variable
export GROQ_API_KEY="your-api-key"
```

## Three Ways to Use

### Method 1: Simple Utility (Recommended)
```python
from utils.error_analyzer import analyze_error

result = analyze_error("Your error message")
# Returns: {explanation, cause, fix}
```

### Method 2: Safe Utility (Never Fails)
```python
from utils.error_analyzer import get_error_analysis_safe

result = get_error_analysis_safe("Error")
# Always returns valid dict, handles all errors
```

### Method 3: REST API
```bash
curl -X POST http://localhost:5000/api/errors/analyze \
  -H "Content-Type: application/json" \
  -d '{"message":"error text"}'
```

## Response Format

```json
{
  "explanation": "What went wrong (1-2 sentences)",
  "cause": "Root cause (1-2 sentences)",
  "fix": "How to fix it (1-2 sentences)"
}
```

## Common Integrations

### In Exception Handlers
```python
try:
    # code
except Exception as e:
    from utils.error_analyzer import analyze_error
    result = analyze_error(str(e))
    logger.error(f"Cause: {result['cause']}")
```

### In Flask Routes
```python
@app.route("/api/endpoint")
def endpoint():
    try:
        # code
    except Exception as e:
        from utils.error_analyzer import get_error_analysis_safe
        analysis = get_error_analysis_safe(str(e))
        return jsonify({"error": str(e), **analysis}), 500
```

### In Test Handling
```python
def handle_test_failure(error):
    from utils.error_analyzer import analyze_error
    analysis = analyze_error(error)
    print(f"Fix: {analysis['fix']}")
```

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/errors/analyze` | POST | Analyze single error |
| `/api/errors/batch` | POST | Analyze multiple errors |
| `/api/errors/health` | GET | Check service status |

## Batch Analysis
```python
errors = ["Error 1", "Error 2", "Error 3"]
for error in errors:
    result = analyze_error(error)
    print(result['fix'])
```

## Health Check
```bash
curl http://localhost:5000/api/errors/health
# Returns: {status, service, model}
```

## Error Cases

| Problem | Solution |
|---------|----------|
| "GROQ_API_KEY not set" | Set env var with API key |
| Connection timeout | Check internet/API key |
| Partial response | Check token/rate limits |

## Files Created

- `services/groq_ai_service.py` - Core service
- `utils/error_analyzer.py` - Utility wrapper
- `routes/error_analysis.py` - REST endpoints
- `GROQ_SETUP.md` - Full documentation
- `GROQ_EXAMPLES.py` - 10 code examples

## Configuration

```python
# Automatic in config.py
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# Service uses:
model = "llama3-8b-8192"
temperature = 0.3
max_tokens = 500
```

## Performance

- **Response time**: 1-2 seconds
- **Token cost**: ~250 tokens per analysis
- **Rate limits**: Check Groq console

## One-Liner Examples

```python
# Analyze error in one line
from utils.error_analyzer import analyze_error; print(analyze_error("error")['fix'])

# Safe one-liner
from utils.error_analyzer import get_error_analysis_safe; print(get_error_analysis_safe("error")['explanation'])
```

## Documentation

- `GROQ_SETUP.md` - Complete setup & usage guide
- `GROQ_EXAMPLES.py` - 10 working examples
- `GROQ_INTEGRATION.txt` - Full reference
- This file - Quick reference

## Next Steps

1. Set `GROQ_API_KEY` environment variable
2. Import and use in your code
3. Or call REST API endpoints
4. Check logs if issues

That's it! You now have AI-powered error analysis.
