# Groq API Integration

This project uses **Groq's Mixtral-8x7b LLM** for intelligent error analysis through the **llama3-8b-8192** model.

## Setup

### 1. Get API Key

1. Visit [console.groq.com](https://console.groq.com)
2. Sign up or log in
3. Navigate to API Keys section
4. Create a new API key

### 2. Set Environment Variable

```bash
export GROQ_API_KEY="your-api-key-here"
```

Or add to `.env` file:
```
GROQ_API_KEY=your-api-key-here
```

The application will automatically load from `.env` via `python-dotenv`.

## Usage

### Option 1: Direct Service Class

```python
from services.groq_ai_service import GroqAIService

service = GroqAIService()
result = service.analyzeError("TypeError: Cannot read property 'x' of undefined")

print(result['explanation'])  # What went wrong
print(result['cause'])         # Root cause
print(result['fix'])           # How to fix
```

### Option 2: Utility Function (Recommended)

```python
from utils.error_analyzer import analyze_error

result = analyze_error("Your error message here")
print(result['explanation'])
print(result['cause'])
print(result['fix'])
```

Safe version with fallback:

```python
from utils.error_analyzer import get_error_analysis_safe

result = get_error_analysis_safe("Error message")
# Never throws exceptions, returns fallback if service unavailable
```

### Option 3: REST API

**Endpoint:** `POST /api/errors/analyze`

**Request:**
```json
{
  "message": "Error message or traceback to analyze"
}
```

**Response:**
```json
{
  "explanation": "What went wrong (technical)",
  "cause": "Root cause of the error",
  "fix": "Practical steps to resolve it"
}
```

**Example:**
```bash
curl -X POST http://localhost:5000/api/errors/analyze \
  -H "Content-Type: application/json" \
  -d '{"message": "ConnectionError: Failed to connect to database"}'
```

### Option 4: Batch Analysis

**Endpoint:** `POST /api/errors/batch`

**Request:**
```json
{
  "errors": [
    "Error 1",
    "Error 2",
    "Error 3"
  ]
}
```

**Response:**
```json
{
  "results": [
    {
      "message": "Error 1",
      "explanation": "...",
      "cause": "...",
      "fix": "..."
    }
  ]
}
```

### Option 5: Health Check

**Endpoint:** `GET /api/errors/health`

**Response (Success):**
```json
{
  "status": "ok",
  "service": "Groq AI",
  "model": "llama3-8b-8192"
}
```

**Response (Error):**
```json
{
  "status": "error",
  "message": "GROQ_API_KEY not configured"
}
```

## Response Format

All methods return a dictionary with three fields:

| Field | Type | Description |
|-------|------|-------------|
| `explanation` | string | Technical explanation of what went wrong (1-2 sentences) |
| `cause` | string | Root cause of the error (1-2 sentences) |
| `fix` | string | Practical steps to fix or prevent the error (1-2 sentences) |

## Error Handling

The integration handles errors gracefully:

- **Missing API Key**: Returns helpful message about setting GROQ_API_KEY
- **API Failures**: Logs error and returns fallback response
- **Invalid Input**: Validates before sending to API
- **JSON Parsing**: Extracts JSON from response even with extra text

All errors are logged to `logging` for debugging.

## Configuration

In `config.py`:
```python
GROQ_API_KEY = _env("GROQ_API_KEY")  # Your API key
```

The model is hardcoded in `GroqAIService`:
```python
self.model = "llama3-8b-8192"
```

Temperature is set to 0.3 for consistent, deterministic responses.

## Performance

- **Response Time**: ~1-2 seconds per error (depends on error complexity)
- **Model**: llama3-8b-8192 (fast, efficient)
- **Tokens**: ~200-300 per analysis
- **Cost**: See Groq pricing (generally very affordable)

## Integration Examples

### In Route Handlers

```python
@app.route("/api/test/run", methods=["POST"])
def run_test():
    try:
        # ... test execution code ...
    except Exception as e:
        from utils.error_analyzer import analyze_error
        analysis = analyze_error(str(e))
        
        return jsonify({
            "success": False,
            "error": str(e),
            "analysis": analysis
        }), 500
```

### In QA Pipeline

```python
def handle_test_failure(error_msg, test_name):
    from utils.error_analyzer import get_error_analysis_safe
    
    analysis = get_error_analysis_safe(error_msg)
    
    # Store analysis result
    db.store_error_analysis(
        test_name=test_name,
        error=error_msg,
        explanation=analysis['explanation'],
        cause=analysis['cause'],
        fix=analysis['fix']
    )
```

### In Exception Handlers

```python
def log_and_analyze_exception(exc: Exception):
    from utils.error_analyzer import analyze_error
    
    error_str = f"{type(exc).__name__}: {str(exc)}"
    analysis = analyze_error(error_str)
    
    logger.error({
        "exception": error_str,
        "analysis": analysis
    })
```

## Troubleshooting

**Q: "GROQ_API_KEY environment variable is required"**
- A: Set the GROQ_API_KEY environment variable with your API key from console.groq.com

**Q: "Connection error" when calling API**
- A: Check internet connection and that API key is valid

**Q: Response is incomplete or truncated**
- A: Service may have max_tokens limit. Check logs for details.

**Q: Getting same response for different errors**
- A: Temperature is low (0.3) for consistency. This is by design.

## API Cost Estimation

- Average error analysis: ~250 tokens
- Groq pricing: See console.groq.com/pricing
- Generally: Very affordable compared to OpenAI/Claude

## Limits & Quotas

Check your Groq account for:
- Rate limits (requests per minute)
- Token limits (per month)
- Concurrent requests

Adjust error handling based on your quota.

## References

- [Groq Console](https://console.groq.com)
- [Groq API Docs](https://console.groq.com/docs)
- [Python SDK](https://github.com/groq/groq-python)
