# AutoQA Pro - Groq AI Integration Guide

This guide explains how to set up and use the Groq AI integration for intelligent error analysis in AutoQA Pro.

## Overview

AutoQA Pro now includes AI-powered error explanation using Groq's Mixtral-8x7b model. This feature helps developers understand errors faster by providing:

- **Error Explanations**: What went wrong and why
- **Root Cause Analysis**: The underlying issue causing the error
- **Suggested Fixes**: Practical steps to resolve the problem
- **Test Failure Analysis**: Debugging assistance for test failures
- **Performance Diagnostics**: Optimization suggestions for slow operations

## Setup

### 1. Get Groq API Key

1. Visit [console.groq.com](https://console.groq.com)
2. Sign up or log in
3. Create a new API key
4. Copy the API key (save it securely)

### 2. Set Environment Variable

Add the Groq API key to your environment:

**Local Development (.env file):**
```bash
GROQ_API_KEY=your_api_key_here
```

**Production (Vercel):**
1. Go to your Vercel project settings
2. Navigate to Environment Variables
3. Add `GROQ_API_KEY` with your API key value
4. Ensure it's set for all environments (Development, Preview, Production)

### 3. Verify Installation

Dependencies are automatically installed from `requirements.txt`:
- `groq>=0.4.1` - Groq Python SDK
- `psycopg2-binary>=2.9.0` - PostgreSQL adapter
- `bcrypt>=4.0.0` - Password hashing

To manually install:
```bash
pip install groq>=0.4.1
```

### 4. Start the Application

The AI service is automatically initialized when the Flask app starts. Check the status endpoint:

```bash
curl http://localhost:5000/api/ai/status
```

Expected response:
```json
{
  "available": true,
  "model": "mixtral-8x7b-32768"
}
```

## Feature Usage

### Feature 1: Automatic Bug Analysis

When creating a bug report, request automatic AI explanation:

```bash
curl -X POST http://localhost:5000/api/projects/{project_id}/bugs \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Database connection failed",
    "description": "Users cannot log in",
    "severity": "critical",
    "error_message": "psycopg2.OperationalError: could not connect to server",
    "error_type": "OperationalError",
    "generate_explanation": true
  }'
```

The response includes AI-generated explanation:
```json
{
  "message": "Bug reported successfully",
  "bug": { ... },
  "ai_explanation": {
    "explanation": "The database server is not reachable, preventing connection attempts.",
    "cause": "Database service is down or network connectivity is broken.",
    "suggested_fix": "Check database service status, verify connection string, and test network connectivity to the database server."
  }
}
```

### Feature 2: Direct Error Explanation

Analyze any error without creating a bug:

```bash
curl -X POST http://localhost:5000/api/ai/explain-error \
  -H "Content-Type: application/json" \
  -d '{
    "error_message": "TypeError: Cannot read property of undefined",
    "error_type": "TypeError",
    "context": "During form submission"
  }'
```

### Feature 3: Test Failure Analysis

Get debugging suggestions for failing tests:

```bash
curl -X POST http://localhost:5000/api/ai/analyze-test-failure \
  -H "Content-Type: application/json" \
  -d '{
    "test_name": "test_user_login_success",
    "failure_reason": "Expected status 200, got 401",
    "stack_trace": "File tests/test_auth.py line 45"
  }'
```

### Feature 4: Performance Analysis

Get optimization suggestions:

```bash
curl -X POST http://localhost:5000/api/ai/analyze-performance \
  -H "Content-Type: application/json" \
  -d '{
    "metric": "response_time",
    "current_value": 8000,
    "expected_value": 500,
    "details": "API endpoint returns 100k records without pagination"
  }'
```

### Feature 5: Batch Error Analysis

Analyze multiple errors efficiently:

```bash
curl -X POST http://localhost:5000/api/ai/batch-explain \
  -H "Content-Type: application/json" \
  -d '{
    "errors": [
      {"message": "Error 1", "type": "TypeError"},
      {"message": "Error 2", "type": "ValueError"},
      {"message": "Error 3", "context": "In API endpoint"}
    ]
  }'
```

## Database Schema

The AI explanation data is stored in the `saas_bugs` table. When an explanation is generated, these columns are populated:

```sql
- explanation TEXT          -- What went wrong
- cause TEXT               -- Root cause
- suggested_fix TEXT       -- How to fix it
- raw_response TEXT        -- Full model response
- model VARCHAR(255)       -- Model name used
- generated_at TIMESTAMP   -- When explanation was generated
```

## API Endpoints

### AI Analysis Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/ai/status` | Check AI service availability |
| POST | `/api/ai/explain-error` | Get explanation for any error |
| POST | `/api/ai/bugs/{id}/analyze` | Analyze a specific bug |
| GET | `/api/ai/bugs/{id}/explanation` | Get stored bug explanation |
| POST | `/api/ai/analyze-test-failure` | Debug failing tests |
| POST | `/api/ai/analyze-performance` | Optimize performance issues |
| POST | `/api/ai/batch-explain` | Analyze multiple errors |

See [AI_ENDPOINTS.md](./AI_ENDPOINTS.md) for detailed documentation.

## Configuration

### Model Selection

Currently using: **Mixtral-8x7b-32768**
- Fast inference (2-5 seconds per explanation)
- Good balance of speed and quality
- Handles technical content well

To change the model, edit `services/groq_ai_service.py`:
```python
self.model = "mixtral-8x7b-32768"  # Change this line
```

Available models on Groq:
- `mixtral-8x7b-32768` (fastest)
- `llama2-70b-4096` (highest quality)
- `gemma-7b-it` (lightweight)

### Temperature Setting

Currently set to 0.3 (conservative) for consistent, technical explanations.

To adjust, edit `groq_ai_service.py`:
```python
self.temperature = 0.3  # Range: 0.0 (deterministic) to 1.0 (creative)
```

Lower temperature = more consistent, deterministic responses
Higher temperature = more varied, creative responses

## Rate Limiting

Groq API includes rate limiting. Monitor your usage:

1. Visit [console.groq.com](https://console.groq.com)
2. Check your API usage and limits
3. Plan accordingly for high-traffic scenarios

Recommended practices:
- Use batch endpoint for multiple errors
- Cache explanations in the database (they're already stored)
- Implement request queuing for high-volume scenarios

## Error Handling

If the AI service encounters issues:

**Service Not Available:**
- Returns 503 status code
- Check `GROQ_API_KEY` environment variable
- Verify Groq API status

**API Key Invalid:**
- Check API key in console.groq.com
- Ensure key is not revoked or expired
- Update environment variable and restart app

**Rate Limit Exceeded:**
- Wait before making new requests
- Consider upgrading Groq API plan
- Implement request queuing

**Timeout:**
- AI generation can take 2-5 seconds
- Increase timeout settings if needed
- Consider making requests asynchronous

## Monitoring

### Logs

Check Flask logs for AI service activity:
```
[services.groq_ai_service] Error calling Groq API: ...
[routes.ai_analysis] Error analyzing bug: ...
```

### Database

Query stored explanations:
```sql
SELECT id, title, explanation, cause, suggested_fix, generated_at
FROM saas_bugs
WHERE explanation IS NOT NULL
ORDER BY generated_at DESC
LIMIT 10;
```

## Testing

### Test the Service

```bash
# Check status
curl http://localhost:5000/api/ai/status

# Test with sample error
curl -X POST http://localhost:5000/api/ai/explain-error \
  -H "Content-Type: application/json" \
  -d '{
    "error_message": "IndexError: list index out of range",
    "error_type": "IndexError",
    "context": "In data processing function"
  }'
```

### Test in Production

1. Verify environment variable is set
2. Call `/api/ai/status` endpoint
3. Create a test bug with `generate_explanation: true`
4. Verify explanation is generated and stored

## Security Considerations

### API Key Protection

- Never commit API keys to version control
- Use environment variables
- Rotate keys periodically
- Monitor API usage for unauthorized access

### Data Privacy

- Error messages may contain sensitive information
- Be cautious with production errors
- Review and sanitize error messages before sending to AI
- Explanations are stored in the database

### Rate Limiting

- Implement request rate limiting on your API
- Use batch endpoints to reduce requests
- Monitor Groq API quotas

## Troubleshooting

### AI Service Not Available

**Symptom:** Returns `{"error": "AI service not configured"}` with 503 status

**Solution:**
1. Check `GROQ_API_KEY` environment variable is set
2. Restart the Flask application
3. Verify API key is valid in console.groq.com

### Slow Responses

**Symptom:** AI endpoints take >5 seconds

**Solution:**
1. This is normal (Groq inference can take 2-5 seconds)
2. Consider making requests asynchronous
3. Use batch endpoints for multiple errors
4. Check Groq API status and rate limits

### Poor Quality Explanations

**Symptom:** Explanations are vague or unhelpful

**Solution:**
1. Provide more detailed error messages
2. Include error type and context
3. Include stack traces for complex errors
4. Try with different error examples

### "Invalid API Key" Error

**Symptom:** `groq.AuthenticationError: Invalid API key`

**Solution:**
1. Verify key in console.groq.com
2. Check key hasn't been revoked
3. Ensure key is not expired
4. Update environment variable
5. Restart application

## Example Implementation

### In Your Application Code

```python
from services.groq_ai_service import GroqAIService

# Initialize service
try:
    ai_service = GroqAIService()
except ValueError:
    print("Groq API key not configured")
    ai_service = None

# Use service
if ai_service:
    result = ai_service.explain_error(
        error_message="Database connection timeout",
        error_type="TimeoutError",
        context="During user authentication"
    )
    
    print(f"Explanation: {result['explanation']}")
    print(f"Cause: {result['cause']}")
    print(f"Fix: {result['suggested_fix']}")
```

### In Frontend (JavaScript)

```javascript
// Create bug with AI explanation
async function createBugWithAI() {
  const response = await fetch('/api/projects/project-id/bugs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      title: 'Login button broken',
      error_message: 'TypeError: Cannot read property click',
      generate_explanation: true
    })
  });
  
  const data = await response.json();
  if (data.ai_explanation) {
    console.log('AI Explanation:', data.ai_explanation);
  }
}

// Get stored explanation
async function getBugExplanation(bugId) {
  const response = await fetch(`/api/ai/bugs/${bugId}/explanation`);
  const data = await response.json();
  return data;
}
```

## Future Enhancements

Potential improvements for the Groq integration:

1. **Asynchronous Processing**: Queue AI requests for high-volume scenarios
2. **Caching**: Smart caching of similar errors
3. **Learning**: Track which explanations were most helpful
4. **Multi-Language**: Translate explanations to different languages
5. **Integration**: Connect with issue tracking systems
6. **Custom Models**: Fine-tune model for specific error types
7. **Webhooks**: Notify when important errors are explained

## Support

For issues with:

- **Groq API**: Visit [console.groq.com](https://console.groq.com) or check status at [status.groq.com](https://status.groq.com)
- **AutoQA Pro**: Review API documentation or contact support
- **Integration**: See [AI_ENDPOINTS.md](./AI_ENDPOINTS.md) for detailed examples

---

Last Updated: 2024-01-15
