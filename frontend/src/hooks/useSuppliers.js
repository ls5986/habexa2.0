import { useState, useEffect } from 'react';
import api from '../services/api';

export const useSuppliers = () => {
  const [suppliers, setSuppliers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const fetchSuppliers = async () => {
    try {
      setLoading(true);
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
      setError(null);
    } catch (err) {
      setError(err.message);
      console.error('Failed to fetch suppliers:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSuppliers();
  }, []);

  const createSupplier = async (supplierData) => {
    try {
      setSaving(true);
      setError(null);
      const response = await api.post('/suppliers', supplierData);
      await fetchSuppliers();
      return response.data;
    } catch (err) {
      // Handle limit reached error
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
  };

  const updateSupplier = async (id, supplierData) => {
    try {
      setSaving(true);
      setError(null);
      const response = await api.put(`/suppliers/${id}`, supplierData);
      await fetchSuppliers();
      return response.data;
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.response?.data?.message || err.message || 'Failed to update supplier';
      setError(errorMessage);
      console.error('Failed to update supplier:', err);
      throw new Error(errorMessage);
    } finally {
      setSaving(false);
    }
  };

  const deleteSupplier = async (id) => {
    try {
      setSaving(true);
      await api.delete(`/suppliers/${id}`);
      await fetchSuppliers();
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.response?.data?.message || err.message || 'Failed to delete supplier';
      setError(errorMessage);
      console.error('Failed to delete supplier:', err);
      throw new Error(errorMessage);
    } finally {
      setSaving(false);
    }
  };

  return {
    suppliers,
    loading,
    saving,
    error,
    refetch: fetchSuppliers,
    createSupplier,
    updateSupplier,
    deleteSupplier,
  };
};

