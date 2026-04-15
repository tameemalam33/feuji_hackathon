-- AutoQA Pro SaaS Schema Migration
-- Creates tables for user management, projects, tasks, and reports
-- Keeps existing SQLite runs data intact for backward compatibility

-- Users table
CREATE TABLE IF NOT EXISTS public.saas_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL UNIQUE,
    username TEXT UNIQUE,
    full_name TEXT,
    password_hash TEXT,
    role TEXT NOT NULL DEFAULT 'tester' CHECK (role IN ('admin', 'tester', 'developer')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Projects table
CREATE TABLE IF NOT EXISTS public.saas_projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    description TEXT,
    base_url TEXT NOT NULL,
    owner_id UUID NOT NULL REFERENCES public.saas_users(id) ON DELETE CASCADE,
    is_public BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Project members (for sharing projects with team members)
CREATE TABLE IF NOT EXISTS public.saas_project_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES public.saas_projects(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.saas_users(id) ON DELETE CASCADE,
    role TEXT NOT NULL DEFAULT 'tester' CHECK (role IN ('owner', 'editor', 'viewer')),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(project_id, user_id)
);

-- QA Tasks (scoped to projects)
CREATE TABLE IF NOT EXISTS public.saas_qa_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES public.saas_projects(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    created_by UUID NOT NULL REFERENCES public.saas_users(id) ON DELETE SET NULL,
    assigned_to UUID REFERENCES public.saas_users(id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'blocked')),
    priority TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'critical')),
    due_date TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Bug Reports (from QA runs)
CREATE TABLE IF NOT EXISTS public.saas_bugs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES public.saas_qa_tasks(id) ON DELETE SET NULL,
    project_id UUID NOT NULL REFERENCES public.saas_projects(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    severity TEXT NOT NULL DEFAULT 'medium' CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'in_progress', 'resolved', 'won_t_fix')),
    reported_by UUID REFERENCES public.saas_users(id) ON DELETE SET NULL,
    assigned_to UUID REFERENCES public.saas_users(id) ON DELETE SET NULL,
    screenshot_url TEXT,
    page_url TEXT,
    error_message TEXT,
    steps_to_reproduce TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Test Reports (linked to SQLite runs via run_id or batch_id)
CREATE TABLE IF NOT EXISTS public.saas_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES public.saas_projects(id) ON DELETE CASCADE,
    task_id UUID REFERENCES public.saas_qa_tasks(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    sqlite_run_id INTEGER,
    sqlite_batch_id TEXT,
    report_json JSONB,
    total_tests INTEGER,
    passed_tests INTEGER,
    failed_tests INTEGER,
    success_rate REAL,
    test_duration_ms INTEGER,
    generated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Report files (CSV, PDF, screenshots)
CREATE TABLE IF NOT EXISTS public.saas_report_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id UUID NOT NULL REFERENCES public.saas_reports(id) ON DELETE CASCADE,
    file_type TEXT NOT NULL CHECK (file_type IN ('csv', 'pdf', 'screenshot', 'log')),
    file_path TEXT NOT NULL,
    file_name TEXT NOT NULL,
    file_size_bytes INTEGER,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_saas_projects_owner_id ON public.saas_projects(owner_id);
CREATE INDEX IF NOT EXISTS idx_saas_project_members_project_id ON public.saas_project_members(project_id);
CREATE INDEX IF NOT EXISTS idx_saas_project_members_user_id ON public.saas_project_members(user_id);
CREATE INDEX IF NOT EXISTS idx_saas_qa_tasks_project_id ON public.saas_qa_tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_saas_qa_tasks_assigned_to ON public.saas_qa_tasks(assigned_to);
CREATE INDEX IF NOT EXISTS idx_saas_bugs_project_id ON public.saas_bugs(project_id);
CREATE INDEX IF NOT EXISTS idx_saas_bugs_severity ON public.saas_bugs(severity);
CREATE INDEX IF NOT EXISTS idx_saas_bugs_status ON public.saas_bugs(status);
CREATE INDEX IF NOT EXISTS idx_saas_reports_project_id ON public.saas_reports(project_id);
CREATE INDEX IF NOT EXISTS idx_saas_report_files_report_id ON public.saas_report_files(report_id);


