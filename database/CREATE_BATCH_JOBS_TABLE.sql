-- Batch jobs table for tracking background processing
CREATE TABLE IF NOT EXISTS batch_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    type TEXT NOT NULL,  -- 'analyze', 'export', etc.
    status TEXT DEFAULT 'pending',  -- pending, processing, completed, failed, cancelled
    progress INTEGER DEFAULT 0,
    total_items INTEGER DEFAULT 0,
    processed_items INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    errors JSONB DEFAULT '[]',
    result JSONB,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_batch_jobs_user ON batch_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_batch_jobs_status ON batch_jobs(user_id, status);

ALTER TABLE batch_jobs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can manage own batch jobs" ON batch_jobs;
CREATE POLICY "Users can manage own batch jobs" ON batch_jobs
    FOR ALL USING (auth.uid() = user_id);

