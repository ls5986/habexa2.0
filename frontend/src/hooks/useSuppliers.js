import { useState, useEffect } from 'react';
import api from '../services/api';

export const useSuppliers = () => {
  const [suppliers, setSuppliers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchSuppliers = async () => {
    try {
      setLoading(true);
      const response = await api.get('/suppliers');
      // Handle new response format with limit info
      if (response.data.suppliers) {
        setSuppliers(response.data.suppliers);
      } else {
        setSuppliers(response.data);
      }
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
      const response = await api.post('/suppliers', supplierData);
      await fetchSuppliers();
      return response.data;
    } catch (err) {
      throw new Error(err.response?.data?.message || 'Failed to create supplier');
    }
  };

  const updateSupplier = async (id, supplierData) => {
    try {
      const response = await api.put(`/suppliers/${id}`, supplierData);
      await fetchSuppliers();
      return response.data;
    } catch (err) {
      throw new Error(err.response?.data?.message || 'Failed to update supplier');
    }
  };

  const deleteSupplier = async (id) => {
    try {
      await api.delete(`/suppliers/${id}`);
      await fetchSuppliers();
    } catch (err) {
      throw new Error(err.response?.data?.message || 'Failed to delete supplier');
    }
  };

  return {
    suppliers,
    loading,
    error,
    refetch: fetchSuppliers,
    createSupplier,
    updateSupplier,
    deleteSupplier,
  };
};

