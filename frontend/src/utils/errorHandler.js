/**
 * Centralized error handler for consistent error handling across the application.
 * 
 * @param {Error} error - The error object from API calls or other operations
 * @param {Function} showToast - Function to display toast notifications (from useToast hook)
 * @returns {string} - The error message that was displayed
 */
export function handleApiError(error, showToast) {
  console.error('API Error:', error);

  // Extract message
  let message = 'An unexpected error occurred';

  if (error.response?.data?.detail) {
    // Handle both string and object detail responses
    const detail = error.response.data.detail;
    if (typeof detail === 'string') {
      message = detail;
    } else if (typeof detail === 'object' && detail.message) {
      message = detail.message;
    } else if (typeof detail === 'object') {
      // Try to stringify if it's an object
      message = JSON.stringify(detail);
    }
  } else if (error.response?.data?.message) {
    message = error.response.data.message;
  } else if (error.message) {
    message = error.message;
  }

  // Handle specific status codes
  if (error.response?.status === 401) {
    message = 'Session expired. Please log in again.';
    // Optionally trigger logout - could be added later
    // if (onLogout) onLogout();
  } else if (error.response?.status === 403) {
    message = 'You do not have permission to perform this action.';
  } else if (error.response?.status === 404) {
    message = 'The requested resource was not found.';
  } else if (error.response?.status >= 500) {
    message = 'Server error. Please try again later.';
  }

  // Show toast notification if showToast is provided
  if (showToast) {
    showToast(message, 'error');
  }

  return message;
}

