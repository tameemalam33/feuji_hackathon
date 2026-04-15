-- Add AI explanation columns to bugs table for Groq AI integration
-- Stores AI-generated error explanations, causes, and fixes

ALTER TABLE public.saas_bugs
ADD COLUMN IF NOT EXISTS ai_explanation TEXT,
ADD COLUMN IF NOT EXISTS ai_cause TEXT,
ADD COLUMN IF NOT EXISTS ai_suggested_fix TEXT,
ADD COLUMN IF NOT EXISTS ai_raw_response JSONB,
ADD COLUMN IF NOT EXISTS ai_generated_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS ai_model TEXT DEFAULT 'mixtral-8x7b-32768';

-- Create index for queries by ai_generated_at
CREATE INDEX IF NOT EXISTS idx_saas_bugs_ai_generated_at ON public.saas_bugs(ai_generated_at);
