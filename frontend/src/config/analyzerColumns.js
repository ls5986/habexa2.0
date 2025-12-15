// Analyzer Table Column Configuration
// Complete set of columns for product analysis

export const analyzerColumns = [
  // Selection & Image
  {
    id: 'select',
    label: '',
    type: 'checkbox',
    width: 50,
    visible: true,
    sortable: false,
    sticky: true, // Always visible on left
  },
  {
    id: 'image',
    label: 'Image',
    type: 'image',
    width: 80,
    visible: true,
    sortable: false,
    sticky: true,
  },
  
  // Core Product Info
  {
    id: 'asin',
    label: 'ASIN',
    type: 'text',
    width: 120,
    visible: true,
    sortable: true,
    sticky: true,
    copyable: true,
  },
  {
    id: 'title',
    label: 'Product Title',
    type: 'text',
    width: 300,
    visible: true,
    sortable: true,
  },
  {
    id: 'upc',
    label: 'UPC',
    type: 'text',
    width: 130,
    visible: false,
    sortable: true,
    copyable: true,
  },
  {
    id: 'package_quantity',
    label: 'Pkg Qty',
    type: 'number',
    width: 90,
    visible: true,
    sortable: true,
  },
  {
    id: 'amazon_link',
    label: 'Amazon',
    type: 'link',
    width: 90,
    visible: true,
    sortable: false,
  },
  
  // Category & Classification
  {
    id: 'category',
    label: 'Category',
    type: 'text',
    width: 200,
    visible: true,
    sortable: true,
  },
  {
    id: 'subcategory',
    label: 'Subcategory',
    type: 'text',
    width: 180,
    visible: false,
    sortable: true,
  },
  {
    id: 'brand',
    label: 'Brand',
    type: 'text',
    width: 150,
    visible: false,
    sortable: true,
  },
  {
    id: 'manufacturer',
    label: 'Manufacturer',
    type: 'text',
    width: 150,
    visible: false,
    sortable: true,
  },
  {
    id: 'is_top_level',
    label: 'Top Level',
    type: 'boolean',
    width: 100,
    visible: true,
    sortable: true,
  },
  
  // Pricing Data
  {
    id: 'wholesale_cost',
    label: 'Bought In',
    type: 'currency',
    width: 110,
    visible: true,
    sortable: true,
    editable: true, // Can edit wholesale cost
  },
  {
    id: 'buy_cost',
    label: 'Buy Cost',
    type: 'currency',
    width: 110,
    visible: true,
    sortable: true,
    editable: true, // Can edit buy cost
  },
  {
    id: 'pack_size',
    label: 'Pack Size',
    type: 'number',
    width: 100,
    visible: true,
    sortable: true,
    editable: true, // Can edit pack size
  },
  {
    id: 'moq',
    label: 'MOQ',
    type: 'number',
    width: 80,
    visible: true,
    sortable: true,
    editable: true, // Can edit MOQ
  },
  {
    id: 'buy_box_price',
    label: 'Sell Price',
    type: 'currency',
    width: 110,
    visible: true,
    sortable: true,
  },
  {
    id: 'lowest_price_90d',
    label: 'Lowest 90d',
    type: 'currency',
    width: 120,
    visible: true,
    sortable: true,
  },
  {
    id: 'avg_buybox_90d',
    label: 'Avg BB 90d',
    type: 'currency',
    width: 120,
    visible: false,
    sortable: true,
  },
  {
    id: 'list_price',
    label: 'List Price',
    type: 'currency',
    width: 110,
    visible: false,
    sortable: true,
  },
  
  // Genius Score (NEW - 0-100 composite score)
  {
    id: 'genius_score',
    label: 'Genius Score',
    type: 'genius_score',
    width: 140,
    visible: true,
    sortable: true,
    editable: false,
    colorCoded: true,
  },
  
  // Profitability Metrics (COLOR CODED)
  {
    id: 'profit_amount',
    label: 'Profit',
    type: 'currency',
    width: 110,
    visible: true,
    sortable: true,
    colorCoded: true, // Green/yellow/red based on value
  },
  {
    id: 'roi_percentage',
    label: 'ROI %',
    type: 'percentage',
    width: 100,
    visible: true,
    sortable: true,
    colorCoded: true,
    decimals: 1,
  },
  {
    id: 'margin_percentage',
    label: 'Margin %',
    type: 'percentage',
    width: 110,
    visible: true,
    sortable: true,
    colorCoded: true,
    decimals: 1,
  },
  {
    id: 'break_even_price',
    label: 'Break Even',
    type: 'currency',
    width: 120,
    visible: false,
    sortable: true,
  },
  {
    id: 'profit_tier',
    label: 'Profit Tier',
    type: 'badge',
    width: 130,
    visible: false,
    sortable: true,
  },
  {
    id: 'is_profitable',
    label: 'Profitable',
    type: 'boolean',
    width: 110,
    visible: false,
    sortable: true,
  },
  
  // Sales & Rank Data
  {
    id: 'current_sales_rank',
    label: 'BSR',
    type: 'number',
    width: 110,
    visible: true,
    sortable: true,
    format: 'comma',
  },
  {
    id: 'avg_sales_rank_90d',
    label: 'Avg BSR 90d',
    type: 'number',
    width: 130,
    visible: false,
    sortable: true,
    format: 'comma',
  },
  {
    id: 'est_monthly_sales',
    label: 'Est Monthly Sales',
    type: 'number',
    width: 150,
    visible: true,
    sortable: true,
    format: 'comma',
  },
  {
    id: 'sales_rank_drops_90d',
    label: 'Rank Drops 90d',
    type: 'number',
    width: 140,
    visible: false,
    sortable: true,
  },
  
  // Competition Data
  {
    id: 'fba_seller_count',
    label: 'FBA Sellers',
    type: 'number',
    width: 120,
    visible: true,
    sortable: true,
  },
  {
    id: 'total_seller_count',
    label: 'Total Sellers',
    type: 'number',
    width: 130,
    visible: true,
    sortable: true,
  },
  {
    id: 'amazon_in_stock',
    label: 'Amazon Sells?',
    type: 'boolean',
    width: 130,
    visible: true,
    sortable: true,
  },
  
  // Product Details
  {
    id: 'item_weight',
    label: 'Weight (lbs)',
    type: 'number',
    width: 120,
    visible: false,
    sortable: true,
    decimals: 2,
  },
  {
    id: 'item_length',
    label: 'Length (in)',
    type: 'number',
    width: 120,
    visible: false,
    sortable: true,
    decimals: 2,
  },
  {
    id: 'item_width',
    label: 'Width (in)',
    type: 'number',
    width: 120,
    visible: false,
    sortable: true,
    decimals: 2,
  },
  {
    id: 'item_height',
    label: 'Height (in)',
    type: 'number',
    width: 120,
    visible: false,
    sortable: true,
    decimals: 2,
  },
  
  // Fees & Costs
  {
    id: 'fba_fees',
    label: 'FBA Fees',
    type: 'currency',
    width: 110,
    visible: false,
    sortable: true,
  },
  {
    id: 'referral_fee',
    label: 'Referral Fee',
    type: 'currency',
    width: 120,
    visible: false,
    sortable: true,
  },
  {
    id: 'variable_closing_fee',
    label: 'Closing Fee',
    type: 'currency',
    width: 120,
    visible: false,
    sortable: true,
  },
  
  // Restrictions & Warnings
  {
    id: 'is_hazmat',
    label: 'Hazmat?',
    type: 'boolean',
    width: 100,
    visible: true,
    sortable: true,
  },
  {
    id: 'is_oversized',
    label: 'Oversized?',
    type: 'boolean',
    width: 110,
    visible: false,
    sortable: true,
  },
  {
    id: 'requires_approval',
    label: 'Gated?',
    type: 'boolean',
    width: 100,
    visible: false,
    sortable: true,
  },
  
  // Supplier Info
  {
    id: 'supplier_name',
    label: 'Supplier',
    type: 'text',
    width: 150,
    visible: false,
    sortable: true,
  },
  {
    id: 'supplier_sku',
    label: 'Supplier SKU',
    type: 'text',
    width: 140,
    visible: true,
    sortable: true,
    editable: true, // Can edit supplier SKU
  },
  
  // Purchase History
  {
    id: 'bought_last_30d',
    label: 'Bought Last 30d',
    type: 'number',
    width: 130,
    visible: true,
    sortable: true,
    format: 'comma',
  },
  {
    id: 'bought_last_60d',
    label: 'Bought Last 60d',
    type: 'number',
    width: 130,
    visible: false,
    sortable: true,
    format: 'comma',
  },
  {
    id: 'bought_last_90d',
    label: 'Bought Last 90d',
    type: 'number',
    width: 130,
    visible: false,
    sortable: true,
    format: 'comma',
  },
  
  // Review Data
  {
    id: 'review_count',
    label: 'Reviews',
    type: 'number',
    width: 100,
    visible: false,
    sortable: true,
    format: 'comma',
  },
  {
    id: 'rating',
    label: 'Rating',
    type: 'rating',
    width: 100,
    visible: false,
    sortable: true,
    decimals: 1,
  },
  
  // Metadata
  {
    id: 'analyzed_at',
    label: 'Last Analyzed',
    type: 'datetime',
    width: 170,
    visible: false,
    sortable: true,
  },
  {
    id: 'created_at',
    label: 'Added',
    type: 'datetime',
    width: 170,
    visible: false,
    sortable: true,
  },
];

// Default visible columns (shown on first load)
export const defaultVisibleColumns = [
  'select',
  'image',
  'asin',
  'title',
  'package_quantity',
  'amazon_link',
  'wholesale_cost',
  'buy_cost',
  'pack_size',
  'moq',
  'buy_box_price',
  'profit_amount',
  'ppu',
  'margin_percentage',
  'roi_percentage',
  'is_top_level',
  'category',
  'current_sales_rank',
  'est_monthly_sales',
  'lowest_price_90d',
  'fba_seller_count',
  'total_seller_count',
  'amazon_in_stock',
  'is_hazmat',
  'bought_last_30d',
  'supplier_sku',
];

// Column groups for organized menu
export const columnGroups = {
  core: {
    label: 'Core Info',
    columns: ['select', 'image', 'asin', 'title', 'upc', 'package_quantity', 'amazon_link'],
  },
  classification: {
    label: 'Classification',
    columns: ['category', 'subcategory', 'brand', 'manufacturer', 'is_top_level'],
  },
  pricing: {
    label: 'Pricing',
    columns: ['wholesale_cost', 'buy_cost', 'pack_size', 'moq', 'buy_box_price', 'lowest_price_90d', 'avg_buybox_90d', 'list_price'],
  },
  profitability: {
    label: 'Profitability',
    columns: ['profit_amount', 'roi_percentage', 'margin_percentage', 'break_even_price', 'profit_tier', 'is_profitable'],
  },
  sales: {
    label: 'Sales & Rank',
    columns: ['current_sales_rank', 'avg_sales_rank_90d', 'est_monthly_sales', 'sales_rank_drops_90d'],
  },
  competition: {
    label: 'Competition',
    columns: ['fba_seller_count', 'total_seller_count', 'amazon_in_stock'],
  },
  dimensions: {
    label: 'Dimensions',
    columns: ['item_weight', 'item_length', 'item_width', 'item_height'],
  },
  fees: {
    label: 'Fees & Costs',
    columns: ['fba_fees', 'referral_fee', 'variable_closing_fee'],
  },
  restrictions: {
    label: 'Restrictions',
    columns: ['is_hazmat', 'is_oversized', 'requires_approval'],
  },
  supplier: {
    label: 'Supplier',
    columns: ['supplier_name', 'supplier_sku'],
  },
  purchase: {
    label: 'Purchase History',
    columns: ['bought_last_30d', 'bought_last_60d', 'bought_last_90d'],
  },
  reviews: {
    label: 'Reviews',
    columns: ['review_count', 'rating'],
  },
  metadata: {
    label: 'Metadata',
    columns: ['analyzed_at', 'created_at'],
  },
};

// Color coding thresholds for profitability
export const profitabilityColors = {
  roi: {
    excellent: { min: 50, color: '#4caf50', bgColor: '#e8f5e9' }, // Green
    good: { min: 30, color: '#ff9800', bgColor: '#fff3e0' }, // Orange
    marginal: { min: 15, color: '#ffc107', bgColor: '#fffde7' }, // Yellow
    unprofitable: { min: -Infinity, color: '#f44336', bgColor: '#ffebee' }, // Red
  },
  margin: {
    excellent: { min: 40, color: '#4caf50', bgColor: '#e8f5e9' },
    good: { min: 25, color: '#ff9800', bgColor: '#fff3e0' },
    marginal: { min: 10, color: '#ffc107', bgColor: '#fffde7' },
    unprofitable: { min: -Infinity, color: '#f44336', bgColor: '#ffebee' },
  },
  profit: {
    excellent: { min: 10, color: '#4caf50', bgColor: '#e8f5e9' },
    good: { min: 5, color: '#ff9800', bgColor: '#fff3e0' },
    marginal: { min: 2, color: '#ffc107', bgColor: '#fffde7' },
    unprofitable: { min: -Infinity, color: '#f44336', bgColor: '#ffebee' },
  },
};

// Helper function to get color for a value
export const getColorForValue = (type, value) => {
  if (value === null || value === undefined) return null;
  
  const thresholds = profitabilityColors[type];
  if (!thresholds) return null;
  
  if (value >= thresholds.excellent.min) return thresholds.excellent;
  if (value >= thresholds.good.min) return thresholds.good;
  if (value >= thresholds.marginal.min) return thresholds.marginal;
  return thresholds.unprofitable;
};
