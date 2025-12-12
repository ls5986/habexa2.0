-- ============================================================================
-- UPLOAD JOBS TABLE - Enterprise File Processing
-- ============================================================================
-- Track file upload progress for 50k+ product uploads.

-- Drop existing table if it exists
DROP TABLE IF EXISTS upload_jobs CASCADE;

-- Create upload jobs table
CREATE TABLE upload_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    
    -- File info
    filename VARCHAR(500) NOT NULL,
    file_path TEXT,
    file_size_bytes BIGINT,
    total_rows INTEGER,
    
    -- Progress tracking
    status VARCHAR(50) DEFAULT 'pending',
    -- 'pending', 'parsing', 'converting_upcs', 'inserting', 
    -- 'fetching_api', 'complete', 'failed', 'cancelled'
    
    current_phase VARCHAR(100),
    processed_rows INTEGER DEFAULT 0,
    successful_rows INTEGER DEFAULT 0,
    failed_rows INTEGER DEFAULT 0,
    
    -- Performance metrics
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    duration_seconds INTEGER,
    
    -- Results
    products_created INTEGER DEFAULT 0,
    api_calls_made INTEGER DEFAULT 0,
    cache_hits INTEGER DEFAULT 0,
    
    -- Error tracking
    error_summary JSONB,
    failed_rows_details JSONB,
    
    -- Template info (if used)
    supplier_id UUID REFERENCES suppliers(id) ON DELETE SET NULL,
    template_id UUID REFERENCES supplier_templates(id) ON DELETE SET NULL,
    template_applied BOOLEAN DEFAULT false,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for fast queries
CREATE INDEX idx_upload_jobs_user ON upload_jobs(user_id);
CREATE INDEX idx_upload_jobs_status ON upload_jobs(status);
CREATE INDEX idx_upload_jobs_created ON upload_jobs(created_at DESC);

-- Enable RLS (Row Level Security)
ALTER TABLE upload_jobs ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Users can view their own upload jobs" ON upload_jobs;
DROP POLICY IF EXISTS "Users can create their own upload jobs" ON upload_jobs;
DROP POLICY IF EXISTS "Users can update their own upload jobs" ON upload_jobs;
DROP POLICY IF EXISTS "Users can delete their own upload jobs" ON upload_jobs;

-- RLS Policies
CREATE POLICY "Users can view their own upload jobs"
    ON upload_jobs FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can create their own upload jobs"
    ON upload_jobs FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own upload jobs"
    ON upload_jobs FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own upload jobs"
    ON upload_jobs FOR DELETE
    USING (auth.uid() = user_id);

-- Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON upload_jobs TO authenticated;

-- Comments
COMMENT ON TABLE upload_jobs IS 'Track file upload progress for enterprise file processing';
COMMENT ON COLUMN upload_jobs.status IS 'Current processing status';
COMMENT ON COLUMN upload_jobs.current_phase IS 'Human-readable phase description';
COMMENT ON COLUMN upload_jobs.cache_hits IS 'Number of UPC lookups served from cache';
COMMENT ON COLUMN upload_jobs.api_calls_made IS 'Number of API calls made (SP-API + Keepa)';

