# Celery Background Job Integration - Summary

## What Was Implemented

The AutoQA Pro system has been refactored to use **Celery** with **Redis** (Upstash) for asynchronous processing of long-running QA tests.

### Key Features

✓ **Asynchronous Job Queueing** - Tests run in background without blocking API
✓ **Real-time Progress Tracking** - Monitor test execution via progress updates
✓ **Job Management** - Queue, cancel, and track job status
✓ **Error Handling** - Capture and log failures with full tracebacks
✓ **Admin Monitoring** - Dashboard for queue health and statistics
✓ **Scalable Architecture** - Multiple workers can process jobs in parallel

## Components Added

### Files Created

| File | Purpose |
|------|---------|
| `celery_app.py` | Celery application configuration |
| `services/job_status.py` | Database service for job tracking |
| `services/celery_tasks.py` | Celery task definitions for QA operations |
| `routes/job_api.py` | API endpoints for job management (queue, status, list, cancel) |
| `routes/job_monitoring.py` | Admin/monitoring endpoints for queue health and statistics |
| `utils/celery_worker.py` | Worker startup and management utilities |
| `scripts/003_create_job_queue.sql` | Database schema for job tracking |
| `CELERY_SETUP.md` | Comprehensive setup and configuration guide |
| `CELERY_EXAMPLES.md` | Complete usage examples with code samples |
| `CELERY_INTEGRATION_SUMMARY.md` | This file |

### Database Changes

New `job_queue` table with:
- Job ID tracking (maps to Celery task ID)
- Status tracking (queued, started, progress, completed, failed)
- Progress percentage and messages
- Result storage (JSON)
- Error capture with tracebacks
- Performance metrics (duration)
- Indexes for efficient queries

### API Endpoints Added

#### Job Operations
- `POST /api/jobs/run-tests` - Queue public API test run
- `POST /api/jobs/projects/{id}/run-tests` - Queue project tests
- `POST /api/jobs/tasks/{id}/run-tests` - Queue task tests
- `GET /api/jobs/{id}` - Get job status and progress
- `GET /api/jobs` - List user's jobs
- `DELETE /api/jobs/{id}` - Cancel a job

#### Monitoring
- `GET /api/monitoring/jobs/stats` - Queue statistics
- `GET /api/monitoring/jobs/recent` - Recent completed/failed jobs
- `GET /api/monitoring/jobs/queue-health` - Queue health status
- `POST /api/monitoring/jobs/cleanup` - Admin: cleanup old jobs

## Configuration

### Required Environment Variables

```bash
# Automatic (set by Vercel when Upstash connected)
REDIS_URL=redis://...

# Optional
CELERY_CONCURRENCY=2              # Worker concurrency
CELERY_TASK_TIME_LIMIT=1800       # 30 minute hard limit
CELERY_TASK_SOFT_TIME_LIMIT=1500  # 25 minute soft limit
```

### Installation

Dependencies already added to `requirements.txt`:
```
celery>=5.3.0
redis>=5.0.0
```

## Starting the System

### 1. Start the Worker (Required)

```bash
# Using provided utility
python -m utils.celery_worker

# Or with Celery directly
celery -A celery_app worker --loglevel=info --concurrency=2
```

### 2. Start the Flask API

```bash
python app.py
```

The worker and API must both be running for the system to function.

## Usage Examples

### Queue a Test Run

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

Response:
```json
{
  "job_id": "abc123...",
  "status": "queued",
  "message": "Test run queued successfully"
}
```

### Check Job Status

```bash
curl http://localhost:5000/api/jobs/abc123...
```

Response:
```json
{
  "job_id": "abc123...",
  "status": "progress",
  "progress": 45,
  "progress_message": "Running tests on page 15/50",
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Polling Example (Python)

```python
import requests
import time

job_id = "abc123..."

while True:
    response = requests.get(f"http://localhost:5000/api/jobs/{job_id}")
    job = response.json()
    
    print(f"Status: {job['status']} | Progress: {job.get('progress', 0)}%")
    
    if job['status'] in ['completed', 'failed']:
        print(f"Result: {job.get('result', {})}")
        break
    
    time.sleep(2)
```

See `CELERY_EXAMPLES.md` for complete examples in Python and JavaScript.

## Job Status Flow

```
User queues test
    ↓
POST /api/jobs/run-tests
    ↓
Task created in Celery
    ↓
Job record in database (status: queued)
    ↓
Worker picks up task
    ↓
Status updated to "started" (progress: 5%)
    ↓
Tests run, progress updated periodically
    ↓
Tests complete or fail
    ↓
Status updated to "completed" or "failed"
    ↓
Result/error stored in database
    ↓
Job available for retrieval via GET /api/jobs/{id}
```

## Architecture Diagram

```
┌─────────────────┐
│   Flask API     │
│  (request)      │
└────────┬────────┘
         │
         ├──→ POST /api/jobs/run-tests
         │
         └──→ Task queued to Redis
                 │
         ┌───────┴────────┐
         │                │
    ┌────▼─────┐   ┌─────▼───┐
    │  Celery  │   │    Job   │
    │  Worker  │   │  Queue   │
    │ (task)   │   │  (Redis) │
    └────┬─────┘   └──────────┘
         │
    ┌────▼──────────┐
    │  PostgreSQL   │
    │  job_queue    │
    │  table        │
    └──────────────┘
         │
    ┌────▼──────────────┐
    │  Frontend polls   │
    │  GET /jobs/{id}   │
    └───────────────────┘
```

## Performance Characteristics

### Without Celery (Blocking)
```
Request → QA Pipeline (60-300s) → Response
Browser waits for completion
```

### With Celery (Async)
```
Request → Queue task (0.1s) → Response with job_id
Browser: Poll /api/jobs/{id} every 2s
Worker: Process task in background
```

**Result:** API responds immediately, prevents timeout, better UX.

## Monitoring

### Admin Dashboard Endpoints

```bash
# Queue stats
curl http://localhost:5000/api/monitoring/jobs/stats \
  -H "Authorization: Bearer ADMIN_TOKEN"

# Queue health
curl http://localhost:5000/api/monitoring/jobs/queue-health \
  -H "Authorization: Bearer ADMIN_TOKEN"

# Recent jobs
curl http://localhost:5000/api/monitoring/jobs/recent?hours=24 \
  -H "Authorization: Bearer ADMIN_TOKEN"

# Cleanup old jobs
curl -X POST http://localhost:5000/api/monitoring/jobs/cleanup \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -d '{"days": 7}'
```

## Troubleshooting

### Worker Not Processing Tasks

1. **Check Redis Connection:**
   ```bash
   redis-cli PING
   # Should return PONG
   ```

2. **Verify REDIS_URL:**
   ```bash
   echo $REDIS_URL
   # Should show valid Redis URL
   ```

3. **Check Worker Logs:**
   ```bash
   # Look for connection errors or task exceptions
   ```

### Tasks Stuck in "progress"

1. Check worker hasn't crashed
2. Verify QA pipeline isn't hanging
3. Check CELERY_TASK_TIME_LIMIT setting

### Job Never Completes

1. Increase timeout on client polling
2. Check database connectivity
3. Review worker error logs

## Next Steps

1. **Deploy:** Push changes to production
2. **Test:** Queue a test run and verify status polling
3. **Monitor:** Watch queue health in /api/monitoring endpoints
4. **Scale:** Increase CELERY_CONCURRENCY as needed

## Backward Compatibility

The old synchronous endpoints (`/api/run-full-test`) still work but are deprecated. New code should use:
- `/api/jobs/run-tests` for public API
- `/api/jobs/projects/{id}/run-tests` for SaaS projects
- `/api/jobs/tasks/{id}/run-tests` for specific tasks

## Documentation

- **CELERY_SETUP.md** - Complete setup, configuration, and API reference
- **CELERY_EXAMPLES.md** - Code examples in Python, JavaScript, Bash, and Postman
- **CELERY_INTEGRATION_SUMMARY.md** - This overview document

## Support

For issues or questions:
1. Check CELERY_SETUP.md troubleshooting section
2. Review CELERY_EXAMPLES.md for implementation patterns
3. Check worker logs for detailed error messages
4. Verify Redis connectivity and database schema
