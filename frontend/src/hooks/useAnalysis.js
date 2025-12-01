import { useState } from 'react';
import api from '../services/api';

export const useAnalysis = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const analyzeSingle = async (asin, buyCost, moq = 1, supplierId = null) => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.post('/analyze/single', {
        asin,
        buy_cost: buyCost,
        moq,
        supplier_id: supplierId,
      });
      return response.data;
    } catch (err) {
      const errorMessage = err.response?.data?.message || 'Failed to analyze ASIN';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const analyzeBatch = async (items) => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.post('/analyze/batch', { items });
      return response.data;
    } catch (err) {
      const errorMessage = err.response?.data?.message || 'Failed to analyze batch';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const getHistory = async () => {
    try {
      const response = await api.get('/analyze/history');
      return response.data;
    } catch (err) {
      throw new Error(err.response?.data?.message || 'Failed to fetch history');
    }
  };

  return {
    analyzeSingle,
    analyzeBatch,
    getHistory,
    loading,
    error,
  };
};

