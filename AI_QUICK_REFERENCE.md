# AutoQA Pro AI - Quick Reference Guide

## Setup (30 seconds)

1. Get API key from [console.groq.com](https://console.groq.com)
2. Set environment variable:
   ```bash
   export GROQ_API_KEY=your_key_here
   ```
3. Verify service:
   ```bash
   curl http://localhost:5000/api/ai/status
   ```

## Common Tasks

### Explain an Error

```bash
curl -X POST http://localhost:5000/api/ai/explain-error \
  -H "Content-Type: application/json" \
  -d '{
    "error_message": "TypeError: Cannot read property name of undefined",
    "error_type": "TypeError",
    "context": "During user registration"
  }'
```

### Create Bug with AI Explanation

```bash
curl -X POST http://localhost:5000/api/projects/PROJECT_ID/bugs \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Login timeout",
    "error_message": "TimeoutError: Request exceeded 30s",
    "severity": "high",
    "generate_explanation": true
  }'
```

### Analyze Test Failure

```bash
curl -X POST http://localhost:5000/api/ai/analyze-test-failure \
  -H "Content-Type: application/json" \
  -d '{
    "test_name": "test_user_login",
    "failure_reason": "Expected 200 OK, got 401 Unauthorized",
    "stack_trace": "tests/test_auth.py:45"
  }'
```

### Analyze Performance

```bash
curl -X POST http://localhost:5000/api/ai/analyze-performance \
  -H "Content-Type: application/json" \
  -d '{
    "metric": "response_time",
    "current_value": 8000,
    "expected_value": 200,
    "details": "API endpoint takes 8 seconds, expected <200ms"
  }'
```

### Batch Explain Errors

```bash
curl -X POST http://localhost:5000/api/ai/batch-explain \
  -H "Content-Type: application/json" \
  -d '{
    "errors": [
      {"message": "TypeError: undefined is not an object"},
      {"message": "ValueError: invalid UUID format"},
      {"message": "ConnectionError: database unreachable"}
    ]
  }'
```

### Get Stored Explanation

```bash
curl http://localhost:5000/api/ai/bugs/BUG_ID/explanation
```

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/ai/status` | GET | Check if service is available |
| `/api/ai/explain-error` | POST | Explain any error |
| `/api/ai/bugs/{id}/analyze` | POST | Generate explanation for bug |
| `/api/ai/bugs/{id}/explanation` | GET | Get stored explanation |
| `/api/ai/analyze-test-failure` | POST | Debug test failures |
| `/api/ai/analyze-performance` | POST | Optimize performance |
| `/api/ai/batch-explain` | POST | Analyze multiple errors |

## Response Structure

All AI endpoints return:

```json
{
  "explanation": "Brief technical explanation",
  "cause": "Root cause analysis",
  "suggested_fix": "Practical fix steps",
  "raw_response": "Full model response",
  "model": "mixtral-8x7b-32768",
  "generated_at": "2024-01-15T10:30:00.000000"
}
```

## Configuration

**Model:** `mixtral-8x7b-32768` (fast, 2-5 seconds)

To change model, edit `services/groq_ai_service.py` line 20:
```python
self.model = "llama2-70b-4096"  # Other option: higher quality
```

**Temperature:** `0.3` (conservative, consistent)

To change, edit `services/groq_ai_service.py` line 21:
```python
self.temperature = 0.5  # 0.0=deterministic, 1.0=creative
```

## Database

Explanations stored in `saas_bugs` table:

```sql
-- View all explanations
SELECT id, title, explanation, cause, suggested_fix 
FROM saas_bugs 
WHERE explanation IS NOT NULL
ORDER BY generated_at DESC;

-- Find most common errors
SELECT error_message, COUNT(*) as frequency
FROM saas_bugs
GROUP BY error_message
ORDER BY frequency DESC
LIMIT 10;
```

## Error Handling

| Status | Meaning | Solution |
|--------|---------|----------|
| 503 | Service unavailable | Check `GROQ_API_KEY` environment variable |
| 401 | Unauthorized | Log in first or check session |
| 400 | Bad request | Check required fields in request |
| 404 | Not found | Check bug/project ID exists |
| 500 | Server error | Check logs for details |

## Tips

1. **Include Context**: More detail = better explanations
2. **Add Error Type**: Helps AI understand the issue
3. **Use Batch for Multiple**: More efficient than individual requests
4. **Cache Results**: Explanations are stored in DB automatically
5. **Check Status First**: Verify service with `/api/ai/status`

## Example Python Integration

```python
from services.groq_ai_service import GroqAIService

# Initialize
ai = GroqAIService()

# Explain error
result = ai.explain_error(
    error_message="Database connection failed",
    error_type="ConnectionError",
    context="During user authentication"
)

# Use results
print(f"Issue: {result['explanation']}")
print(f"Cause: {result['cause']}")
print(f"Fix: {result['suggested_fix']}")
```

## Example JavaScript Integration

```javascript
// Explain error
const response = await fetch('/api/ai/explain-error', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    error_message: "TypeError: cannot read property",
    context: "Form submission"
  })
});

const data = await response.json();
console.log(data.explanation);
console.log(data.suggested_fix);
```

## Troubleshooting

**Service not available?**
```bash
echo $GROQ_API_KEY  # Should print your key
curl http://localhost:5000/api/ai/status  # Should return available: true
```

**API key invalid?**
1. Go to [console.groq.com](https://console.groq.com)
2. Create new API key
3. Update `GROQ_API_KEY` environment variable
4. Restart Flask app

**Slow responses?**
- Normal (2-5 seconds for Groq)
- Use batch endpoints for multiple errors
- Consider async processing

**Poor explanations?**
- Add more context
- Include error type
- Include stack traces
- Try with full error message

## Files Reference

| File | Purpose |
|------|---------|
| `services/groq_ai_service.py` | Core AI service |
| `routes/ai_analysis.py` | API endpoints |
| `scripts/002_add_ai_explanations.sql` | Database schema |
| `AI_ENDPOINTS.md` | Full API documentation |
| `GROQ_INTEGRATION.md` | Setup and integration guide |
| `AI_INTEGRATION_SUMMARY.md` | Summary of changes |

## Documentation Links

- **Full API Docs:** See `AI_ENDPOINTS.md`
- **Setup Guide:** See `GROQ_INTEGRATION.md`
- **Integration Summary:** See `AI_INTEGRATION_SUMMARY.md`
- **Groq Docs:** https://console.groq.com/docs
- **API Status:** https://status.groq.com

## Rate Limits

- No explicit rate limits on Groq API endpoints for most plans
- Check your plan at [console.groq.com](https://console.groq.com)
- Monitor usage in API console
- Plan for ~2-5 seconds per request
- Use batch endpoint for efficiency

## Cost

- Free tier: 500+ calls per day
- Pay-as-you-go available
- Check pricing at [console.groq.com](https://console.groq.com)

---

**Need Help?**
1. Check `/api/ai/status` endpoint
2. Review `AI_ENDPOINTS.md` for full documentation
3. See `GROQ_INTEGRATION.md` for troubleshooting
4. Visit [console.groq.com](https://console.groq.com) for API issues
