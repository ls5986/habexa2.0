import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';
import { useAuth } from '../context/AuthContext';

// Query key factory
export const supplierKeys = {
  all: ['suppliers'],
  lists: () => [...supplierKeys.all, 'list'],
  list: (filters) => [...supplierKeys.lists(), { filters }],
  details: () => [...supplierKeys.all, 'detail'],
  detail: (id) => [...supplierKeys.details(), id],
};

/**
 * Hook to fetch suppliers list
 * Uses React Query with 5-minute cache
 */
export function useSuppliers() {
  const { user } = useAuth();

  const {
    data: suppliers = [],
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: supplierKeys.lists(),
    queryFn: async () => {
      if (!user) {
        return [];
      }

      const response = await api.get('/suppliers');
      
      // Handle different response formats safely
      if (Array.isArray(response.data)) {
        return response.data;
      } else if (Array.isArray(response.data?.suppliers)) {
        return response.data.suppliers;
      } else if (Array.isArray(response.data?.data)) {
        return response.data.data;
      }
      
      return [];
    },
    enabled: !!user, // Only fetch if user is logged in
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  return {
    suppliers,
    loading: isLoading,
    error: isError ? error : null,
    refetch,
  };
}

/**
 * Hook to create a new supplier
 */
export function useCreateSupplier() {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: async (supplierData) => {
      const response = await api.post('/suppliers', supplierData);
      return response.data?.supplier || response.data;
    },
    onSuccess: (newSupplier) => {
      // Invalidate and refetch suppliers list
      queryClient.invalidateQueries({ queryKey: supplierKeys.lists() });
      
      // Optionally add to cache optimistically
      queryClient.setQueryData(supplierKeys.lists(), (old = []) => [...old, newSupplier]);
    },
    onError: (error) => {
      console.error('Failed to create supplier:', error);
    },
  });

  return {
    createSupplier: mutation.mutateAsync,
    isCreating: mutation.isPending,
    error: mutation.error,
  };
}

/**
 * Hook to update a supplier
 */
export function useUpdateSupplier() {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: async ({ id, ...supplierData }) => {
      const response = await api.put(`/suppliers/${id}`, supplierData);
      return response.data;
    },
    onSuccess: (updatedSupplier, variables) => {
      // Invalidate and refetch suppliers list
      queryClient.invalidateQueries({ queryKey: supplierKeys.lists() });
      
      // Update cache optimistically
      queryClient.setQueryData(supplierKeys.lists(), (old = []) =>
        old.map((s) => (s.id === variables.id ? updatedSupplier : s))
      );
    },
    onError: (error) => {
      console.error('Failed to update supplier:', error);
    },
  });

  return {
    updateSupplier: mutation.mutateAsync,
    isUpdating: mutation.isPending,
    error: mutation.error,
  };
}

/**
 * Hook to delete a supplier
 */
export function useDeleteSupplier() {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: async (id) => {
      await api.delete(`/suppliers/${id}`);
      return id;
    },
    onSuccess: (deletedId) => {
      // Invalidate and refetch suppliers list
      queryClient.invalidateQueries({ queryKey: supplierKeys.lists() });
      
      // Remove from cache optimistically
      queryClient.setQueryData(supplierKeys.lists(), (old = []) =>
        old.filter((s) => s.id !== deletedId)
      );
    },
    onError: (error) => {
      console.error('Failed to delete supplier:', error);
    },
  });

  return {
    deleteSupplier: mutation.mutateAsync,
    isDeleting: mutation.isPending,
    error: mutation.error,
  };
}

