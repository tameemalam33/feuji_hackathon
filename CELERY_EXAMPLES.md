# Celery Job Queue Examples

Complete examples for testing and using the Celery background job system.

## Quick Start

### 1. Queue a Test Run

```bash
curl -X POST http://localhost:5000/api/jobs/run-tests \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "mode": "standard",
    "page_limit": 30,
    "max_depth": 2
  }'
```

**Response:**
```json
{
  "job_id": "9d4e1c3b-2f5a-4d8e-a1b2-c3d4e5f6a7b8",
  "status": "queued",
  "message": "Test run queued successfully"
}
```

### 2. Check Job Status

```bash
curl http://localhost:5000/api/jobs/9d4e1c3b-2f5a-4d8e-a1b2-c3d4e5f6a7b8
```

**Response:**
```json
{
  "job_id": "9d4e1c3b-2f5a-4d8e-a1b2-c3d4e5f6a7b8",
  "status": "progress",
  "progress": 45,
  "progress_message": "Running tests on page 15/50",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:35:22Z",
  "completed_at": null
}
```

### 3. Poll Until Complete

```python
import requests
import time

job_id = "9d4e1c3b-2f5a-4d8e-a1b2-c3d4e5f6a7b8"
api_url = "http://localhost:5000"

while True:
    response = requests.get(f"{api_url}/api/jobs/{job_id}")
    job = response.json()
    
    print(f"Status: {job['status']}")
    print(f"Progress: {job.get('progress', 0)}%")
    
    if job['status'] in ['completed', 'failed', 'cancelled']:
        print(f"Result: {job.get('result', {})}")
        break
    
    time.sleep(2)  # Poll every 2 seconds
```

## API Usage Examples

### Queue Project Tests

```bash
curl -X POST http://localhost:5000/api/jobs/projects/{project_uuid}/run-tests \
  -H "Authorization: Bearer YOUR_SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://myapp.example.com",
    "mode": "deep",
    "task_id": "optional-task-uuid"
  }'
```

### Queue Task Tests

```bash
curl -X POST http://localhost:5000/api/jobs/tasks/{task_uuid}/run-tests \
  -H "Authorization: Bearer YOUR_SESSION_TOKEN"
```

### List User's Jobs

```bash
curl "http://localhost:5000/api/jobs?limit=20&status=completed" \
  -H "Authorization: Bearer YOUR_SESSION_TOKEN"
```

Response:
```json
[
  {
    "job_id": "9d4e1c3b-2f5a-4d8e-a1b2-c3d4e5f6a7b8",
    "status": "completed",
    "job_type": "run_qa",
    "progress": 100,
    "created_at": "2024-01-15T10:30:00Z"
  },
  {
    "job_id": "8c3d2b1a-0f9e-8d7c-6b5a-4d3e2f1a0b9c",
    "status": "failed",
    "job_type": "run_task_tests",
    "progress": 75,
    "created_at": "2024-01-15T09:45:00Z"
  }
]
```

### Cancel a Job

```bash
curl -X DELETE http://localhost:5000/api/jobs/{job_uuid}
```

Response:
```json
{
  "job_id": "9d4e1c3b-2f5a-4d8e-a1b2-c3d4e5f6a7b8",
  "status": "cancelled"
}
```

### Get Job Statistics

```bash
curl http://localhost:5000/api/monitoring/jobs/stats \
  -H "Authorization: Bearer YOUR_SESSION_TOKEN"
```

Response:
```json
{
  "total_jobs": 150,
  "queued": 5,
  "running": 3,
  "completed": 140,
  "failed": 2,
  "average_duration": 245.5,
  "success_rate": 98.6
}
```

### Get Queue Health

```bash
curl http://localhost:5000/api/monitoring/jobs/queue-health \
  -H "Authorization: Bearer YOUR_SESSION_TOKEN"
```

Response:
```json
{
  "healthy": true,
  "queue_length": 5,
  "oldest_queued_job": "2024-01-15T10:30:00Z",
  "processing_rate": 2.5,
  "last_check": "2024-01-15T10:35:00Z"
}
```

### Get Recent Jobs

```bash
curl "http://localhost:5000/api/monitoring/jobs/recent?hours=24&limit=10" \
  -H "Authorization: Bearer YOUR_SESSION_TOKEN"
```

Response:
```json
[
  {
    "job_id": "9d4e1c3b-2f5a-4d8e-a1b2-c3d4e5f6a7b8",
    "job_type": "run_qa",
    "status": "completed",
    "duration": 245.5,
    "completed_at": "2024-01-15T10:45:00Z",
    "error": null
  }
]
```

### Cleanup Old Jobs (Admin Only)

```bash
curl -X POST http://localhost:5000/api/monitoring/jobs/cleanup \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "days": 7
  }'
```

Response:
```json
{
  "deleted": 42,
  "message": "Cleaned up 42 old job records"
}
```

## Python Client Example

```python
import requests
import json
from typing import Optional, Dict, Any

class AutoQAClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.headers = {"Authorization": f"Bearer {api_key}"}
    
    def queue_test_run(self, url: str, mode: str = "standard", 
                       page_limit: int = 30, max_depth: int = 2) -> str:
        """Queue a new test run and return job ID."""
        response = requests.post(
            f"{self.base_url}/api/jobs/run-tests",
            headers=self.headers,
            json={
                "url": url,
                "mode": mode,
                "page_limit": page_limit,
                "max_depth": max_depth
            }
        )
        response.raise_for_status()
        return response.json()["job_id"]
    
    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get the current status of a job."""
        response = requests.get(
            f"{self.base_url}/api/jobs/{job_id}",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def wait_for_completion(self, job_id: str, timeout: int = 3600, 
                           poll_interval: int = 2) -> Dict[str, Any]:
        """Wait for a job to complete."""
        import time
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            job = self.get_job_status(job_id)
            
            if job['status'] in ['completed', 'failed', 'cancelled']:
                return job
            
            print(f"Status: {job['status']} | Progress: {job.get('progress', 0)}%")
            time.sleep(poll_interval)
        
        raise TimeoutError(f"Job {job_id} did not complete within {timeout}s")
    
    def cancel_job(self, job_id: str) -> Dict[str, Any]:
        """Cancel a running job."""
        response = requests.delete(
            f"{self.base_url}/api/jobs/{job_id}",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def list_jobs(self, limit: int = 50) -> list:
        """List the user's jobs."""
        response = requests.get(
            f"{self.base_url}/api/jobs?limit={limit}",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

# Usage
client = AutoQAClient("http://localhost:5000", "your-api-key")

# Queue a test
job_id = client.queue_test_run("https://example.com", mode="deep")
print(f"Queued job: {job_id}")

# Wait for completion
result = client.wait_for_completion(job_id)
print(f"Test completed: {result['status']}")
print(f"Results: {result.get('result', {})}")
```

## JavaScript/Node.js Example

```javascript
class AutoQAClient {
  constructor(baseUrl, apiKey) {
    this.baseUrl = baseUrl.replace(/\/$/, '');
    this.apiKey = apiKey;
  }

  async queueTestRun(url, options = {}) {
    const {
      mode = 'standard',
      pageLimit = 30,
      maxDepth = 2
    } = options;

    const response = await fetch(`${this.baseUrl}/api/jobs/run-tests`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        url,
        mode,
        page_limit: pageLimit,
        max_depth: maxDepth
      })
    });

    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    return data.job_id;
  }

  async getJobStatus(jobId) {
    const response = await fetch(`${this.baseUrl}/api/jobs/${jobId}`, {
      headers: { 'Authorization': `Bearer ${this.apiKey}` }
    });

    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }

  async waitForCompletion(jobId, options = {}) {
    const { timeout = 3600000, pollInterval = 2000 } = options;
    const startTime = Date.now();

    while (Date.now() - startTime < timeout) {
      const job = await this.getJobStatus(jobId);

      if (['completed', 'failed', 'cancelled'].includes(job.status)) {
        return job;
      }

      console.log(`Status: ${job.status} | Progress: ${job.progress || 0}%`);
      await new Promise(resolve => setTimeout(resolve, pollInterval));
    }

    throw new Error(`Job ${jobId} did not complete within ${timeout}ms`);
  }

  async cancelJob(jobId) {
    const response = await fetch(`${this.baseUrl}/api/jobs/${jobId}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${this.apiKey}` }
    });

    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }
}

// Usage
const client = new AutoQAClient('http://localhost:5000', 'your-api-key');

(async () => {
  // Queue a test
  const jobId = await client.queueTestRun('https://example.com', { mode: 'deep' });
  console.log(`Queued job: ${jobId}`);

  // Wait for completion
  const result = await client.waitForCompletion(jobId);
  console.log(`Test completed: ${result.status}`);
  console.log(`Results:`, result.result);
})();
```

## Testing with Postman

Import this into Postman to test the APIs:

```json
{
  "info": {
    "name": "AutoQA Celery Jobs",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Queue Test Run",
      "request": {
        "method": "POST",
        "header": [
          {"key": "Authorization", "value": "Bearer {{api_key}}"},
          {"key": "Content-Type", "value": "application/json"}
        ],
        "body": {
          "mode": "raw",
          "raw": "{\"url\": \"https://example.com\", \"mode\": \"standard\"}"
        },
        "url": {"raw": "{{base_url}}/api/jobs/run-tests", "host": ["{{base_url}}"], "path": ["api", "jobs", "run-tests"]}
      }
    },
    {
      "name": "Get Job Status",
      "request": {
        "method": "GET",
        "header": [{"key": "Authorization", "value": "Bearer {{api_key}}"}],
        "url": {"raw": "{{base_url}}/api/jobs/{{job_id}}", "host": ["{{base_url}}"], "path": ["api", "jobs", "{{job_id}}"]}
      }
    },
    {
      "name": "List Jobs",
      "request": {
        "method": "GET",
        "header": [{"key": "Authorization", "value": "Bearer {{api_key}}"}],
        "url": {"raw": "{{base_url}}/api/jobs?limit=20", "host": ["{{base_url}}"], "path": ["api", "jobs"]}
      }
    },
    {
      "name": "Cancel Job",
      "request": {
        "method": "DELETE",
        "header": [{"key": "Authorization", "value": "Bearer {{api_key}}"}],
        "url": {"raw": "{{base_url}}/api/jobs/{{job_id}}", "host": ["{{base_url}}"], "path": ["api", "jobs", "{{job_id}}"]}
      }
    },
    {
      "name": "Get Job Stats",
      "request": {
        "method": "GET",
        "header": [{"key": "Authorization", "value": "Bearer {{api_key}}"}],
        "url": {"raw": "{{base_url}}/api/monitoring/jobs/stats", "host": ["{{base_url}}"], "path": ["api", "monitoring", "jobs", "stats"]}
      }
    }
  ]
}
```

Set environment variables in Postman:
- `base_url`: http://localhost:5000
- `api_key`: Your API key
- `job_id`: Job ID from queue response
