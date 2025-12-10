-- Create favorites table for saving favorite products
CREATE TABLE IF NOT EXISTS public.favorites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE NOT NULL,
    product_id UUID REFERENCES public.products(id) ON DELETE CASCADE NOT NULL,
    asin TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- One favorite per user per product
    UNIQUE(user_id, product_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_favorites_user ON public.favorites(user_id);
CREATE INDEX IF NOT EXISTS idx_favorites_product ON public.favorites(product_id);
CREATE INDEX IF NOT EXISTS idx_favorites_user_created ON public.favorites(user_id, created_at DESC);

-- RLS
ALTER TABLE public.favorites ENABLE ROW LEVEL SECURITY;

-- Policies
CREATE POLICY "Users can view own favorites" ON public.favorites
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own favorites" ON public.favorites
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own favorites" ON public.favorites
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own favorites" ON public.favorites
    FOR DELETE USING (auth.uid() = user_id);

COMMENT ON TABLE public.favorites IS 'User favorite products';
COMMENT ON COLUMN public.favorites.product_id IS 'Reference to products table';
COMMENT ON COLUMN public.favorites.asin IS 'Cached ASIN for quick access';
COMMENT ON COLUMN public.favorites.notes IS 'User notes about this favorite';

