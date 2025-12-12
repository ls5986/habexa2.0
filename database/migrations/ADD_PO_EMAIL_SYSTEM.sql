-- HABEXA: Automated Purchase Order Email System
-- Tables for PO generation, email templates, and email tracking

-- ============================================
-- 1. EMAIL TEMPLATES TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS email_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    supplier_id UUID REFERENCES suppliers(id) ON DELETE CASCADE,
    
    -- Template Info
    name TEXT NOT NULL,
    subject TEXT NOT NULL,
    body_text TEXT NOT NULL, -- Plain text body
    body_html TEXT, -- HTML body (optional)
    
    -- Template Variables
    -- Supported variables:
    -- {{order_number}}, {{total}}, {{supplier_name}}, {{order_date}}, {{items_count}}
    -- {{line_items}}, {{shipping_address}}, {{payment_terms}}
    
    -- Settings
    is_default BOOLEAN DEFAULT false,
    cc_emails TEXT[], -- Array of CC email addresses
    bcc_emails TEXT[], -- Array of BCC email addresses
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(user_id, supplier_id, name) -- One template per name per supplier
);

CREATE INDEX IF NOT EXISTS idx_email_templates_user ON email_templates(user_id);
CREATE INDEX IF NOT EXISTS idx_email_templates_supplier ON email_templates(supplier_id);

-- ============================================
-- 2. PO GENERATION RECORDS
-- ============================================
CREATE TABLE IF NOT EXISTS po_generations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    supplier_order_id UUID REFERENCES supplier_orders(id) ON DELETE CASCADE NOT NULL,
    
    -- PO Details
    po_number TEXT NOT NULL UNIQUE, -- PO-2024-12-00001
    pdf_url TEXT, -- URL to generated PDF (stored in S3 or similar)
    pdf_filename TEXT,
    
    -- Email Details
    email_template_id UUID REFERENCES email_templates(id),
    email_sent_at TIMESTAMP WITH TIME ZONE,
    email_subject TEXT,
    email_recipient TEXT, -- Supplier email
    email_cc TEXT[],
    email_bcc TEXT[],
    
    -- Status
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'sent', 'opened', 'bounced', 'failed')),
    
    -- Metadata
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_po_generations_order ON po_generations(supplier_order_id);
CREATE INDEX IF NOT EXISTS idx_po_generations_user ON po_generations(user_id);
CREATE INDEX IF NOT EXISTS idx_po_generations_status ON po_generations(status);
CREATE UNIQUE INDEX IF NOT EXISTS idx_po_generations_po_number ON po_generations(po_number);

-- ============================================
-- 3. EMAIL TRACKING
-- ============================================
CREATE TABLE IF NOT EXISTS email_tracking (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
    po_generation_id UUID REFERENCES po_generations(id) ON DELETE CASCADE,
    
    -- Email Details
    email_id TEXT, -- SendGrid email ID
    recipient TEXT NOT NULL,
    subject TEXT NOT NULL,
    
    -- Tracking
    sent_at TIMESTAMP WITH TIME ZONE,
    delivered_at TIMESTAMP WITH TIME ZONE,
    opened_at TIMESTAMP WITH TIME ZONE,
    opened_count INTEGER DEFAULT 0,
    clicked_at TIMESTAMP WITH TIME ZONE,
    clicked_count INTEGER DEFAULT 0,
    bounced_at TIMESTAMP WITH TIME ZONE,
    bounced_reason TEXT,
    
    -- Status
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'delivered', 'opened', 'clicked', 'bounced', 'failed')),
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_email_tracking_po ON email_tracking(po_generation_id);
CREATE INDEX IF NOT EXISTS idx_email_tracking_user ON email_tracking(user_id);
CREATE INDEX IF NOT EXISTS idx_email_tracking_status ON email_tracking(status);
CREATE INDEX IF NOT EXISTS idx_email_tracking_email_id ON email_tracking(email_id);

-- ============================================
-- 4. HELPER FUNCTION: Generate PO Number
-- ============================================
CREATE OR REPLACE FUNCTION generate_po_number()
RETURNS TEXT AS $$
DECLARE
    v_date TEXT;
    v_sequence INTEGER;
    v_po_number TEXT;
BEGIN
    -- Format: PO-YYYY-MM-#####
    v_date := TO_CHAR(NOW(), 'YYYY-MM');
    
    -- Get next sequence number for this month
    SELECT COALESCE(MAX(CAST(SUBSTRING(po_number FROM '[0-9]+$') AS INTEGER)), 0) + 1
    INTO v_sequence
    FROM po_generations
    WHERE po_number LIKE 'PO-' || v_date || '-%';
    
    -- Format with leading zeros (5 digits)
    v_po_number := 'PO-' || v_date || '-' || LPAD(v_sequence::TEXT, 5, '0');
    
    RETURN v_po_number;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- 5. COMMENTS
-- ============================================
COMMENT ON TABLE email_templates IS 'Email templates for PO emails with variable substitution';
COMMENT ON TABLE po_generations IS 'Records of generated POs with PDF and email tracking';
COMMENT ON TABLE email_tracking IS 'SendGrid email tracking (sent, delivered, opened, clicked, bounced)';
COMMENT ON COLUMN email_templates.body_text IS 'Plain text email body with {{variable}} placeholders';
COMMENT ON COLUMN po_generations.po_number IS 'Auto-generated PO number (PO-2024-12-00001)';
COMMENT ON FUNCTION generate_po_number IS 'Generates unique PO number: PO-YYYY-MM-#####';

