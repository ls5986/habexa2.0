// Formatting utilities

export const formatCurrency = (amount) => {
  if (amount === null || amount === undefined) return '$0.00';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(amount);
};

export const formatNumber = (num) => {
  if (num === null || num === undefined) return '0';
  return new Intl.NumberFormat('en-US').format(num);
};

export const formatROI = (roi) => {
  if (roi === null || roi === undefined) return '0%';
  const sign = roi >= 0 ? '+' : '';
  return `${sign}${roi.toFixed(1)}%`;
};

export const formatPercentage = (value) => {
  if (value === null || value === undefined || isNaN(value)) return '0%';
  return `${Number(value).toFixed(1)}%`;
};

export const formatRank = (rank) => {
  if (!rank) return 'N/A';
  return `#${formatNumber(rank)}`;
};

export const formatTimeAgo = (dateString) => {
  if (!dateString) return 'Unknown';
  
  const date = new Date(dateString);
  const now = new Date();
  const seconds = Math.floor((now - date) / 1000);
  
  if (seconds < 60) return `${seconds} sec ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)} min ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} hour${Math.floor(seconds / 3600) > 1 ? 's' : ''} ago`;
  return `${Math.floor(seconds / 86400)} day${Math.floor(seconds / 86400) > 1 ? 's' : ''} ago`;
};

export const getInitials = (name) => {
  if (!name) return '?';
  return name
    .split(' ')
    .map(n => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
};

