import { useState, useEffect } from 'react';
import api from '../services/api';

export const useDeals = (filters = {}) => {
  const [deals, setDeals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchDeals = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      
      if (filters.status) params.append('status', filters.status);
      if (filters.minRoi) params.append('min_roi', filters.minRoi);
      if (filters.supplierId) params.append('supplier_id', filters.supplierId);
      if (filters.category) params.append('category', filters.category);
      if (filters.gating) params.append('gating_status', filters.gating);
      if (filters.limit) params.append('limit', filters.limit);
      if (filters.offset) params.append('offset', filters.offset);

      const response = await api.get(`/deals?${params.toString()}`);
      setDeals(response.data);
      setError(null);
    } catch (err) {
      setError(err.message);
      console.error('Failed to fetch deals:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDeals();
  }, [JSON.stringify(filters)]);

  const saveDeal = async (dealId) => {
    try {
      await api.post(`/deals/${dealId}/save`);
      await fetchDeals();
    } catch (err) {
      throw new Error(err.response?.data?.message || 'Failed to save deal');
    }
  };

  const dismissDeal = async (dealId) => {
    try {
      await api.post(`/deals/${dealId}/dismiss`);
      await fetchDeals();
    } catch (err) {
      throw new Error(err.response?.data?.message || 'Failed to dismiss deal');
    }
  };

  const orderDeal = async (dealId) => {
    try {
      await api.post(`/deals/${dealId}/order`);
      await fetchDeals();
    } catch (err) {
      throw new Error(err.response?.data?.message || 'Failed to mark as ordered');
    }
  };

  return {
    deals,
    loading,
    error,
    refetch: fetchDeals,
    saveDeal,
    dismissDeal,
    orderDeal,
  };
};

