import { createContext, useContext, useMemo } from 'react';
import {
  useSuppliers as useSuppliersQuery,
  useCreateSupplier,
  useUpdateSupplier,
  useDeleteSupplier,
} from '../hooks/useSuppliersQuery';

const SuppliersContext = createContext(null);

/**
 * SuppliersProvider - Wraps React Query hooks for suppliers
 * Provides backward-compatible API for existing components
 */
export function SuppliersProvider({ children }) {
  // React Query hooks
  const { suppliers, loading, error, refetch } = useSuppliersQuery();
  const { createSupplier: createSupplierMutation, isCreating } = useCreateSupplier();
  const { updateSupplier: updateSupplierMutation, isUpdating } = useUpdateSupplier();
  const { deleteSupplier: deleteSupplierMutation, isDeleting } = useDeleteSupplier();

  // Wrap mutations with error handling
  const createSupplier = async (supplierData) => {
    try {
      return await createSupplierMutation(supplierData);
    } catch (err) {
      const errorDetail = err.response?.data?.detail;
      let errorMessage = 'Failed to create supplier';
      
      if (errorDetail) {
        if (typeof errorDetail === 'object' && errorDetail.error === 'limit_reached') {
          errorMessage = errorDetail.message || `You've reached your supplier limit (${errorDetail.used}/${errorDetail.limit}). Please upgrade to add more suppliers.`;
        } else if (typeof errorDetail === 'string') {
          errorMessage = errorDetail;
        } else if (errorDetail.message) {
          errorMessage = errorDetail.message;
        }
      } else if (err.response?.data?.message) {
        errorMessage = err.response.data.message;
      } else if (err.message) {
        errorMessage = err.message;
      }
      
      throw new Error(errorMessage);
    }
  };

  const updateSupplier = async (id, supplierData) => {
    try {
      return await updateSupplierMutation({ id, ...supplierData });
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.response?.data?.message || err.message || 'Failed to update supplier';
      throw new Error(errorMessage);
    }
  };

  const deleteSupplier = async (id) => {
    try {
      await deleteSupplierMutation(id);
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.response?.data?.message || err.message || 'Failed to delete supplier';
      throw new Error(errorMessage);
    }
  };

  // Combine saving states
  const saving = isCreating || isUpdating || isDeleting;

  const value = useMemo(
    () => ({
      suppliers,
      loading,
      saving,
      error,
      createSupplier,
      updateSupplier,
      deleteSupplier,
      refreshSuppliers: refetch,
      lastFetch: null, // React Query manages this internally
    }),
    [suppliers, loading, saving, error, refetch]
  );

  return (
    <SuppliersContext.Provider value={value}>
      {children}
    </SuppliersContext.Provider>
  );
}

/**
 * Hook to use suppliers - backward compatible with existing code
 * Now powered by React Query with 5-minute cache
 */
export function useSuppliers() {
  const context = useContext(SuppliersContext);
  if (!context) {
    throw new Error('useSuppliers must be used within a SuppliersProvider');
  }
  return context;
}

