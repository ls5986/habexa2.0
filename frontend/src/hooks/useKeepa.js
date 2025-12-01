import { useState, useCallback } from 'react';
import api from '../services/api';

export function useKeepa() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [cache, setCache] = useState({});

  const getProduct = useCallback(async (asin, days = 90) => {
    // Check cache
    const cacheKey = `${asin}-${days}`;
    if (cache[cacheKey]) {
      return cache[cacheKey];
    }

    setLoading(true);
    setError(null);

    try {
      const response = await api.get(`/keepa/product/${asin}`, {
        params: { days }
      });
      
      const data = response.data;
      
      // Cache the result
      setCache(prev => ({ ...prev, [cacheKey]: data }));
      
      return data;
    } catch (err) {
      const message = err.response?.data?.detail || 'Failed to fetch Keepa data';
      setError(message);
      throw new Error(message);
    } finally {
      setLoading(false);
    }
  }, [cache]);

  const getHistory = useCallback(async (asin, days = 90) => {
    setLoading(true);
    setError(null);

    try {
      const response = await api.get(`/keepa/history/${asin}`, {
        params: { days }
      });
      return response.data;
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to fetch history');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const getSalesEstimate = useCallback(async (asin) => {
    try {
      const response = await api.get(`/keepa/sales-estimate/${asin}`);
      return response.data;
    } catch (err) {
      console.error('Sales estimate error:', err);
      return null;
    }
  }, []);

  const getTokenStatus = useCallback(async () => {
    try {
      const response = await api.get('/keepa/tokens');
      return response.data;
    } catch {
      return null;
    }
  }, []);

  return {
    getProduct,
    getHistory,
    getSalesEstimate,
    getTokenStatus,
    loading,
    error,
    cache,
  };
}

