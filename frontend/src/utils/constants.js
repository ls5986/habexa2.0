// Application constants

// API base URL - must be set in environment variables
export const API_URL = import.meta.env.VITE_API_URL;

if (!API_URL) {
  console.error('VITE_API_URL environment variable is not set');
}

// For backward compatibility, export as API_BASE_URL as well
export const API_BASE_URL = API_URL;

export const DEAL_STATUSES = {
  PENDING: 'pending',
  ANALYZED: 'analyzed',
  SAVED: 'saved',
  ORDERED: 'ordered',
  DISMISSED: 'dismissed',
};

export const GATING_STATUSES = {
  UNGATED: 'ungated',
  GATED: 'gated',
  AMAZON_RESTRICTED: 'amazon_restricted',
  UNKNOWN: 'unknown',
};

export const DEAL_SCORES = ['A', 'B', 'C', 'D', 'F'];

export const CATEGORIES = [
  'Electronics',
  'Home & Kitchen',
  'Toys & Games',
  'Beauty',
  'Pet Supplies',
  'Clothing',
  'Grocery',
  'Sports',
  'Books',
  'Health & Personal Care',
];

