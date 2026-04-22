# Celery Background Job Configuration

This document covers the Celery setup for processing long-running QA tests asynchronously.

## Overview

The system uses **Celery** with **Redis** (Upstash) as the message broker to queue and execute long-running test operations without blocking the API server.

### Architecture

```
Flask API (routes/job_api.py)
    ↓
    Queue Task (Celery)
    ↓
    Redis (Upstash)
    ↓
    Celery Worker (services/celery_tasks.py)
    ↓
    Database (job_queue table)
```

## Environment Variables

Required environment variables for Celery:

```bash
# Redis Configuration (Upstash)
REDIS_URL=redis://default:password@host:port/0

# Celery Settings (optional)
CELERY_CONCURRENCY=2          # Number of parallel workers
CELERY_TASK_TIME_LIMIT=1800   # Hard limit: 30 minutes
CELERY_TASK_SOFT_TIME_LIMIT=1500  # Soft limit: 25 minutes
```

The `REDIS_URL` is automatically set by Vercel when you connect Upstash for Redis.

## Installation & Setup

### 1. Install Dependencies

Dependencies are already in `requirements.txt`:
- celery>=5.3.0
- redis>=5.0.0

Install if not already done:
```bash
pip install -r requirements.txt
```

### 2. Start the Celery Worker

In production or development, start the worker in a separate terminal:

```bash
# Using the utility script
python -m utils.celery_worker

# Or directly with Celery
celery -A celery_app worker --loglevel=info --concurrency=2
```

### 3. Monitor Jobs

View job status:
```bash
GET /api/jobs/{job_id}
```

List user's jobs:
```bash
GET /api/jobs
```

Get queue statistics:
```bash
GET /api/monitoring/jobs/stats
```

## API Endpoints

### Queue Operations

#### Queue a QA Test Run
```bash
POST /api/jobs/run-tests
Authorization: Bearer <API_KEY>

{
  "url": "https://example.com",
  "mode": "standard",
  "page_limit": 30,
  "max_depth": 2
}

Response:
{
  "job_id": "abc123def456",
  "status": "queued",
  "message": "Test run queued successfully"
}
```

#### Queue Project Tests
```bash
POST /api/jobs/projects/{project_id}/run-tests
Authorization: Bearer <SESSION_TOKEN>

{
  "url": "https://example.com",
  "mode": "standard",
  "task_id": "optional-task-uuid"
}

Response:
{
  "job_id": "abc123def456",
  "status": "queued",
  "project_id": "project-uuid"
}
```

#### Queue Task Tests
```bash
POST /api/jobs/tasks/{task_id}/run-tests
Authorization: Bearer <SESSION_TOKEN>

Response:
{
  "job_id": "abc123def456",
  "status": "queued",
  "task_id": "task-uuid"
}
```

### Job Tracking

#### Get Job Status
```bash
GET /api/jobs/{job_id}

Response:
{
  "job_id": "abc123def456",
  "status": "progress",
  "progress": 45,
  "progress_message": "Running tests on page 15/50",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:35:00Z",
  "completed_at": null
}
```

#### List Jobs
```bash
GET /api/jobs?project_id={uuid}&status=completed&limit=20

Response:
[
  {
    "job_id": "abc123def456",
    "status": "completed",
    "job_type": "run_qa",
    "progress": 100,
    "created_at": "2024-01-15T10:30:00Z"
  }
]
```

#### Cancel Job
```bash
DELETE /api/jobs/{job_id}

Response:
{
  "job_id": "abc123def456",
  "status": "cancelled"
}
```

### Monitoring

#### Get Job Statistics
```bash
GET /api/monitoring/jobs/stats
Authorization: Bearer <SESSION_TOKEN>

Response:
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

#### Get Recent Jobs
```bash
GET /api/monitoring/jobs/recent?hours=24&limit=20
Authorization: Bearer <SESSION_TOKEN>

Response:
[
  {
    "job_id": "abc123def456",
    "job_type": "run_qa",
    "status": "completed",
    "duration": 245.5,
    "completed_at": "2024-01-15T10:45:00Z",
    "error": null
  }
]
```

#### Get Queue Health
```bash
GET /api/monitoring/jobs/queue-health
Authorization: Bearer <SESSION_TOKEN>

Response:
{
  "healthy": true,
  "queue_length": 5,
  "oldest_queued_job": "2024-01-15T10:30:00Z",
  "processing_rate": 2.5,
  "last_check": "2024-01-15T10:35:00Z"
}
```

#### Cleanup Old Jobs (Admin Only)
```bash
POST /api/monitoring/jobs/cleanup
Authorization: Bearer <ADMIN_TOKEN>

{
  "days": 7
}

Response:
{
  "deleted": 42,
  "message": "Cleaned up 42 old job records"
}
```

## Job Status Values

- **queued**: Task is waiting to be processed
- **started**: Worker has started processing
- **progress**: In progress with periodic updates
- **completed**: Successfully finished
- **failed**: Encountered an error
- **cancelled**: Cancelled by user

## Database Schema

Jobs are tracked in the `job_queue` table:

```sql
CREATE TABLE public.job_queue (
    id BIGSERIAL PRIMARY KEY,
    job_id UUID NOT NULL UNIQUE,              -- Celery task ID
    job_type VARCHAR(50) NOT NULL,            -- run_qa, run_task_tests, etc.
    status VARCHAR(20) NOT NULL,              -- queued, started, progress, completed, failed
    user_id UUID,                             -- Associated user
    project_id UUID,                          -- Associated project
    task_id UUID,                             -- Associated task (optional)
    progress FLOAT,                           -- 0-100
    progress_message VARCHAR(255),            -- Human-readable progress
    result JSONB,                             -- Job result data
    error_message VARCHAR(500),               -- Error message if failed
    error_traceback TEXT,                     -- Full traceback
    duration_seconds FLOAT,                   -- Execution time
    metadata JSONB,                           -- Additional context
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);
```

## Task Types

### 1. run_qa_tests
Executes full QA test suite for a project or public URL.

**Input:**
- project_id: UUID or null for public API
- user_id: UUID or null for public API
- metadata: {url, mode, page_limit, max_depth}

**Output:**
```json
{
  "total_tests": 150,
  "passed": 145,
  "failed": 5,
  "success_rate": 96.7,
  "summary": {...}
}
```

### 2. run_task_tests
Executes tests for a specific task.

**Input:**
- task_id: UUID
- project_id: UUID
- user_id: UUID

**Output:**
Same as run_qa_tests

### 3. generate_report
Generates comprehensive QA report.

**Input:**
- project_id: UUID
- user_id: UUID
- filters: Optional report filters

**Output:**
```json
{
  "project_id": "...",
  "generated_at": 1705320000,
  "total_tests": 150,
  "passed": 145,
  "failed": 5,
  "success_rate": 96.7
}
```

## Progress Tracking

Tasks report progress via the `job_queue` table:

```python
job_service.update_job_status(
    job_id=job_id,
    status="progress",
    progress=45,
    progress_message="Running tests on page 15/50"
)
```

Frontend can poll the status endpoint to show real-time progress.

## Error Handling

If a task fails, the error is captured:

```python
job_service.set_job_error(
    job_id=job_id,
    error_message="Connection timeout",
    error_traceback=traceback_string
)
```

## Development

### Running Locally

1. Ensure Redis is running (or use Upstash):
```bash
export REDIS_URL=redis://localhost:6379/0
```

2. Start the worker:
```bash
celery -A celery_app worker --loglevel=info
```

3. Start the Flask app:
```bash
python app.py
```

4. Queue a job:
```bash
curl -X POST http://localhost:5000/api/jobs/run-tests \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

5. Check status:
```bash
curl http://localhost:5000/api/jobs/{job_id}
```

## Troubleshooting

### Worker Not Processing Jobs
1. Check Redis connection: `redis-cli PING`
2. Check worker logs for errors
3. Verify REDIS_URL environment variable is set
4. Check that Celery app imports are correct

### Tasks Stuck in "progress"
1. Check worker logs for exceptions
2. Verify database connection is working
3. Check task time limits: CELERY_TASK_TIME_LIMIT

### Job Never Completes
1. Check worker concurrency: `CELERY_CONCURRENCY=2`
2. Verify QA pipeline is not hanging
3. Check worker resource limits (memory, CPU)

## Production Considerations

1. **Multiple Workers**: Scale horizontally by running multiple workers
2. **Monitoring**: Use Celery Flower for web-based monitoring
3. **Persistence**: Results expire after 1 hour (configurable)
4. **Retries**: Failed tasks can be retried via API
5. **Backups**: Job data is persisted in PostgreSQL database

## Monitoring with Flower

Install Flower for web-based monitoring:
```bash
pip install flower
celery -A celery_app flower
```

Access at `http://localhost:5555`
