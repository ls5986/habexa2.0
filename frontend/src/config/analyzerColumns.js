/**
 * Column configuration for Analyzer table.
 * Defines which columns are available, their properties, and default visibility.
 */

export const ANALYZER_COLUMNS = [
  {
    id: 'select',
    label: '',
    type: 'checkbox',
    width: 50,
    fixed: true, // Always visible
    sortable: false
  },
  {
    id: 'image',
    label: 'Image',
    type: 'image',
    width: 60,
    defaultVisible: true,
    sortable: false
  },
  {
    id: 'asin',
    label: 'ASIN',
    type: 'text',
    width: 120,
    defaultVisible: true,
    sortable: true,
    sortField: 'asin'
  },
  {
    id: 'title',
    label: 'Title',
    type: 'text',
    width: 200,
    defaultVisible: false, // Hidden by default (too long)
    sortable: true,
    sortField: 'title'
  },
  {
    id: 'package_quantity',
    label: 'Pkg Qty',
    type: 'number',
    width: 80,
    defaultVisible: true,
    sortable: true,
    sortField: 'package_quantity'
  },
  {
    id: 'amazon_link',
    label: 'Amazon',
    type: 'link',
    width: 80,
    defaultVisible: true,
    sortable: false
  },
  {
    id: 'wholesale_cost',
    label: 'Bought In',
    type: 'currency',
    width: 100,
    defaultVisible: true,
    sortable: true,
    sortField: 'wholesale_cost'
  },
  {
    id: 'sell_price',
    label: 'Sell Price',
    type: 'currency',
    width: 100,
    defaultVisible: true,
    sortable: true,
    sortField: 'sell_price'
  },
  {
    id: 'est_monthly_sales',
    label: 'Est Sale #1',
    type: 'number',
    width: 100,
    defaultVisible: true,
    sortable: true,
    sortField: 'est_monthly_sales'
  },
  {
    id: 'profit',
    label: 'Profit',
    type: 'currency',
    width: 100,
    defaultVisible: true,
    sortable: true,
    sortField: 'profit_amount',
    colorCoded: true // Green if positive, red if negative
  },
  {
    id: 'margin',
    label: 'Margin %',
    type: 'percentage',
    width: 100,
    defaultVisible: true,
    sortable: true,
    sortField: 'margin_percentage',
    colorCoded: true
  },
  {
    id: 'roi',
    label: 'ROI %',
    type: 'percentage',
    width: 100,
    defaultVisible: true,
    sortable: true,
    sortField: 'roi_percentage',
    colorCoded: true
  },
  {
    id: 'is_top_level',
    label: 'Top Level',
    type: 'boolean',
    width: 90,
    defaultVisible: true,
    sortable: true,
    sortField: 'is_top_level'
  },
  {
    id: 'category',
    label: 'Category',
    type: 'text',
    width: 150,
    defaultVisible: true,
    sortable: true,
    sortField: 'category'
  },
  {
    id: 'bsr',
    label: 'BSR',
    type: 'number',
    width: 100,
    defaultVisible: true,
    sortable: true,
    sortField: 'current_sales_rank'
  },
  {
    id: 'bsr_30d',
    label: 'BSR 30d',
    type: 'number',
    width: 100,
    defaultVisible: false,
    sortable: true,
    sortField: 'sales_rank_30_day_avg'
  },
  {
    id: 'bsr_90d',
    label: 'BSR 90d',
    type: 'number',
    width: 100,
    defaultVisible: false,
    sortable: true,
    sortField: 'sales_rank_90_day_avg'
  },
  {
    id: 'lowest_90d',
    label: 'Lowest 90d',
    type: 'currency',
    width: 110,
    defaultVisible: true,
    sortable: true,
    sortField: 'lowest_90d'
  },
  {
    id: 'fba_sellers',
    label: 'FBA Sellers',
    type: 'number',
    width: 110,
    defaultVisible: true,
    sortable: true,
    sortField: 'fba_seller_count'
  },
  {
    id: 'total_sellers',
    label: 'Total Sellers',
    type: 'number',
    width: 120,
    defaultVisible: true,
    sortable: true,
    sortField: 'seller_count'
  },
  {
    id: 'amazon_sells',
    label: 'Amazon Sells?',
    type: 'boolean',
    width: 120,
    defaultVisible: true,
    sortable: true,
    sortField: 'amazon_sells'
  },
  {
    id: 'amazon_in_stock',
    label: 'Amazon Stock',
    type: 'boolean',
    width: 120,
    defaultVisible: false,
    sortable: true,
    sortField: 'amazon_in_stock'
  },
  {
    id: 'is_hazmat',
    label: 'Hazmat?',
    type: 'boolean',
    width: 90,
    defaultVisible: true,
    sortable: true,
    sortField: 'is_hazmat'
  },
  {
    id: 'brand_sells',
    label: 'Brand Sells?',
    type: 'boolean',
    width: 110,
    defaultVisible: false,
    sortable: true,
    sortField: 'brand_sells'
  },
  {
    id: 'supplier_name',
    label: 'Supplier',
    type: 'text',
    width: 150,
    defaultVisible: false,
    sortable: false
  },
  {
    id: 'profit_tier',
    label: 'Tier',
    type: 'badge',
    width: 100,
    defaultVisible: false,
    sortable: true,
    sortField: 'profit_tier'
  },
  {
    id: 'break_even_price',
    label: 'Break Even',
    type: 'currency',
    width: 110,
    defaultVisible: false,
    sortable: true,
    sortField: 'break_even_price'
  }
];

/**
 * Get default visible columns
 */
export function getDefaultVisibleColumns() {
  return ANALYZER_COLUMNS
    .filter(col => col.defaultVisible || col.fixed)
    .map(col => col.id);
}

/**
 * Get ROI color based on value
 */
export function getROIColor(roi) {
  if (!roi && roi !== 0) return 'default';
  if (roi >= 50) return 'success'; // Green
  if (roi >= 30) return 'info'; // Blue
  if (roi >= 15) return 'warning'; // Yellow
  return 'error'; // Red
}

/**
 * Get profit tier badge color
 */
export function getProfitTierColor(tier) {
  const colors = {
    excellent: 'success',
    good: 'info',
    marginal: 'warning',
    unprofitable: 'error'
  };
  return colors[tier] || 'default';
}

/**
 * Get row background color based on profitability
 */
export function getRowColor(roi, profitTier) {
  if (!roi && roi !== 0) return 'default';
  
  // Use profit tier if available
  if (profitTier === 'excellent') return 'success.light';
  if (profitTier === 'good') return 'info.light';
  if (profitTier === 'marginal') return 'warning.light';
  if (profitTier === 'unprofitable') return 'error.light';
  
  // Fallback to ROI
  if (roi >= 50) return 'success.light';
  if (roi >= 30) return 'info.light';
  if (roi >= 15) return 'warning.light';
  return 'error.light';
}

