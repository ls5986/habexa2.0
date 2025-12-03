import { createContext, useContext, useState, useEffect } from 'react';
import { loadStripe } from '@stripe/stripe-js';
import api from '../services/api';

const stripePromise = loadStripe(import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY);

const StripeContext = createContext(null);

export function StripeProvider({ children }) {
  const [subscription, setSubscription] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSubscription();
  }, []);

  const fetchSubscription = async () => {
    try {
      const response = await api.get('/billing/subscription');
      setSubscription(response.data);
    } catch (error) {
      console.error('Failed to fetch subscription:', error);
      setSubscription({
        tier: 'free',
        status: 'active',
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
    } finally {
      setLoading(false);
    }
  };

  const createCheckout = async (priceKey) => {
    const response = await api.post('/billing/checkout', { price_key: priceKey });
    window.location.href = response.data.url;
  };

  const openPortal = async () => {
    const response = await api.post('/billing/portal');
    window.location.href = response.data.url;
  };

  const cancelSubscription = async (atPeriodEnd = true) => {
    await api.post(`/billing/cancel?at_period_end=${atPeriodEnd}`);
    await fetchSubscription();
  };

  const reactivateSubscription = async () => {
    await api.post('/billing/reactivate');
    await fetchSubscription();
  };

  const changePlan = async (newPriceKey) => {
    await api.post('/billing/change-plan', { new_price_key: newPriceKey });
    await fetchSubscription();
  };

  const setTier = async (tier) => {
    await api.post('/billing/set-tier', { tier });
    await fetchSubscription();
  };

  const syncSubscription = async () => {
    try {
      const response = await api.post('/billing/sync');
      await fetchSubscription(); // Refresh subscription data
      return response.data;
    } catch (error) {
      console.error('Failed to sync subscription:', error);
      throw error;
    }
  };

  const refreshSubscription = async () => {
    await fetchSubscription();
  };

  const checkFeatureAccess = (feature) => {
    if (!subscription) return false;
    const limits = subscription.limits || {};
    
    if (typeof limits[feature] === 'boolean') {
      return limits[feature];
    }
    
    if (limits[feature] === -1) return true;
    
    if (feature === 'analyses_per_month') {
      return (subscription.analyses_used || 0) < limits[feature];
    }
    
    return true;
  };

  return (
    <StripeContext.Provider value={{
      subscription,
      loading,
      createCheckout,
      openPortal,
      cancelSubscription,
      reactivateSubscription,
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

