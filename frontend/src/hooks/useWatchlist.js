import { useState, useEffect } from 'react';
import api from '../services/api';

export const useWatchlist = () => {
  const [watchlist, setWatchlist] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchWatchlist = async () => {
    try {
      setLoading(true);
      const response = await api.get('/watchlist');
      setWatchlist(response.data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWatchlist();
  }, []);

  const addToWatchlist = async (asin, targetPrice = null, notes = null) => {
    try {
      const response = await api.post('/watchlist', {
        asin,
        target_price: targetPrice,
        notes,
        notify_on_price_drop: true,
      });
      await fetchWatchlist();
      return response.data;
    } catch (err) {
      throw new Error(err.response?.data?.detail || 'Failed to add to watchlist');
    }
  };

  const removeFromWatchlist = async (itemId) => {
    try {
      await api.delete(`/watchlist/${itemId}`);
      await fetchWatchlist();
    } catch (err) {
      throw new Error(err.response?.data?.detail || 'Failed to remove from watchlist');
    }
  };

  const checkWatchlist = async (asin) => {
    try {
      const response = await api.get(`/watchlist/${asin}/check`);
      return response.data;
    } catch (err) {
      return { in_watchlist: false, item_id: null };
    }
  };

  return {
    watchlist,
    loading,
    error,
    refetch: fetchWatchlist,
    addToWatchlist,
    removeFromWatchlist,
    checkWatchlist,
  };
};

