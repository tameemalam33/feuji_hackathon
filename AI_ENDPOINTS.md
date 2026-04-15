# AutoQA Pro - AI Analysis Endpoints (Powered by Groq)

This document describes the AI-powered error analysis endpoints integrated with Groq LLM.

## Overview

The AI analysis service provides intelligent error explanation and debugging suggestions using Groq's Mixtral-8x7b model. All endpoints require authentication via session or JWT tokens.

## Base URL

```
/api/ai
```

## Authentication

All endpoints require user authentication. Include session cookies or JWT tokens in requests.

## Endpoints

### 1. Get AI Service Status

Check if the AI service is available and get model information.

**Endpoint:** `GET /api/ai/status`

**Authentication:** Not required

**Response:**
```json
{
  "available": true,
  "model": "mixtral-8x7b-32768"
}
```

---

### 2. Explain Generic Error

Generate AI explanation for any error message.

**Endpoint:** `POST /api/ai/explain-error`

**Authentication:** Required

**Request Body:**
```json
{
  "error_message": "TypeError: Cannot read property 'name' of undefined",
  "error_type": "TypeError",
  "context": "Occurred in user registration form submission"
}
```

**Parameters:**
- `error_message` (string, required): The error message or stack trace to analyze
- `error_type` (string, optional): Type of error (e.g., 'TypeError', 'ValueError')
- `context` (string, optional): Additional context about when/where the error occurred

**Response:**
```json
{
  "explanation": "The code attempted to access the 'name' property on an undefined object, causing a TypeError.",
  "cause": "The object was not properly initialized before accessing its properties.",
  "suggested_fix": "Add null checks before accessing object properties or ensure the object is instantiated before use.",
  "raw_response": "...",
  "model": "mixtral-8x7b-32768",
  "generated_at": "2024-01-15T10:30:00.000000"
}
```

---

### 3. Analyze Bug Report

Generate AI explanation for a specific bug and store it in the database.

**Endpoint:** `POST /api/ai/bugs/{bug_id}/analyze`

**Authentication:** Required

**Path Parameters:**
- `bug_id` (string, UUID): The ID of the bug to analyze

**Response:**
```json
{
  "bug_id": "550e8400-e29b-41d4-a716-446655440000",
  "explanation": "The authentication token expired due to the session timeout setting being too short.",
  "cause": "Session tokens were configured with a 15-minute expiration instead of the standard 24-hour window.",
  "suggested_fix": "Update the SESSION_TIMEOUT configuration to 86400 seconds (24 hours) and implement token refresh mechanisms.",
  "model": "mixtral-8x7b-32768",
  "generated_at": "2024-01-15T10:30:00.000000"
}
```

---

### 4. Get Stored Bug Explanation

Retrieve AI explanation for a bug (returns empty if not yet generated).

**Endpoint:** `GET /api/ai/bugs/{bug_id}/explanation`

**Authentication:** Required

**Path Parameters:**
- `bug_id` (string, UUID): The ID of the bug

**Response:**
```json
{
  "bug_id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Login page timeout error",
  "explanation": "The authentication token expired due to the session timeout setting being too short.",
  "cause": "Session tokens were configured with a 15-minute expiration instead of the standard 24-hour window.",
  "suggested_fix": "Update the SESSION_TIMEOUT configuration to 86400 seconds (24 hours) and implement token refresh mechanisms.",
  "model": "mixtral-8x7b-32768",
  "generated_at": "2024-01-15T10:30:00.000000"
}
```

---

### 5. Analyze Test Failure

Analyze a test failure with AI to identify the root cause and debugging steps.

**Endpoint:** `POST /api/ai/analyze-test-failure`

**Authentication:** Required

**Request Body:**
```json
{
  "test_name": "test_user_registration_with_existing_email",
  "failure_reason": "Expected error response, got 200 OK",
  "stack_trace": "File 'tests/test_auth.py', line 45, in test_user_registration\n    assert response.status_code == 400"
}
```

**Parameters:**
- `test_name` (string, required): Name of the failing test
- `failure_reason` (string, required): Why the test failed
- `stack_trace` (string, optional): Full stack trace from the test failure

**Response:**
```json
{
  "explanation": "The test expected a 400 error when registering with an existing email, but the registration succeeded.",
  "cause": "Email uniqueness validation was disabled or bypassed in the current code.",
  "suggested_fix": "Verify that email uniqueness constraints are enabled in the database schema and that the validation middleware is properly applied.",
  "raw_response": "...",
  "model": "mixtral-8x7b-32768",
  "generated_at": "2024-01-15T10:30:00.000000"
}
```

---

### 6. Analyze Performance Issue

Get AI suggestions for optimizing performance problems.

**Endpoint:** `POST /api/ai/analyze-performance`

**Authentication:** Required

**Request Body:**
```json
{
  "metric": "response_time",
  "current_value": 5000,
  "expected_value": 200,
  "details": "Query returns 50,000 rows and filters in application code"
}
```

**Parameters:**
- `metric` (string, required): Performance metric name (e.g., 'response_time', 'memory_usage', 'cpu_usage')
- `current_value` (number, required): Current measured value
- `expected_value` (number, required): Expected or target value
- `details` (string, optional): Additional performance context

**Response:**
```json
{
  "explanation": "The database query is retrieving all 50,000 rows and filtering on the application side, causing network overhead and memory waste.",
  "cause": "Missing database-side filtering and pagination in the SQL query.",
  "suggested_fix": "Move the WHERE clause and LIMIT from application code to SQL query. Implement pagination with OFFSET/LIMIT. Add database indexes on filtered columns.",
  "raw_response": "...",
  "model": "mixtral-8x7b-32768",
  "generated_at": "2024-01-15T10:30:00.000000"
}
```

---

### 7. Batch Explain Multiple Errors

Analyze multiple errors in a single request (efficient for reports).

**Endpoint:** `POST /api/ai/batch-explain`

**Authentication:** Required

**Request Body:**
```json
{
  "errors": [
    {
      "message": "TypeError: Cannot read property 'length' of null",
      "type": "TypeError",
      "context": "In data validation function"
    },
    {
      "message": "ValueError: Invalid UUID format",
      "type": "ValueError",
      "context": "During user lookup"
    }
  ]
}
```

**Parameters:**
- `errors` (array, required): Array of error objects to analyze
  - Each error object can have:
    - `message` (string): Error message to analyze
    - `type` (string, optional): Error type
    - `context` (string, optional): Additional context

**Response:**
```json
{
  "results": [
    {
      "explanation": "The code attempted to access the length of a null value.",
      "cause": "Input data was not properly validated before use.",
      "suggested_fix": "Add null checks and validate data structure before processing.",
      "raw_response": "...",
      "model": "mixtral-8x7b-32768",
      "generated_at": "2024-01-15T10:30:01.000000"
    },
    {
      "explanation": "The UUID string format was invalid (expected format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx).",
      "cause": "User provided input with incorrect UUID formatting.",
      "suggested_fix": "Implement UUID validation before database queries. Use uuid.UUID() constructor with error handling.",
      "raw_response": "...",
      "model": "mixtral-8x7b-32768",
      "generated_at": "2024-01-15T10:30:02.000000"
    }
  ]
}
```

---

## Usage Examples

### Example 1: Get Error Explanation in Bug Report

```bash
curl -X POST http://localhost:5000/api/ai/explain-error \
  -H "Content-Type: application/json" \
  -H "Cookie: session=your_session_id" \
  -d '{
    "error_message": "ConnectionError: Failed to connect to database",
    "error_type": "ConnectionError",
    "context": "During user login process"
  }'
```

### Example 2: Analyze Stored Bug

```bash
curl -X POST http://localhost:5000/api/ai/bugs/550e8400-e29b-41d4-a716-446655440000/analyze \
  -H "Cookie: session=your_session_id"
```

### Example 3: Create Bug with Auto-Explanation

```bash
curl -X POST http://localhost:5000/api/projects/project-id/bugs \
  -H "Content-Type: application/json" \
  -H "Cookie: session=your_session_id" \
  -d '{
    "title": "Login fails with timeout",
    "description": "Users cannot log in after 10 minutes",
    "severity": "high",
    "error_message": "TimeoutError: Request exceeded 30 second limit",
    "error_type": "TimeoutError",
    "generate_explanation": true
  }'
```

---

## Error Responses

All endpoints return appropriate HTTP status codes and error messages:

**400 Bad Request:**
```json
{
  "error": "error_message is required"
}
```

**401 Unauthorized:**
```json
{
  "error": "Authentication required"
}
```

**404 Not Found:**
```json
{
  "error": "Bug not found"
}
```

**503 Service Unavailable:**
```json
{
  "error": "AI service not configured"
}
```

**500 Internal Server Error:**
```json
{
  "error": "Internal server error"
}
```

---

## Integration with Bug Reports

When creating a bug report, you can request automatic AI explanation generation:

```json
POST /api/projects/{project_id}/bugs

{
  "title": "Database connection timeout",
  "description": "Connections timeout after 30 seconds",
  "severity": "critical",
  "error_message": "psycopg2.OperationalError: server closed the connection unexpectedly",
  "error_type": "OperationalError",
  "generate_explanation": true
}
```

The response will include the bug data plus the AI explanation:

```json
{
  "message": "Bug reported successfully",
  "bug": { ... },
  "ai_explanation": {
    "explanation": "...",
    "cause": "...",
    "suggested_fix": "...",
    "generated_at": "..."
  }
}
```

---

## Performance Considerations

- AI explanation generation typically takes 2-5 seconds per request
- For batch operations, consider processing errors asynchronously
- Explanations are cached in the database for future reference
- Status endpoint (`/api/ai/status`) can be called to verify service availability before making requests

---

## Configuration

The AI service requires:
- `GROQ_API_KEY` environment variable set with a valid Groq API key
- Groq API key should have access to the Mixtral-8x7b-32768 model

If the API key is not configured, the service will return 503 Service Unavailable for AI endpoints.

---

## Troubleshooting

**Service Not Available:**
- Check that `GROQ_API_KEY` environment variable is set
- Verify Groq API key has appropriate permissions
- Check Groq API status at https://status.groq.com

**Slow Responses:**
- AI explanation generation can take 2-5 seconds
- Consider using batch endpoints for multiple errors
- Monitor Groq API quotas and rate limits

**Poor Explanations:**
- Provide detailed error messages and context
- Include error types for better analysis
- Add relevant context about when/where errors occur
