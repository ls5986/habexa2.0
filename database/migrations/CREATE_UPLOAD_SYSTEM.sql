-- Migration: Create Upload System Tables
-- Date: 2025-12-05
-- Purpose: Support large file processing with column mapping, chunked processing, and progress tracking

-- ============================================================================
-- PHASE 1: UPLOAD JOBS MASTER TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS upload_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    supplier_id UUID REFERENCES suppliers(id) ON DELETE SET NULL,
    filename VARCHAR(255) NOT NULL,
    file_size_bytes BIGINT,
    
    -- File storage path (temporary)
    file_path TEXT,
    
    -- Status tracking
    status VARCHAR(50) DEFAULT 'pending',
    -- Values: pending, mapping, validating, processing, complete, failed, cancelled
    
    -- Row counts
    total_rows INTEGER,
    processed_rows INTEGER DEFAULT 0,
    successful_rows INTEGER DEFAULT 0,
    failed_rows INTEGER DEFAULT 0,
    skipped_rows INTEGER DEFAULT 0,
    
    -- Chunk tracking
    chunk_size INTEGER DEFAULT 500,
    total_chunks INTEGER,
    completed_chunks INTEGER DEFAULT 0,
    
    -- Column mapping (stored as JSONB)
    column_mapping JSONB,
    -- Example: {"upc": "Item UPC", "buy_cost": "Wholesale", "pack_size": "Case Qty"}
    
    -- Error tracking
    error_summary JSONB,
    validation_errors JSONB,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- ============================================================================
-- PHASE 2: UPLOAD CHUNKS FOR PARALLEL PROCESSING
-- ============================================================================

CREATE TABLE IF NOT EXISTS upload_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID REFERENCES upload_jobs(id) ON DELETE CASCADE NOT NULL,
    chunk_index INTEGER NOT NULL,
    start_row INTEGER NOT NULL,
    end_row INTEGER NOT NULL,
    
    -- Status
    status VARCHAR(50) DEFAULT 'pending',
    -- Values: pending, queued, processing, complete, failed, cancelled
    
    celery_task_id VARCHAR(255),
    
    -- Progress
    processed_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    
    -- Errors for this chunk
    errors JSONB,
    
    -- Timing
    queued_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    
    UNIQUE(job_id, chunk_index)
);

-- ============================================================================
-- PHASE 3: SAVED COLUMN MAPPINGS PER SUPPLIER
-- ============================================================================

CREATE TABLE IF NOT EXISTS supplier_column_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    supplier_id UUID REFERENCES suppliers(id) ON DELETE CASCADE NOT NULL,
    mapping_name VARCHAR(100),  -- "KEHE Default", "KEHE Promo Format"
    column_mapping JSONB NOT NULL,
    is_default BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id, supplier_id, mapping_name)
);

-- ============================================================================
-- PHASE 4: UPC TO ASIN CACHE
-- ============================================================================

CREATE TABLE IF NOT EXISTS upc_asin_cache (
    upc VARCHAR(14) PRIMARY KEY,
    asin VARCHAR(10),
    not_found BOOLEAN DEFAULT false,
    lookup_count INTEGER DEFAULT 1,
    first_lookup TIMESTAMPTZ DEFAULT NOW(),
    last_lookup TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

-- Upload jobs indexes
CREATE INDEX IF NOT EXISTS idx_upload_jobs_user_status ON upload_jobs(user_id, status);
CREATE INDEX IF NOT EXISTS idx_upload_jobs_created ON upload_jobs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_upload_jobs_supplier ON upload_jobs(supplier_id) WHERE supplier_id IS NOT NULL;

-- Upload chunks indexes
CREATE INDEX IF NOT EXISTS idx_upload_chunks_job_status ON upload_chunks(job_id, status);
CREATE INDEX IF NOT EXISTS idx_upload_chunks_pending ON upload_chunks(status) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_upload_chunks_processing ON upload_chunks(status) WHERE status IN ('queued', 'processing');

-- Supplier mappings indexes
CREATE INDEX IF NOT EXISTS idx_supplier_mappings_lookup ON supplier_column_mappings(user_id, supplier_id);
CREATE INDEX IF NOT EXISTS idx_supplier_mappings_default ON supplier_column_mappings(user_id, supplier_id, is_default) WHERE is_default = true;

-- UPC cache indexes
CREATE INDEX IF NOT EXISTS idx_upc_cache_not_found ON upc_asin_cache(not_found) WHERE not_found = true;
CREATE INDEX IF NOT EXISTS idx_upc_cache_asin ON upc_asin_cache(asin) WHERE asin IS NOT NULL;

-- ============================================================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON TABLE upload_jobs IS 'Master table for file upload jobs with progress tracking';
COMMENT ON TABLE upload_chunks IS 'Individual chunks of rows processed in parallel for large files';
COMMENT ON TABLE supplier_column_mappings IS 'Saved column mappings per supplier for reuse';
COMMENT ON TABLE upc_asin_cache IS 'Cache for UPC to ASIN conversions to avoid repeat API calls';

COMMENT ON COLUMN upload_jobs.status IS 'Job status: pending (created), mapping (awaiting column mapping), validating (checking mapping), processing (chunks running), complete (all done), failed (errors), cancelled (user stopped)';
COMMENT ON COLUMN upload_jobs.column_mapping IS 'JSON mapping of internal fields to file column names: {"upc": "Item UPC", "buy_cost": "Wholesale"}';
COMMENT ON COLUMN upload_chunks.status IS 'Chunk status: pending (not started), queued (in Celery queue), processing (running), complete (done), failed (error), cancelled (job cancelled)';
COMMENT ON COLUMN upc_asin_cache.not_found IS 'True if UPC lookup returned no ASIN (cache negative results)';

