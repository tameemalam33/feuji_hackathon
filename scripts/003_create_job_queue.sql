-- Migration: Add job queue table for background job tracking
-- Purpose: Track Celery task execution status, progress, and results

CREATE TABLE IF NOT EXISTS public.job_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id TEXT NOT NULL UNIQUE,  -- Celery task ID
    task_name TEXT NOT NULL,  -- e.g., 'tasks.run_qa_tests'
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'started', 'progress', 'success', 'failure', 'revoked')),
    user_id UUID,
    project_id UUID,
    task_config_id UUID,
    
    -- Progress tracking
    progress_percent INTEGER DEFAULT 0 CHECK (progress_percent >= 0 AND progress_percent <= 100),
    progress_message TEXT,
    tests_total INTEGER DEFAULT 0,
    tests_completed INTEGER DEFAULT 0,
    tests_passed INTEGER DEFAULT 0,
    tests_failed INTEGER DEFAULT 0,
    
    -- Results storage
    result_data JSONB,  -- Stores test results, metrics, failures
    error_message TEXT,
    error_traceback TEXT,
    
    -- Timing
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,
    
    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,  -- Custom metadata (browser, options, etc.)
    
    FOREIGN KEY (user_id) REFERENCES saas_users(id) ON DELETE SET NULL,
    FOREIGN KEY (project_id) REFERENCES saas_projects(id) ON DELETE CASCADE,
    FOREIGN KEY (task_config_id) REFERENCES saas_qa_tasks(id) ON DELETE SET NULL
);

-- Indexes for efficient querying
CREATE INDEX idx_job_queue_status ON public.job_queue(status);
CREATE INDEX idx_job_queue_user_id ON public.job_queue(user_id);
CREATE INDEX idx_job_queue_project_id ON public.job_queue(project_id);
CREATE INDEX idx_job_queue_task_id ON public.job_queue(task_id);
CREATE INDEX idx_job_queue_created_at ON public.job_queue(created_at DESC);
CREATE INDEX idx_job_queue_status_user ON public.job_queue(status, user_id);

-- View for quick job monitoring
CREATE OR REPLACE VIEW public.job_queue_summary AS
SELECT 
    COUNT(*) as total_jobs,
    COUNT(*) FILTER (WHERE status = 'pending') as pending,
    COUNT(*) FILTER (WHERE status = 'started') as running,
    COUNT(*) FILTER (WHERE status = 'success') as successful,
    COUNT(*) FILTER (WHERE status = 'failure') as failed,
    COUNT(*) FILTER (WHERE status = 'revoked') as revoked,
    AVG(EXTRACT(EPOCH FROM (COALESCE(completed_at, NOW()) - started_at))) as avg_duration_sec
FROM public.job_queue
WHERE created_at > NOW() - INTERVAL '24 hours';
