# AutoQA Pro SaaS API Documentation

This document outlines the new SaaS API endpoints for multi-user features, project management, and bug tracking.

## Base URL
```
/api
```

## Authentication

### Session-Based (Web)
All authenticated endpoints require an active session. Sessions are created via login and stored in HTTP-only cookies.

### API Key (CI/External Integrations)
For programmatic access, use the `Authorization: Bearer <api_key>` header.

---

## Authentication Endpoints

### POST /auth/register
Register a new user account.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123",
  "full_name": "John Doe",
  "username": "johndoe"
}
```

**Response (201):**
```json
{
  "message": "User registered successfully",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "username": "johndoe",
    "full_name": "John Doe",
    "role": "tester",
    "is_active": true,
    "created_at": "2025-12-15T10:30:00Z",
    "updated_at": "2025-12-15T10:30:00Z"
  }
}
```

### POST /auth/login
Authenticate with email and password.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response (200):**
```json
{
  "message": "Login successful",
  "user": { ... },
  "session": {
    "user_id": "uuid",
    "user_role": "tester",
    "user_email": "user@example.com",
    "session_token": "...",
    "created_at": "...",
    "expires_at": "..."
  }
}
```

### POST /auth/logout
Logout current user.

**Response (200):**
```json
{
  "message": "Logged out successfully"
}
```

### GET /auth/me
Get current user profile.

**Response (200):**
```json
{
  "user": { ... }
}
```

### PUT /auth/profile
Update user profile.

**Request:**
```json
{
  "full_name": "Jane Doe",
  "username": "janedoe"
}
```

**Response (200):**
```json
{
  "message": "Profile updated successfully",
  "user": { ... }
}
```

### POST /auth/change-password
Change user password.

**Request:**
```json
{
  "current_password": "oldpassword123",
  "new_password": "newpassword456"
}
```

**Response (200):**
```json
{
  "message": "Password changed successfully"
}
```

---

## User Management Endpoints (Admin Only)

### GET /users
List all users (pagination supported).

**Query Parameters:**
- `limit`: Number of users to return (default: 100, max: 1000)
- `offset`: Pagination offset (default: 0)

**Response (200):**
```json
{
  "users": [ ... ],
  "count": 10,
  "limit": 100,
  "offset": 0
}
```

### GET /users/<user_id>
Get user details.

**Response (200):**
```json
{
  "user": { ... }
}
```

### PUT /users/<user_id>/role
Update user role (admin only).

**Request:**
```json
{
  "role": "developer"
}
```

**Response (200):**
```json
{
  "message": "User role updated successfully",
  "user": { ... }
}
```

### PUT /users/<user_id>/status
Enable/disable user account (admin only).

**Request:**
```json
{
  "is_active": true
}
```

**Response (200):**
```json
{
  "message": "User activated successfully",
  "user": { ... }
}
```

---

## Project Management Endpoints

### POST /projects
Create a new project.

**Request:**
```json
{
  "name": "E-Commerce Site",
  "base_url": "https://example-store.com",
  "description": "Test suite for e-commerce platform",
  "is_public": false
}
```

**Response (201):**
```json
{
  "message": "Project created successfully",
  "project": {
    "id": "uuid",
    "name": "E-Commerce Site",
    "base_url": "https://example-store.com",
    "description": "...",
    "owner_id": "uuid",
    "is_public": false,
    "created_at": "...",
    "updated_at": "..."
  }
}
```

### GET /projects
List projects for current user.

**Query Parameters:**
- `limit`: Number of projects (default: 100)
- `offset`: Pagination offset (default: 0)

**Response (200):**
```json
{
  "projects": [ ... ],
  "count": 5,
  "limit": 100,
  "offset": 0
}
```

### GET /projects/<project_id>
Get project details.

**Response (200):**
```json
{
  "project": { ... }
}
```

---

## Task Management Endpoints

### POST /projects/<project_id>/tasks
Create a QA task in a project.

**Request:**
```json
{
  "title": "Test homepage flow",
  "description": "Test user registration flow on homepage",
  "priority": "high",
  "assigned_to": "user-uuid",
  "due_date": "2025-12-31T23:59:59Z"
}
```

**Response (201):**
```json
{
  "message": "Task created successfully",
  "task": {
    "id": "uuid",
    "project_id": "uuid",
    "title": "...",
    "description": "...",
    "created_by": "uuid",
    "assigned_to": "uuid",
    "status": "pending",
    "priority": "high",
    "due_date": "...",
    "created_at": "...",
    "updated_at": "..."
  }
}
```

### GET /projects/<project_id>/tasks
List tasks in a project.

**Query Parameters:**
- `limit`: Number of tasks (default: 100)
- `offset`: Pagination offset (default: 0)

**Response (200):**
```json
{
  "tasks": [ ... ],
  "count": 15,
  "limit": 100,
  "offset": 0
}
```

---

## Bug Tracking Endpoints

### POST /projects/<project_id>/bugs
Report a bug.

**Request:**
```json
{
  "title": "Login button unresponsive",
  "description": "Button doesn't respond to clicks on mobile",
  "severity": "high",
  "page_url": "https://example.com/login",
  "error_message": "TypeError: Cannot read property 'click'",
  "steps_to_reproduce": "1. Go to login page\n2. Tap button",
  "task_id": "task-uuid"
}
```

**Response (201):**
```json
{
  "message": "Bug reported successfully",
  "bug": {
    "id": "uuid",
    "project_id": "uuid",
    "title": "...",
    "description": "...",
    "severity": "high",
    "status": "open",
    "reported_by": "uuid",
    "page_url": "...",
    "error_message": "...",
    "steps_to_reproduce": "...",
    "created_at": "...",
    "updated_at": "..."
  }
}
```

### GET /projects/<project_id>/bugs
List bugs in a project.

**Query Parameters:**
- `limit`: Number of bugs (default: 100)
- `offset`: Pagination offset (default: 0)
- `severity`: Filter by severity (low, medium, high, critical)
- `status`: Filter by status (open, in_progress, resolved, won_t_fix)

**Response (200):**
```json
{
  "bugs": [ ... ],
  "count": 8,
  "total_count": 10,
  "limit": 100,
  "offset": 0
}
```

---

## Report & Analytics Endpoints

### POST /projects/<project_id>/reports
Create a test report.

**Request:**
```json
{
  "title": "Homepage test run",
  "task_id": "task-uuid",
  "total_tests": 25,
  "passed_tests": 23,
  "failed_tests": 2,
  "success_rate": 92.0,
  "test_duration_ms": 5432,
  "report_json": { ... },
  "sqlite_run_id": 123
}
```

**Response (201):**
```json
{
  "message": "Report created successfully",
  "report": {
    "id": "uuid",
    "project_id": "uuid",
    "title": "...",
    "total_tests": 25,
    "passed_tests": 23,
    "failed_tests": 2,
    "success_rate": 92.0,
    "test_duration_ms": 5432,
    "created_at": "...",
    "generated_at": "..."
  }
}
```

### GET /projects/<project_id>/reports
List test reports.

**Query Parameters:**
- `limit`: Number of reports (default: 100)
- `offset`: Pagination offset (default: 0)

**Response (200):**
```json
{
  "reports": [ ... ],
  "count": 12,
  "limit": 100,
  "offset": 0
}
```

---

## SaaS-Integrated QA Endpoints

### POST /projects/<project_id>/run-test
Run QA tests for a project.

**Request:**
```json
{
  "url": "https://example.com",
  "mode": "standard",
  "page_limit": 30,
  "max_depth": 2,
  "task_id": "task-uuid"
}
```

**Response (202):**
```json
{
  "message": "Test started",
  "project_id": "uuid",
  "task_id": "uuid",
  "status": "running"
}
```

### GET /projects/<project_id>/test-status
Get aggregated test statistics.

**Response (200):**
```json
{
  "project_id": "uuid",
  "stats": {
    "total_runs": 15,
    "total_tests": 375,
    "total_passed": 350,
    "total_failed": 25,
    "average_success_rate": 93.33,
    "total_duration_ms": 45000
  }
}
```

---

## Error Responses

### 400 Bad Request
```json
{
  "error": "Invalid request parameter"
}
```

### 401 Unauthorized
```json
{
  "error": "Unauthorized"
}
```

### 403 Forbidden
```json
{
  "error": "Forbidden"
}
```

### 404 Not Found
```json
{
  "error": "Project not found"
}
```

### 500 Internal Server Error
```json
{
  "error": "Internal server error"
}
```

---

## Data Models

### User
```python
{
  "id": UUID,
  "email": str,
  "username": str | null,
  "full_name": str | null,
  "role": "admin" | "tester" | "developer",
  "is_active": bool,
  "created_at": ISO8601,
  "updated_at": ISO8601
}
```

### Project
```python
{
  "id": UUID,
  "name": str,
  "description": str | null,
  "base_url": str,
  "owner_id": UUID,
  "is_public": bool,
  "created_at": ISO8601,
  "updated_at": ISO8601
}
```

### QA Task
```python
{
  "id": UUID,
  "project_id": UUID,
  "title": str,
  "description": str | null,
  "created_by": UUID,
  "assigned_to": UUID | null,
  "status": "pending" | "in_progress" | "completed" | "blocked",
  "priority": "low" | "medium" | "high" | "critical",
  "due_date": ISO8601 | null,
  "created_at": ISO8601,
  "updated_at": ISO8601
}
```

### Bug Report
```python
{
  "id": UUID,
  "project_id": UUID,
  "task_id": UUID | null,
  "title": str,
  "description": str | null,
  "severity": "low" | "medium" | "high" | "critical",
  "status": "open" | "in_progress" | "resolved" | "won_t_fix",
  "reported_by": UUID | null,
  "assigned_to": UUID | null,
  "page_url": str | null,
  "error_message": str | null,
  "steps_to_reproduce": str | null,
  "created_at": ISO8601,
  "updated_at": ISO8601
}
```

### Test Report
```python
{
  "id": UUID,
  "project_id": UUID,
  "task_id": UUID | null,
  "title": str,
  "total_tests": int | null,
  "passed_tests": int | null,
  "failed_tests": int | null,
  "success_rate": float | null,
  "test_duration_ms": int | null,
  "created_at": ISO8601,
  "generated_at": ISO8601
}
```

---

## Environment Variables

Required for SaaS features:
- `DATABASE_URL`: Neon PostgreSQL connection string
- `SECRET_KEY`: Flask session secret key
- `SESSION_COOKIE_SECURE`: Set to `True` for HTTPS (production only)

---

## Testing the API

### Example: Complete Workflow

1. **Register a user:**
```bash
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpass123",
    "full_name": "Test User"
  }'
```

2. **Login:**
```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -c cookies.txt \
  -d '{
    "email": "test@example.com",
    "password": "testpass123"
  }'
```

3. **Create a project:**
```bash
curl -X POST http://localhost:5000/api/projects \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "name": "My Test Project",
    "base_url": "https://example.com"
  }'
```

4. **Create a task:**
```bash
curl -X POST http://localhost:5000/api/projects/{project_id}/tasks \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "title": "Test homepage",
    "priority": "high"
  }'
```

5. **Run tests:**
```bash
curl -X POST http://localhost:5000/api/projects/{project_id}/run-test \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "mode": "standard",
    "task_id": "{task_id}"
  }'
```

---

## Notes

- All timestamps are in ISO 8601 format (UTC)
- UUIDs are used for all resource IDs
- Sessions expire after 24 hours
- Passwords are hashed using bcrypt with 12 rounds
- Row-level security (RLS) is implemented at the database level
