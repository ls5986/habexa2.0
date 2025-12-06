import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import api from '../services/api';
import { useAuth } from './AuthContext';

const SuppliersContext = createContext(null);

export function SuppliersProvider({ children }) {
  const { user } = useAuth();
  const [suppliers, setSuppliers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [lastFetch, setLastFetch] = useState(null);

  // Fetch suppliers from API
  const fetchSuppliers = useCallback(async () => {
    if (!user) {
      setSuppliers([]);
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const response = await api.get('/suppliers');
      
      // Handle different response formats safely
      let suppliersData = [];
      if (Array.isArray(response.data)) {
        suppliersData = response.data;
      } else if (Array.isArray(response.data?.suppliers)) {
        suppliersData = response.data.suppliers;
      } else if (Array.isArray(response.data?.data)) {
        suppliersData = response.data.data;
      }
      
      setSuppliers(suppliersData);
      setLastFetch(Date.now());
    } catch (err) {
      setError(err.message);
      console.error('Failed to fetch suppliers:', err);
      setSuppliers([]);
    } finally {
      setLoading(false);
    }
  }, [user]);

  // Initial fetch on mount
  useEffect(() => {
    if (user) {
      fetchSuppliers();
    }
  }, [user, fetchSuppliers]);

  // Create supplier
  const createSupplier = useCallback(async (supplierData) => {
    try {
      setSaving(true);
      setError(null);
      const response = await api.post('/suppliers', supplierData);
      const newSupplier = response.data?.supplier || response.data;
      
      // Update local state
      setSuppliers(prev => [...prev, newSupplier]);
      return newSupplier;
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
      
      setError(errorMessage);
      console.error('Failed to create supplier:', err);
      throw new Error(errorMessage);
    } finally {
      setSaving(false);
    }
  }, []);

  // Update supplier
  const updateSupplier = useCallback(async (id, supplierData) => {
    try {
      setSaving(true);
      setError(null);
      const response = await api.put(`/suppliers/${id}`, supplierData);
      const updatedSupplier = response.data;
      
      // Update local state
      setSuppliers(prev => prev.map(s => s.id === id ? updatedSupplier : s));
      return updatedSupplier;
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.response?.data?.message || err.message || 'Failed to update supplier';
      setError(errorMessage);
      console.error('Failed to update supplier:', err);
      throw new Error(errorMessage);
    } finally {
      setSaving(false);
    }
  }, []);

  // Delete supplier
  const deleteSupplier = useCallback(async (id) => {
    try {
      setSaving(true);
      await api.delete(`/suppliers/${id}`);
      
      // Update local state
      setSuppliers(prev => prev.filter(s => s.id !== id));
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.response?.data?.message || err.message || 'Failed to delete supplier';
      setError(errorMessage);
      console.error('Failed to delete supplier:', err);
      throw new Error(errorMessage);
    } finally {
      setSaving(false);
    }
  }, []);

  // Manual refresh
  const refreshSuppliers = useCallback(async () => {
    await fetchSuppliers();
  }, [fetchSuppliers]);

  const value = {
    suppliers,
    loading,
    saving,
    error,
    createSupplier,
    updateSupplier,
    deleteSupplier,
    refreshSuppliers,
    lastFetch,
  };

  return (
    <SuppliersContext.Provider value={value}>
      {children}
    </SuppliersContext.Provider>
  );
}

export function useSuppliers() {
  const context = useContext(SuppliersContext);
  if (!context) {
    throw new Error('useSuppliers must be used within a SuppliersProvider');
  }
  return context;
}

