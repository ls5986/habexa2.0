import { useState, useCallback } from 'react';
import api from '../services/api';

export function useEligibility() {
  const [cache, setCache] = useState({});
  const [loading, setLoading] = useState({});

  const checkEligibility = useCallback(async (asin) => {
    // Return cached result if available
    if (cache[asin]) {
      return cache[asin];
    }

    // Mark as loading
    setLoading(prev => ({ ...prev, [asin]: true }));

    try {
      const response = await api.get(`/integrations/amazon/eligibility/${asin}`);
      const result = response.data;
      
      // Cache the result
      setCache(prev => ({ ...prev, [asin]: result }));
      
      return result;
    } catch (error) {
      const errorResult = {
        status: 'UNKNOWN',
        asin,
        error: error.response?.data?.detail || 'Check failed'
      };
      setCache(prev => ({ ...prev, [asin]: errorResult }));
      return errorResult;
    } finally {
      setLoading(prev => ({ ...prev, [asin]: false }));
    }
  }, [cache]);

  const checkBatch = useCallback(async (asins) => {
    // Filter out already cached
    const uncached = asins.filter(asin => !cache[asin]);
    
    if (uncached.length > 0) {
      try {
        const response = await api.post('/integrations/amazon/eligibility/batch', {
          asins: uncached
        });
        
        // Update cache with results
        const newCache = {};
        response.data.results.forEach(result => {
          newCache[result.asin] = result;
        });
        setCache(prev => ({ ...prev, ...newCache }));
      } catch (error) {
        console.error('Batch eligibility check failed:', error);
      }
    }

    // Return all results from cache
    return asins.map(asin => cache[asin] || { status: 'UNKNOWN', asin });
  }, [cache]);

  const isLoading = useCallback((asin) => {
    return loading[asin] || false;
  }, [loading]);

  const getStatus = useCallback((asin) => {
    return cache[asin]?.status || null;
  }, [cache]);

  return {
    checkEligibility,
    checkBatch,
    isLoading,
    getStatus,
    cache,
  };
}
