-- Create table for storing UPC → ASIN selections
-- Allows users to save their ASIN choice for a UPC to auto-use on future uploads

CREATE TABLE IF NOT EXISTS public.upc_asin_selections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    upc VARCHAR(20) NOT NULL,
    asin VARCHAR(20) NOT NULL,
    alternative_asins TEXT[] DEFAULT '{}',
    selected_at TIMESTAMP WITH TIME ZONE NOT NULL,
    selection_count INTEGER DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(user_id, upc)  -- One selection per user per UPC
);

-- Index for fast lookups
CREATE INDEX IF NOT EXISTS idx_upc_asin_selections_user_upc ON public.upc_asin_selections(user_id, upc);

-- RLS policies
ALTER TABLE public.upc_asin_selections ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own selections" ON public.upc_asin_selections
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own selections" ON public.upc_asin_selections
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own selections" ON public.upc_asin_selections
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own selections" ON public.upc_asin_selections
    FOR DELETE USING (auth.uid() = user_id);

