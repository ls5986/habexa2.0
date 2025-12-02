-- Drop old tables if they exist
DROP TABLE IF EXISTS jobs CASCADE;
DROP TABLE IF EXISTS batch_jobs CASCADE;

-- Create unified jobs table
CREATE TABLE IF NOT EXISTS jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Job info
    type TEXT NOT NULL,  -- 'file_upload', 'batch_analyze', 'single_analyze', 'telegram_sync', 'export'
    status TEXT DEFAULT 'pending',  -- pending, processing, completed, failed, cancelled
    
    -- Progress
    progress INTEGER DEFAULT 0,
    total_items INTEGER DEFAULT 0,
    processed_items INTEGER DEFAULT 0,
    
    -- Results
    success_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    errors JSONB DEFAULT '[]',
    result JSONB,
    
    -- Metadata
    metadata JSONB,  -- Store job-specific data (filename, supplier_id, etc.)
    
    -- Timestamps
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_jobs_user ON jobs(user_id);
CREATE INDEX idx_jobs_status ON jobs(user_id, status);
CREATE INDEX idx_jobs_type ON jobs(user_id, type);
CREATE INDEX idx_jobs_created ON jobs(created_at DESC);

-- RLS
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own jobs" ON jobs
    FOR ALL USING (auth.uid() = user_id);

