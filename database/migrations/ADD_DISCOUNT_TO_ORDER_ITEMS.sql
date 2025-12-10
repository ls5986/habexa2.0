-- Add discount column to order_items table if it doesn't exist
-- This allows per-item discounts in purchase requests

ALTER TABLE order_items 
ADD COLUMN IF NOT EXISTS discount DECIMAL(10, 2) DEFAULT 0;

-- Update the total_cost calculation to include discount
-- Note: PostgreSQL doesn't allow modifying GENERATED columns directly
-- We'll calculate total in application code: (quantity * unit_cost) - discount

COMMENT ON COLUMN order_items.discount IS 'Discount amount for this item in the order';

