-- Add supplier_id to telegram_channels if not exists
ALTER TABLE telegram_channels 
ADD COLUMN IF NOT EXISTS supplier_id UUID REFERENCES suppliers(id) ON DELETE SET NULL;

-- Add index for supplier lookup
CREATE INDEX IF NOT EXISTS idx_telegram_channels_supplier 
ON telegram_channels(supplier_id);

-- Make sure suppliers table has source column
ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'manual';

-- Add telegram_channel_id for reverse lookup (optional)
ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS telegram_channel_id BIGINT;

-- Add index for reverse lookup
CREATE INDEX IF NOT EXISTS idx_suppliers_telegram_channel 
ON suppliers(telegram_channel_id);

