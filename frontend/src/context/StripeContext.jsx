import { createContext, useContext, useState, useEffect } from 'react';
import { loadStripe } from '@stripe/stripe-js';
import api from '../services/api';

const stripePromise = loadStripe(import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY);

const StripeContext = createContext(null);

export function StripeProvider({ children }) {
  const [subscription, setSubscription] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Helper to refresh tier in AuthContext (called after subscription changes)
  const refreshAuthTier = async () => {
    try {
      // Call /auth/me to refresh tier in AuthContext
      // This will be picked up by AuthContext's loadUserTier
      await api.get('/auth/me');
    } catch (err) {
      console.warn('Failed to refresh tier after subscription change:', err);
    }
  };

  useEffect(() => {
    fetchSubscription();
  }, []);

  const fetchSubscription = async (retryCount = 0) => {
    try {
      setLoading(true);
      const response = await api.get('/billing/subscription');
      setSubscription(response.data);
      setError(null);
    } catch (err) {
      console.error('Subscription fetch failed:', err.response?.status, err.response?.data);
      console.error('Full error:', err);
      
      // Retry once (unless it's a 401 auth error)
      if (retryCount === 0 && err.response?.status !== 401) {
        console.log('Retrying subscription fetch...');
        setTimeout(() => fetchSubscription(1), 2000);
        return;
      }
      
      // Fall back to free tier but log the error
      setSubscription({
        tier: 'free',
        status: 'error',
        error: err.response?.data?.detail || 'Failed to load subscription',
        limits: {
          telegram_channels: 1,
          analyses_per_month: 10,
          suppliers: 3,
          alerts: false,
          bulk_analyze: false,
          api_access: false,
          team_seats: 1,
        }
      });
      setError('Could not load subscription. Using free tier.');
    } finally {
      setLoading(false);
    }
  };

  const createCheckout = async (priceKey, includeTrial = true) => {
    const response = await api.post('/billing/checkout', { 
      price_key: priceKey,
      include_trial: includeTrial
    });
    
    // If existing subscription found, return it
    if (response.data.existing) {
      await fetchSubscription();
      return response.data;
    }
    
    window.location.href = response.data.url;
  };

  const openPortal = async () => {
    const response = await api.post('/billing/portal');
    window.location.href = response.data.url;
  };

  const cancelSubscription = async (atPeriodEnd = true) => {
    if (atPeriodEnd) {
      await api.post('/billing/cancel', null, { params: { at_period_end: true } });
    } else {
      await api.post('/billing/cancel-immediately');
    }
    await fetchSubscription();
    // ✅ Refresh tier in AuthContext after subscription change
    await refreshAuthTier();
  };
  
  const resubscribe = async (priceKey) => {
    const response = await api.post('/billing/resubscribe', { price_key: priceKey });
    if (response.data.url) {
      window.location.href = response.data.url;
    }
    await fetchSubscription();
    // ✅ Refresh tier in AuthContext after subscription change
    await refreshAuthTier();
  };

  const reactivateSubscription = async () => {
    await api.post('/billing/reactivate');
    await fetchSubscription();
    // ✅ Refresh tier in AuthContext after subscription change
    await refreshAuthTier();
  };

  const changePlan = async (newPriceKey) => {
    await api.post('/billing/change-plan', { new_price_key: newPriceKey });
    await fetchSubscription();
    // ✅ Refresh tier in AuthContext after subscription change
    await refreshAuthTier();
  };

  const setTier = async (tier) => {
    await api.post('/billing/set-tier', { tier });
    await fetchSubscription();
    // ✅ Refresh tier in AuthContext after subscription change
    await refreshAuthTier();
  };

  const syncSubscription = async () => {
    try {
      const response = await api.post('/billing/sync');
      await fetchSubscription(); // Refresh subscription data
      // ✅ Refresh tier in AuthContext after subscription change
      await refreshAuthTier();
      return response.data;
    } catch (error) {
      console.error('Failed to sync subscription:', error);
      throw error;
    }
  };

  const refreshSubscription = async () => {
    await fetchSubscription();
    // ✅ Refresh tier in AuthContext after subscription change
    await refreshAuthTier();
  };

  const checkFeatureAccess = (feature) => {
    if (!subscription) return false;
    const limits = subscription?.limits || {};
    
    if (typeof limits[feature] === 'boolean') {
      return limits[feature];
    }
    
    if (limits[feature] === -1) return true;
    
    if (feature === 'analyses_per_month') {
      return (subscription?.analyses_used || 0) < (limits[feature] || 0);
    }
    
    return true;
  };

  return (
    <StripeContext.Provider value={{
      subscription,
      loading,
      error,
      createCheckout,
      openPortal,
      cancelSubscription,
      reactivateSubscription,
      resubscribe,
      changePlan,
      setTier,
      syncSubscription,
      checkFeatureAccess,
      refreshSubscription: fetchSubscription,
    }}>
      {children}
    </StripeContext.Provider>
  );
}

export function useStripe() {
  const context = useContext(StripeContext);
  if (!context) {
    throw new Error('useStripe must be used within a StripeProvider');
  }
  return context;
}

