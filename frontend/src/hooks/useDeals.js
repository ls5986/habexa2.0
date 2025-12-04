import { useState, useEffect, useRef } from 'react';
import api from '../services/api';

// Simple in-memory cache with TTL - persists across navigation
const cache = new Map();
const CACHE_TTL = 30000; // 30 seconds

const getCacheKey = (filters) => {
  return `deals:${JSON.stringify(filters)}`;
};

const getCached = (key) => {
  const cached = cache.get(key);
  if (!cached) return null;
  if (Date.now() - cached.timestamp > CACHE_TTL) {
    cache.delete(key);
    return null;
  }
  return cached.data;
};

const setCached = (key, data) => {
  cache.set(key, { data, timestamp: Date.now() });
};

export const useDeals = (filters = {}) => {
  const [deals, setDeals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const abortControllerRef = useRef(null);

  const fetchDeals = async (useCache = true) => {
    // Cancel previous request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();
    
    try {
      setLoading(true);
      
      // Check cache first
      const cacheKey = getCacheKey(filters);
      if (useCache) {
        const cached = getCached(cacheKey);
        if (cached) {
          console.log('✅ [DEALS] Using cached data');
          // Ensure cached data is always an array
          let cachedDeals = [];
          if (Array.isArray(cached)) {
            cachedDeals = cached;
          } else if (Array.isArray(cached?.deals)) {
            cachedDeals = cached.deals;
          } else if (Array.isArray(cached?.data)) {
            cachedDeals = cached.data;
          }
          setDeals(cachedDeals);
          setError(null);
          setLoading(false);
          return;
        }
      }
      
      const params = new URLSearchParams();
      
      if (filters.status) params.append('status', filters.status);
      if (filters.minRoi) params.append('min_roi', filters.minRoi);
      if (filters.supplierId) params.append('supplier_id', filters.supplierId);
      if (filters.category) params.append('category', filters.category);
      if (filters.gating) params.append('gating_status', filters.gating);
      if (filters.limit) params.append('limit', filters.limit);
      if (filters.offset) params.append('offset', filters.offset);
      // Only append is_profitable if it's actually a boolean (true/false), not null/undefined
      if (typeof filters.is_profitable === 'boolean') {
        params.append('is_profitable', filters.is_profitable.toString());
      }
      if (filters.search) params.append('search', filters.search);

      const startTime = performance.now();
      const response = await api.get(`/deals?${params.toString()}`, {
        signal: abortControllerRef.current.signal
      });
      const fetchTime = performance.now() - startTime;
      console.log(`⏱️ [DEALS] API call took ${fetchTime.toFixed(0)}ms`);
      
      // New API returns { deals, total, limit, offset }
      // Handle different response formats safely
      let dealsData = [];
      if (Array.isArray(response.data)) {
        dealsData = response.data;
      } else if (Array.isArray(response.data?.deals)) {
        dealsData = response.data.deals;
      } else if (Array.isArray(response.data?.data)) {
        dealsData = response.data.data;
      }
      
      setDeals(dealsData);
      setError(null);
      
      // Cache the result
      setCached(cacheKey, response.data);
      console.log('💾 [DEALS] Cached response');
    } catch (err) {
      // Ignore AbortError - it's expected when requests are cancelled
      if (err.name === 'AbortError' || err.code === 'ERR_CANCELED') {
        console.log('✅ Request cancelled (expected)');
        return;
      }
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
      // Clear cache and refetch
      cache.clear();
      await fetchDeals(false);
    } catch (err) {
      throw new Error(err.response?.data?.message || 'Failed to save deal');
    }
  };

  const dismissDeal = async (dealId) => {
    try {
      await api.post(`/deals/${dealId}/dismiss`);
      // Clear cache and refetch
      cache.clear();
      await fetchDeals(false);
    } catch (err) {
      throw new Error(err.response?.data?.message || 'Failed to dismiss deal');
    }
  };

  const orderDeal = async (dealId) => {
    try {
      await api.post(`/deals/${dealId}/order`);
      // Clear cache and refetch
      cache.clear();
      await fetchDeals(false);
    } catch (err) {
      throw new Error(err.response?.data?.message || 'Failed to mark as ordered');
    }
  };

  return {
    deals,
    loading,
    error,
    refetch: () => fetchDeals(false), // Force refresh, skip cache
    saveDeal,
    dismissDeal,
    orderDeal,
  };
};
