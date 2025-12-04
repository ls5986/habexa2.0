// Application constants

// API base URL - must be set in environment variables
const envApiUrl = import.meta.env.VITE_API_URL;

// Production default fallback
const PRODUCTION_API_URL = 'https://habexa-backend-w5u5.onrender.com';

// Get API URL with fallback
let API_URL = envApiUrl || PRODUCTION_API_URL;

// If it's a relative path (starts with /), it's wrong - use production default
if (API_URL.startsWith('/')) {
  console.error('VITE_API_URL is a relative path:', API_URL, '- using production default');
  API_URL = PRODUCTION_API_URL;
}

// If it doesn't start with http, assume it's missing protocol
if (API_URL && !API_URL.startsWith('http')) {
  console.warn('VITE_API_URL missing protocol, adding https://');
  API_URL = `https://${API_URL}`;
}

// Final fallback
if (!API_URL) {
  console.error('API_URL is undefined, using production default');
  API_URL = PRODUCTION_API_URL;
}

// Log the final URL (only in dev to avoid spam)
if (import.meta.env.DEV) {
  console.log('API_BASE_URL configured as:', API_URL);
}

// For backward compatibility, export as API_BASE_URL as well
export const API_BASE_URL = API_URL;
export { API_URL };

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

