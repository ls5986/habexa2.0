// Application constants

export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

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

