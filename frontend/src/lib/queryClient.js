import { QueryClient } from '@tanstack/react-query';

// Configure QueryClient with 5-minute cache
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Cache data for 5 minutes
      staleTime: 5 * 60 * 1000, // 5 minutes in milliseconds
      // Keep unused data in cache for 10 minutes
      gcTime: 10 * 60 * 1000, // 10 minutes (formerly cacheTime)
      // Retry failed requests 2 times
      retry: 2,
      // Refetch on window focus (optional - can disable if desired)
      refetchOnWindowFocus: false,
      // Don't refetch on reconnect (optional)
      refetchOnReconnect: true,
    },
    mutations: {
      // Retry failed mutations once
      retry: 1,
    },
  },
});

