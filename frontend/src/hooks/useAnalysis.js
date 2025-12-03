import { useState } from 'react';
import api from '../services/api';

export const useAnalysis = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const analyzeSingle = async (identifier, buyCost, moq = 1, supplierId = null, identifierType = 'asin', quantity = 1) => {
    try {
      setLoading(true);
      setError(null);
      const payload = {
        identifier_type: identifierType,
        buy_cost: buyCost,
        moq,
        supplier_id: supplierId,
      };
      
      if (identifierType === 'asin') {
        payload.asin = identifier;
      } else {
        payload.upc = identifier;
        payload.quantity = quantity;
      }
      
      const response = await api.post('/analyze/single', payload);
      return response.data;
    } catch (err) {
      const errorMessage = err.response?.data?.detail?.message || err.response?.data?.detail || err.response?.data?.message || `Failed to analyze ${identifierType.toUpperCase()}`;
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

