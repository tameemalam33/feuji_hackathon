# AutoQA Pro SaaS Upgrade Documentation

## Overview

This document describes the SaaS upgrade for AutoQA Pro, transforming it from a standalone QA tool into a multi-user, cloud-based platform with project management, task assignment, and bug tracking.

## Architecture

### Technology Stack

- **Backend:** Flask (Python)
- **Database:** Neon PostgreSQL (replacing SQLite)
- **Authentication:** Session-based + API keys
- **Frontend:** HTML5, CSS3, Vanilla JavaScript

### Database Schema

The upgrade introduces 7 new tables to the PostgreSQL database:

1. **saas_users** - User accounts with roles (admin, tester, developer)
2. **saas_projects** - QA projects owned by users
3. **saas_project_members** - Project team members with role assignments
4. **saas_qa_tasks** - QA test tasks within projects
5. **saas_bugs** - Bug reports with severity tracking
6. **saas_reports** - Test run reports with metrics
7. **saas_report_files** - Report file storage (CSV, PDF, screenshots)

All existing SQLite data remains intact for backward compatibility.

## New Features

### 1. Multi-User Authentication

- **User Registration & Login:** Email/password authentication
- **Role-Based Access Control:** Admin, Tester, Developer roles
- **Session Management:** Secure HTTP-only cookies
- **API Keys:** For CI/CD pipeline integration

**Files:**
- `routes/auth.py` - Authentication endpoints
- `utils/auth.py` - Password hashing, session management
- `templates/login.html` - Login UI
- `templates/register.html` - Registration UI

### 2. Project Management

- **Create & Manage Projects:** Organize tests by application/domain
- **Project Sharing:** Assign team members with different permission levels
- **Base URL Configuration:** Define the application URL to test

**Files:**
- `routes/projects.py` - Project CRUD endpoints
- `templates/projects.html` - Projects dashboard
- `models/saas_models.py` - Project data models

### 3. Task Management

- **QA Tasks:** Create test tasks within projects
- **Task Assignment:** Assign tasks to team members
- **Priority & Status:** Track task progress with priority levels
- **Due Dates:** Set deadlines for test completion

**Integrated into:** `routes/projects.py`

### 4. Bug Tracking

- **Bug Reports:** Report issues found during testing
- **Severity Levels:** Track bug severity (low, medium, high, critical)
- **Error Details:** Capture screenshots, error messages, reproduction steps
- **Status Tracking:** Track bug resolution status

**Files:**
- `routes/bugs.py` - Bug management endpoints
- `services/saas_service.py` - BugService class

### 5. Report & Analytics

- **Test Reports:** Store QA test run results
- **Metrics Tracking:** Capture pass/fail rates, duration, coverage
- **Report Files:** Attach generated reports (CSV, PDF)
- **Historical Data:** Track test trends over time

**Files:**
- `routes/bugs.py` - Report endpoints
- `services/saas_service.py` - ReportService class

### 6. QA Pipeline Integration

- **Seamless Integration:** New SaaS features integrate with existing QA pipeline
- **Automatic Report Generation:** Test runs automatically create SaaS reports
- **Bug Auto-Detection:** Failed tests automatically create bug reports
- **Backward Compatibility:** Existing API endpoints continue to work

**Files:**
- `routes/saas_qa.py` - SaaS-integrated QA endpoints
- `services/saas_qa_integration.py` - Integration layer

## File Structure

```
/vercel/share/v0-project/
├── models/
│   ├── database.py (existing)
│   └── saas_models.py (NEW)
├── routes/
│   ├── api.py (existing)
│   ├── auth.py (NEW)
│   ├── bugs.py (NEW)
│   ├── projects.py (NEW)
│   ├── saas_qa.py (NEW)
│   └── users.py (NEW)
├── services/
│   ├── qa_pipeline.py (existing)
│   ├── saas_service.py (NEW)
│   └── saas_qa_integration.py (NEW)
├── utils/
│   ├── helpers.py (existing)
│   ├── auth.py (NEW)
│   └── integrations.py (existing)
├── templates/
│   ├── base.html (existing)
│   ├── dashboard.html (existing)
│   ├── login.html (NEW)
│   ├── register.html (NEW)
│   ├── projects.html (NEW)
│   └── project_detail.html (NEW - to be created)
├── scripts/
│   └── 001_create_saas_schema.sql (NEW)
├── app.py (UPDATED)
├── config.py (UPDATED)
├── SAAS_API.md (NEW)
└── SAAS_UPGRADE.md (NEW)
```

## Setup Instructions

### 1. Database Migration

The Neon PostgreSQL database is automatically set up during the migration:

```bash
# Execute the migration script
python -m psycopg2 < scripts/001_create_saas_schema.sql
```

Or use the web interface to execute the SQL script.

### 2. Environment Variables

Add these to your `.env` file:

```env
# Database
DATABASE_URL=postgresql://user:password@neon.tech/dbname

# Session
SECRET_KEY=your-secret-key-here
SESSION_COOKIE_SECURE=True  # Set to True in production with HTTPS

# Optional: LLM features (existing)
OPENAI_API_KEY=sk-...
GROQ_API_KEY=gsk-...
```

### 3. Install Dependencies

New Python dependencies required:

```bash
pip install bcrypt  # Password hashing
# Other dependencies already installed
```

### 4. Run the Application

```bash
python app.py
```

The application will:
1. Initialize the database connection
2. Start the Flask server on port 5000
3. Register all route blueprints
4. Serve the SaaS features

### 5. Access the Application

- **Web UI:** http://localhost:5000
- **Register:** http://localhost:5000/register
- **Login:** http://localhost:5000/login
- **Projects:** http://localhost:5000/projects
- **API Docs:** See `SAAS_API.md`

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login user
- `POST /api/auth/logout` - Logout user
- `GET /api/auth/me` - Get current user
- `PUT /api/auth/profile` - Update profile
- `POST /api/auth/change-password` - Change password

### User Management (Admin)
- `GET /api/users` - List users
- `GET /api/users/<id>` - Get user details
- `PUT /api/users/<id>/role` - Update user role
- `PUT /api/users/<id>/status` - Enable/disable user

### Projects
- `POST /api/projects` - Create project
- `GET /api/projects` - List user projects
- `GET /api/projects/<id>` - Get project details

### Tasks
- `POST /api/projects/<id>/tasks` - Create task
- `GET /api/projects/<id>/tasks` - List project tasks

### Bugs & Reports
- `POST /api/projects/<id>/bugs` - Report bug
- `GET /api/projects/<id>/bugs` - List project bugs
- `POST /api/projects/<id>/reports` - Create report
- `GET /api/projects/<id>/reports` - List project reports

### SaaS QA
- `POST /api/projects/<id>/run-test` - Run QA tests (SaaS-aware)
- `GET /api/projects/<id>/test-status` - Get test statistics

See `SAAS_API.md` for full API documentation.

## User Roles

### Admin
- Manage all users
- Access all projects
- Create, view, modify any project
- Full system access

### Developer
- Create and manage projects
- Assign tasks to team members
- View reports and analytics
- Standard project access

### Tester
- Execute QA tests
- Report bugs
- Complete assigned tasks
- View project reports

## Data Security

### Authentication & Authorization
- Passwords hashed with bcrypt (12 rounds)
- Session tokens generated with secrets module
- HTTP-only cookies prevent XSS attacks
- CSRF protection via session validation

### Database Security
- All queries use parameterized statements
- Row-level security (RLS) implemented
- UUID primary keys prevent enumeration
- Sensitive fields excluded from API responses

### API Security
- API key validation for CI/CD endpoints
- Rate limiting ready (implement in production)
- CORS headers for cross-origin requests
- Input validation on all endpoints

## Backward Compatibility

The upgrade maintains full backward compatibility with existing features:

1. **SQLite Data:** Existing test runs remain in SQLite
2. **API Endpoints:** Original QA endpoints continue to work
3. **UI Components:** Existing dashboard pages unchanged
4. **Test Pipeline:** Core test execution logic untouched
5. **Integrations:** External tool integrations still functional

### Migration Path

Users can migrate gradually:
1. Keep using SQLite-based features (existing dashboard, test runner)
2. Adopt SaaS features for new projects (multi-user, team collaboration)
3. Link old test runs to new SaaS projects for unified view
4. Eventually consolidate all tests to PostgreSQL

## Testing

### API Testing

Test the API using curl or Postman:

```bash
# Register
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"pass123"}'

# Login
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -c cookies.txt \
  -d '{"email":"test@example.com","password":"pass123"}'

# Create project
curl -X POST http://localhost:5000/api/projects \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"name":"My Project","base_url":"https://example.com"}'
```

See `SAAS_API.md` for complete API testing guide.

### Unit Tests

Key areas to test:

1. **Authentication**
   - User registration validation
   - Password hashing
   - Login success/failure
   - Session creation

2. **Authorization**
   - Role-based access control
   - Project ownership verification
   - Admin-only endpoints

3. **Data Models**
   - Project CRUD operations
   - Task management
   - Bug reporting
   - Report generation

4. **Integration**
   - QA pipeline + SaaS integration
   - Automatic report creation
   - Bug auto-detection from failures

## Performance Considerations

### Database Optimization
- Indexes created on frequently queried columns
- Pagination implemented for list endpoints
- Connection pooling configured

### Caching Strategy
- Session caching (built-in Flask)
- Project list caching (client-side)
- Report aggregation caching (future improvement)

### Scalability
- Horizontal scaling via multiple app instances
- Database read replicas via Neon
- CDN for static assets
- Async task processing (implemented for test runs)

## Future Enhancements

1. **Advanced Reporting**
   - Custom report templates
   - Scheduled report generation
   - Report sharing & publishing

2. **Collaboration Features**
   - Real-time notifications
   - Team chat integration
   - Code review workflow

3. **Analytics & Insights**
   - Test coverage trends
   - Failure root cause analysis
   - Team performance metrics

4. **Integrations**
   - Slack notifications
   - GitHub/GitLab CI/CD
   - Jira bug sync
   - Email reports

5. **Automation**
   - Scheduled test runs
   - Automated test case generation
   - Smart failure detection

## Troubleshooting

### Database Connection Issues
- Verify `DATABASE_URL` environment variable
- Check Neon PostgreSQL credentials
- Ensure network connectivity to Neon

### Authentication Problems
- Clear browser cookies and try again
- Check `SECRET_KEY` is set correctly
- Verify password meets minimum requirements

### Test Execution Issues
- Check project base URL is valid
- Verify task is assigned correctly
- Review QA pipeline logs for details

### Performance Issues
- Monitor database query times
- Check for N+1 query problems
- Implement caching where needed

## Support

For issues or questions:
1. Check `SAAS_API.md` for API reference
2. Review database schema in `scripts/001_create_saas_schema.sql`
3. Check Flask logs for error details
4. Refer to `models/saas_models.py` for data structures

## Version History

**v2.0.0 - SaaS Upgrade (Current)**
- Multi-user authentication
- Project management
- Task assignment
- Bug tracking
- Test reporting
- QA pipeline integration

**v1.0.0 - Original Release**
- SQLite-based QA tool
- Single-user testing
- Basic reporting
