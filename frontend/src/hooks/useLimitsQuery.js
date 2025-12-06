import { useQuery, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';
import { useAuth } from '../context/AuthContext';

// Query key factory for limits
export const limitsKeys = {
  all: ['limits'] as const,
  user: (userId) => [...limitsKeys.all, 'user', userId] as const,
  userLimits: (userId) => [...limitsKeys.user(userId), 'details'] as const,
};

/**
 * Hook to fetch user limits and tier info
 * Uses React Query with 5-minute cache
 * This replaces direct calls to /billing/user/limits
 */
export function useLimitsQuery() {
  const { user } = useAuth();

  const {
    data: limitsData = null,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: limitsKeys.userLimits(user?.id),
    queryFn: async () => {
      if (!user) {
        return null;
      }

      const response = await api.get('/billing/user/limits');
      return response.data;
    },
    enabled: !!user, // Only fetch if user is logged in
    staleTime: 5 * 60 * 1000, // 5 minutes
    // Refetch on window focus (optional - can disable)
    refetchOnWindowFocus: false,
  });

  return {
    limitsData,
    loading: isLoading,
    error: isError ? error : null,
    refetch,
  };
}

/**
 * Hook to invalidate limits cache
 * Call this after subscription changes, upgrades, etc.
 */
export function useInvalidateLimits() {
  const queryClient = useQueryClient();
  const { user } = useAuth();

  const invalidateLimits = () => {
    if (user?.id) {
      queryClient.invalidateQueries({ 
        queryKey: limitsKeys.user(user.id) 
      });
    }
  };

  return { invalidateLimits };
}

