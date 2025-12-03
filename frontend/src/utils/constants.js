// Application constants

// Determine API base URL based on environment
const getApiBaseUrl = () => {
  let url = import.meta.env.VITE_API_URL;
  
  // If VITE_API_URL is set, use it (but ensure it has protocol and full domain)
  if (url && url !== 'http://localhost:8020') {
    // If it's just a hostname (from Render's fromService.host), add https:// and .onrender.com
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
      // Check if it already has .onrender.com
      if (!url.includes('.onrender.com') && !url.includes('localhost')) {
        url = `https://${url}.onrender.com`;
      } else {
        url = `https://${url}`;
      }
    }
    return url;
  }
  
  // In production (on Render), construct backend URL
  if (import.meta.env.PROD || (typeof window !== 'undefined' && window.location.hostname.includes('onrender.com'))) {
    // Backend URL on Render - check for env var first, then fallback
    if (import.meta.env.VITE_BACKEND_URL) {
      const backendUrl = import.meta.env.VITE_BACKEND_URL;
      if (backendUrl.startsWith('http')) {
        return backendUrl;
      }
      // If it's just a hostname, add https:// and .onrender.com if needed
      if (!backendUrl.includes('.onrender.com')) {
        return `https://${backendUrl}.onrender.com`;
      }
      return `https://${backendUrl}`;
    }
    // Default Render backend URL (update this if your service name is different)
    return 'https://habexa-backend-w5u5.onrender.com';
  }
  
  // Default to localhost for development
  return 'http://localhost:8020';
};

export const API_BASE_URL = getApiBaseUrl();

// Debug: log the API URL in development
if (import.meta.env.DEV) {
  console.log('🔗 API_BASE_URL:', API_BASE_URL);
}

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

