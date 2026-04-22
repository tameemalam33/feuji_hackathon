# AutoQA Pro - System Architecture

## High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           USER INTERFACE                                 │
│                         Flask Web Templates                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐   │
│  │ Dashboard│  │ Projects │  │  Login   │  │ Job Progress Monitor │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────────┬───────────┘   │
└───────┼─────────────┼─────────────┼────────────────────┼────────────────┘
        │             │             │                    │
        └─────────────┴─────────────┴────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         FLASK API LAYER                                  │
│         (50+ Endpoints Across 10 Route Modules)                          │
│                                                                          │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐                   │
│  │  Auth APIs  │  │ Project APIs │  │   Bug APIs   │                   │
│  │  (5 routes) │  │  (7 routes)  │  │  (5 routes)  │                   │
│  └─────────────┘  └──────────────┘  └──────────────┘                   │
│                                                                          │
│  ┌────────────────┐  ┌───────────────┐  ┌──────────────────┐           │
│  │  Job Queue APIs│  │   AI APIs     │  │  Monitoring APIs │           │
│  │  (6 routes)    │  │  (7 routes)   │  │  (4 routes)      │           │
│  └─────┬──────────┘  └───────┬───────┘  └────────┬─────────┘           │
└────────┼──────────────────────┼─────────────────────┼────────────────────┘
         │                      │                     │
         │ Queues jobs          │ Analyzes errors     │ Monitors health
         │                      │                     │
         ▼                      ▼                     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                    BUSINESS LOGIC LAYER (Services)                        │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ QA Pipeline Service                                              │    │
│  │ ├─ Crawler (discover pages)                                     │    │
│  │ ├─ Test Generator (create tests)                                │    │
│  │ ├─ Test Executor (run tests)                                    │    │
│  │ └─ Report Generator (create reports)                            │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ Celery Task Service (NEW)                                        │    │
│  │ ├─ run_qa_tests (queue test execution)                          │    │
│  │ ├─ run_task_tests (queue task-specific tests)                   │    │
│  │ └─ generate_report (create reports asynchronously)              │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ Job Status Service (NEW)                                         │    │
│  │ ├─ Create job record                                             │    │
│  │ ├─ Update progress                                               │    │
│  │ ├─ Store results                                                 │    │
│  │ └─ Retrieve status                                               │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ Groq AI Service (NEW)                                            │    │
│  │ ├─ analyzeError()                                                │    │
│  │ ├─ analyze_test_failure()                                        │    │
│  │ ├─ analyze_performance_issue()                                   │    │
│  │ └─ batch_explain_errors()                                        │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ SaaS Service Layer                                               │    │
│  │ ├─ UserService (auth, profiles)                                 │    │
│  │ ├─ ProjectService (projects, members)                           │    │
│  │ ├─ TaskService (QA tasks)                                       │    │
│  │ └─ BugService (bug tracking)                                    │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────┘
         │                     │                    │
         ▼                     ▼                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                     INFRASTRUCTURE LAYER                                  │
│                                                                           │
│  ┌────────────────────┐  ┌──────────────────┐  ┌────────────────────┐  │
│  │  PostgreSQL (Neon) │  │  Redis (Upstash) │  │   Groq API         │  │
│  │                    │  │                  │  │                    │  │
│  │ ├─ saas_users      │  │ ├─ Job Queue     │  │ ├─ llama3-8b-8192  │  │
│  │ ├─ saas_projects   │  │ ├─ Task Storage  │  │ └─ Error Analysis  │  │
│  │ ├─ saas_tasks      │  │ └─ Results       │  │                    │  │
│  │ ├─ saas_bugs       │  │                  │  │ (Groq API)         │  │
│  │ ├─ saas_reports    │  │ (Redis)          │  └────────────────────┘  │
│  │ └─ job_queue       │  │                  │                           │
│  │                    │  │ (In-Memory +     │                           │
│  │ (Persistent Data)  │  │  Persistent)     │                           │
│  └────────────────────┘  └──────────────────┘                           │
│                                                                           │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │ Celery Workers (Separate Processes)                               │  │
│  │                                                                    │  │
│  │ Worker 1: Processes job_queue tasks                               │  │
│  │ ├─ Executes QA pipeline                                           │  │
│  │ ├─ Updates job progress in PostgreSQL                             │  │
│  │ ├─ Stores results                                                 │  │
│  │ └─ Optionally calls Groq for AI analysis                          │  │
│  │                                                                    │  │
│  │ Worker 2-N: Additional workers for parallelization                │  │
│  │ (Configured via CELERY_CONCURRENCY)                               │  │
│  │                                                                    │  │
│  │ (Can run on same host or different servers)                       │  │
│  └────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Request Flow: Queuing a Test

```
1. USER
   └─→ POST /api/jobs/run-tests
       {base_url, crawl_mode, page_limit}
       
2. API LAYER
   └─→ routes/job_api.py
       ├─ Validate input
       ├─ Create JobStatus record in PostgreSQL
       ├─ Queue Celery task to Redis
       └─ Return: {job_id, status: "queued"}
       
3. IMMEDIATE RESPONSE (100ms)
   ✓ User gets job_id immediately
   ✓ API not blocked
   
4. BACKGROUND PROCESSING (in parallel)
   Redis → Celery Worker picks up task
   ├─ Execute QA Pipeline
   │  ├─ Crawl website
   │  ├─ Generate tests
   │  ├─ Run tests
   │  └─ Capture results
   │
   ├─ Update Progress in PostgreSQL
   │  └─ job_queue.progress_percentage
   │  └─ job_queue.progress_message
   │
   ├─ (Optional) Call Groq AI
   │  └─ Analyze errors
   │  └─ Store explanations in saas_bugs
   │
   └─ Store Results in PostgreSQL
      └─ job_queue.result (JSON)
      └─ job_queue.status = "completed"
      
5. USER POLLS FOR STATUS
   GET /api/jobs/{job_id}
   └─ Returns: {status, progress, message, result}
   
6. USER GETS RESULTS
   ✓ All data persisted in PostgreSQL
   ✓ Accessible via API anytime
```

---

## Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        API REQUEST FLOW                                  │
│                                                                          │
│  POST /api/jobs/run-tests                                               │
│         │                                                                │
│         ▼                                                                │
│  ┌────────────────────────────────────────────────────┐                │
│  │ Flask Route Handler (job_api.py)                   │                │
│  │ ├─ Validate request                                │                │
│  │ ├─ Create job record in PostgreSQL                 │                │
│  │ ├─ Queue Celery task to Redis                      │                │
│  │ └─ Return job_id immediately                       │                │
│  └────────────────────────────────────────────────────┘                │
│                                                                          │
│  ✓ Response time: < 100ms                                               │
│  ✓ No blocking                                                           │
│  ✓ No waiting for tests                                                  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                    BACKGROUND JOB EXECUTION FLOW                          │
│                                                                          │
│  Redis (Upstash)                                                         │
│  └─ Contains: Celery task queue                                          │
│              {task_id, function, args, kwargs}                           │
│                                                                          │
│  Celery Worker (Separate Python Process)                                 │
│  ├─ Connects to Redis broker                                             │
│  ├─ Polls for available tasks                                            │
│  └─ Executes task:                                                       │
│     │                                                                    │
│     ├─ Task: run_qa_tests(base_url, crawl_mode, ...)                     │
│     │  │                                                                 │
│     │  ├─ Start: Update job_queue.status = "started"                     │
│     │  │         Store job_queue.started_at                              │
│     │  │                                                                 │
│     │  ├─ Progress: Update regularly                                     │
│     │  │  └─ job_queue.progress_percentage = 25                          │
│     │  │  └─ job_queue.progress_message = "Testing page 3/10"            │
│     │  │                                                                 │
│     │  ├─ Execution: QA Pipeline                                         │
│     │  │  ├─ Crawler.discover_pages()                                    │
│     │  │  ├─ TestGenerator.generate_tests()                              │
│     │  │  ├─ TestExecutor.run_tests()                                    │
│     │  │  └─ ReportGenerator.create_report()                             │
│     │  │                                                                 │
│     │  ├─ Optional: AI Analysis                                          │
│     │  │  └─ GroqAIService.analyzeError(error_message)                   │
│     │  │     └─ Returns: {explanation, cause, fix}                       │
│     │  │     └─ Stored in saas_bugs table                                │
│     │  │                                                                 │
│     │  └─ Complete: Update job_queue.status = "completed"                │
│     │            Store job_queue.result = {results_json}                 │
│     │            Store job_queue.completed_at                            │
│     │                                                                    │
│     └─ Error handling:                                                   │
│        ├─ Catch exceptions                                               │
│        ├─ Store in job_queue.error                                       │
│        ├─ Store traceback in job_queue.error_traceback                   │
│        └─ Set job_queue.status = "failed"                                │
│                                                                          │
│  PostgreSQL (Neon) Database                                              │
│  └─ Persistent storage for:                                              │
│     ├─ job_queue: Job tracking                                           │
│     ├─ saas_bugs: Bug reports + AI analysis                              │
│     ├─ saas_reports: Test results                                        │
│     └─ saas_projects, saas_tasks, saas_users: SaaS data                  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                       USER STATUS POLLING FLOW                            │
│                                                                          │
│  GET /api/jobs/{job_id}                                                  │
│         │                                                                │
│         ▼                                                                │
│  ┌────────────────────────────────────────────────────┐                │
│  │ Flask Route Handler (job_api.py)                   │                │
│  │ ├─ Query PostgreSQL for job record                 │                │
│  │ ├─ Extract: status, progress, progress_message     │                │
│  │ ├─ If completed: include result JSON               │                │
│  │ └─ Return to user                                  │                │
│  └────────────────────────────────────────────────────┘                │
│                                                                          │
│  Response Examples:                                                      │
│                                                                          │
│  Status: "queued"                                                        │
│  {                                                                       │
│    "id": "abc123",                                                       │
│    "status": "queued",                                                   │
│    "progress": 0,                                                        │
│    "message": "Waiting for worker"                                       │
│  }                                                                       │
│                                                                          │
│  Status: "running"                                                       │
│  {                                                                       │
│    "id": "abc123",                                                       │
│    "status": "running",                                                  │
│    "progress": 45,                                                       │
│    "message": "Testing page 5 of 10"                                     │
│  }                                                                       │
│                                                                          │
│  Status: "completed"                                                     │
│  {                                                                       │
│    "id": "abc123",                                                       │
│    "status": "completed",                                                │
│    "progress": 100,                                                      │
│    "result": {                                                           │
│      "pages_tested": 10,                                                 │
│      "tests_passed": 45,                                                 │
│      "tests_failed": 2,                                                  │
│      "duration": "5m 32s"                                                │
│    }                                                                     │
│  }                                                                       │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Component Interaction Diagram

```
                         ┌─────────────────────┐
                         │   User Dashboard    │
                         │  (Flask Templates)  │
                         └──────────┬──────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
                    ▼               ▼               ▼
              ┌──────────┐   ┌──────────┐   ┌──────────┐
              │ POST     │   │ GET      │   │ DELETE   │
              │ /api/... │   │ /api/... │   │ /api/... │
              └────┬─────┘   └────┬─────┘   └────┬─────┘
                   │              │              │
                   └──────────────┼──────────────┘
                                  │
                    ┌─────────────▼──────────────┐
                    │   Flask API Layer          │
                    │   (Routes & Auth)          │
                    └─────────────┬──────────────┘
                                  │
                ┌─────────────────┼─────────────────┐
                │                 │                 │
                ▼                 ▼                 ▼
        ┌────────────────┐ ┌────────────────┐ ┌─────────────┐
        │ Service Layer  │ │ Database Layer │ │ Async Queue │
        │                │ │                │ │             │
        │┌──────────────┐│ │┌──────────────┐│ │┌──────────┐ │
        ││QA Pipeline  ││ ││PostgreSQL    ││ ││ Celery   │ │
        │└──────────────┘│ ││ (Neon)       ││ ││ + Redis  │ │
        │┌──────────────┐│ ││              ││ │└──────────┘ │
        ││Job Status   ││ ││ Tables:      ││ │             │
        │└──────────────┘│ ││ - saas_users ││ │┌──────────┐ │
        │┌──────────────┐│ ││ - saas_jobs  ││ ││ Workers  │ │
        ││Groq AI      ││ ││ - saas_bugs  ││ │└──────────┘ │
        │└──────────────┘│ ││ - saas_tasks ││ │             │
        │┌──────────────┐│ ││ - saas_reports││ └─────────────┘
        ││SaaS Logic   ││ │└──────────────┘│
        │└──────────────┘│ │                │
        └────────────────┘ └────────────────┘
```

---

## Scaling Architecture

```
Single Server (Development)
┌─────────────────────────────────────────────────┐
│                    1 Host                        │
│ ┌──────────────────────────────────────────┐   │
│ │ Flask App (port 5000)                    │   │
│ │ + Celery Worker (same process)           │   │
│ └──────────────────────────────────────────┘   │
│ ├─ PostgreSQL (local or Neon)                   │
│ └─ Redis (local or Upstash)                     │
└─────────────────────────────────────────────────┘


Multiple Servers (Production)
┌──────────────────────────────────────────────────────────────┐
│                  Server 1: Web API                           │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ Flask Application                                      │  │
│ │ ├─ Handles API requests (fast)                         │  │
│ │ └─ Queues jobs to Redis                                │  │
│ └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
                          │
                ┌─────────┴──────────┐
                │                    │
┌──────────────────────────────┐  ┌──────────────────────────────┐
│  Server 2: Worker Pool       │  │  Server 3: Worker Pool       │
│ ┌────────────────────────────┐│  │ ┌────────────────────────────┐│
│ │ Celery Worker 1            ││  │ │ Celery Worker 3            ││
│ │ ├─ Executes QA pipeline    ││  │ │ ├─ Executes QA pipeline    ││
│ │ └─ Updates job progress    ││  │ │ └─ Updates job progress    ││
│ ├────────────────────────────┤│  │ ├────────────────────────────┤│
│ │ Celery Worker 2            ││  │ │ Celery Worker 4            ││
│ │ ├─ Executes QA pipeline    ││  │ │ ├─ Executes QA pipeline    ││
│ │ └─ Updates job progress    ││  │ │ └─ Updates job progress    ││
│ └────────────────────────────┘│  │ └────────────────────────────┘│
└──────────────────────────────────┘  └──────────────────────────────┘
                │                              │
                └──────────────┬───────────────┘
                               │
                ┌──────────────┴──────────────┐
                │                             │
        ┌──────▼──────────┐          ┌───────▼────────┐
        │ Redis (Upstash) │          │ PostgreSQL     │
        │                 │          │ (Neon)         │
        │ Job Queue       │          │                │
        │ Task Storage    │          │ Persistent     │
        │ Results         │          │ Data           │
        └─────────────────┘          └────────────────┘
```

---

## Technology Stack Visualization

```
Frontend Tier
│
├─ HTML/CSS/JavaScript
├─ Jinja2 Templates
└─ Flask Static Files

Application Tier
│
├─ Flask 3.0+ (Web Framework)
├─ Blueprints (Route Organization)
├─ Sessions (Authentication)
└─ Middleware (Request Processing)

Business Logic Tier
│
├─ QA Pipeline Service
├─ Celery Tasks
├─ Job Status Service
├─ Groq AI Service
└─ SaaS Services (User, Project, Task, Bug)

Data Persistence Tier
│
├─ PostgreSQL (Neon) - Primary
│  └─ 8 tables: users, projects, tasks, bugs, reports, jobs, etc.
│
├─ Redis (Upstash) - Message Broker
│  └─ Celery task queue and results
│
└─ SQLite (Legacy) - Backward Compatibility
   └─ Original test history

Integration Tier
│
└─ Groq API (LLM for error analysis)
```

---

## Security Architecture

```
Request Entry
     │
     ▼
  ┌─────────────┐
  │ SSL/TLS     │ ← HTTPS enforced
  └──────┬──────┘
         │
         ▼
  ┌──────────────────┐
  │ Request Validation│ ← Input validation, CSRF
  └──────┬───────────┘
         │
         ▼
  ┌──────────────────┐
  │ Authentication   │ ← Session check or API key
  │ (Session/APIKey) │
  └──────┬───────────┘
         │
         ▼
  ┌──────────────────┐
  │ Authorization    │ ← Role-based access
  │ (Role Check)     │
  └──────┬───────────┘
         │
         ▼
  ┌──────────────────┐
  │ Parameterized    │ ← SQL Injection prevention
  │ Queries          │
  └──────┬───────────┘
         │
         ▼
  ┌──────────────────┐
  │ Password Hashing │ ← bcrypt for stored passwords
  │ (bcrypt)         │
  └──────┬───────────┘
         │
         ▼
  ┌──────────────────┐
  │ HTTP-only Cookies│ ← No JavaScript access
  │ + Secure Flag    │
  └──────┬───────────┘
         │
         ▼
  Response Returned
```

---

This architecture supports:
- ✅ Scalability (horizontal scaling of workers)
- ✅ Reliability (persistent data storage)
- ✅ Performance (asynchronous job processing)
- ✅ Security (layered authentication and authorization)
- ✅ Maintainability (clear separation of concerns)
- ✅ Extensibility (easy to add new services/endpoints)
