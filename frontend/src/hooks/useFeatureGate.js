import { useCallback, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useToast } from '../context/ToastContext';
import api from '../services/api';

export function useFeatureGate() {
  const navigate = useNavigate();
  const { showToast } = useToast();
  
  // Fetch limits from backend API - single source of truth
  const [limitsData, setLimitsData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchLimits = async () => {
      try {
        setIsLoading(true);
        const response = await api.get('/billing/user/limits');
        setLimitsData(response.data);
        setError(null);
      } catch (err) {
        console.error('Failed to fetch user limits:', err);
        setError(err);
        // Fallback to free tier on error
        setLimitsData({
          tier: 'free',
          tier_display: 'Free',
          is_super_admin: false,
          unlimited: false,
          limits: {
            analyses_per_month: { limit: 5, used: 0, remaining: 5, unlimited: false },
            telegram_channels: { limit: 1, used: 0, remaining: 1, unlimited: false },
            suppliers: { limit: 3, used: 0, remaining: 3, unlimited: false },
          }
        });
      } finally {
        setIsLoading(false);
      }
    };

    fetchLimits();
    
    // Refresh every 30 seconds to keep usage up to date
    const interval = setInterval(fetchLimits, 30000);
    return () => clearInterval(interval);
  }, []);

  const tier = limitsData?.tier || 'free';
  const isSuperAdmin = limitsData?.is_super_admin || false;
  const isUnlimited = limitsData?.unlimited || false;

  /**
   * Check limit for a feature - returns backend data
   */
  const checkLimit = useCallback((feature) => {
    if (isLoading || !limitsData) {
      return { allowed: false, loading: true };
    }

    const featureLimit = limitsData?.limits?.[feature];
    if (!featureLimit) {
      // Unknown feature, allow by default
      return { allowed: true, unlimited: true };
    }

    // Boolean feature
    if (typeof featureLimit.allowed === 'boolean') {
      return {
        allowed: featureLimit.allowed,
        unlimited: featureLimit.unlimited || false,
      };
    }

    // Numeric feature
    return {
      allowed: featureLimit.unlimited || featureLimit.remaining > 0,
      remaining: featureLimit.remaining,
      limit: featureLimit.limit,
      used: featureLimit.used,
      unlimited: featureLimit.unlimited,
    };
  }, [limitsData, isLoading]);

  /**
   * Check if user has access to a boolean feature
   */
  const hasFeature = useCallback((feature) => {
    const check = checkLimit(feature);
    return check.allowed === true;
  }, [checkLimit]);

  /**
   * Get the limit for a numeric feature
   * Returns -1 for unlimited
   */
  const getLimit = useCallback((feature) => {
    const check = checkLimit(feature);
    return check.unlimited ? -1 : (check.limit ?? 0);
  }, [checkLimit]);

  /**
   * Check if a numeric limit has been reached
   */
  const isLimitReached = useCallback((feature) => {
    const check = checkLimit(feature);
    if (check.unlimited) return false;
    return check.remaining <= 0;
  }, [checkLimit]);

  /**
   * Get remaining count for a numeric feature
   */
  const getRemaining = useCallback((feature) => {
    const check = checkLimit(feature);
    return check.unlimited ? Infinity : (check.remaining ?? 0);
  }, [checkLimit]);

  /**
   * Check if feature is unlimited
   */
  const isFeatureUnlimited = useCallback((feature) => {
    const check = checkLimit(feature);
    return check.unlimited || false;
  }, [checkLimit]);

  /**
   * Show upgrade prompt and optionally navigate to pricing
   */
  const promptUpgrade = useCallback((feature, options = {}) => {
    const { 
      message,
      navigateToPricing = true,
      toastType = 'warning'
    } = options;

    const defaultMessages = {
      telegram_channels: "You've reached your channel limit.",
      analyses_per_month: "You've used all your analyses this month.",
      suppliers: "You've reached your supplier limit.",
      bulk_analyze: "Bulk analysis requires Pro or higher.",
      api_access: "API access requires Agency plan.",
      alerts: "Alerts require Starter or higher.",
      export_data: "Data export requires Starter or higher.",
    };

    const msg = message || defaultMessages[feature] || "This feature requires an upgrade.";
    
    showToast(`${msg} Upgrade for more!`, toastType);

    if (navigateToPricing) {
      setTimeout(() => navigate('/pricing'), 1500);
    }
  }, [showToast, navigate]);

  /**
   * Gate a feature - returns true if allowed, shows prompt if not
   */
  const gateFeature = useCallback((feature, currentUsage = 0) => {
    if (isLoading || !limitsData) {
      return false; // Don't allow while loading
    }

    const check = checkLimit(feature);
    
    // Boolean feature
    if (typeof check.allowed === 'boolean') {
      if (!check.allowed) {
        promptUpgrade(feature);
        return false;
      }
      return true;
    }

    // Numeric limit
    if (isLimitReached(feature)) {
      promptUpgrade(feature);
      return false;
    }

    return true;
  }, [isLoading, limitsData, checkLimit, isLimitReached, promptUpgrade]);

  /**
   * Get upgrade suggestion based on current tier
   */
  const getUpgradeSuggestion = useCallback(() => {
    switch (tier) {
      case 'free':
        return { tier: 'starter', name: 'Starter', price: 29 };
      case 'starter':
        return { tier: 'pro', name: 'Pro', price: 79 };
      case 'pro':
        return { tier: 'agency', name: 'Agency', price: 199 };
      default:
        return null;
    }
  }, [tier]);

  /**
   * Refresh limits from backend
   */
  const refetch = useCallback(async () => {
    try {
      const response = await api.get('/billing/user/limits');
      setLimitsData(response.data);
    } catch (err) {
      console.error('Failed to refresh limits:', err);
    }
  }, []);

  // Safe default limits structure
  const defaultLimits = {
    analyses_per_month: { limit: 5, used: 0, remaining: 5, unlimited: false },
    telegram_channels: { limit: 1, used: 0, remaining: 1, unlimited: false },
    suppliers: { limit: 3, used: 0, remaining: 3, unlimited: false },
    products_tracked: { limit: 250, used: 0, remaining: 250, unlimited: false },
  };

  return {
    tier,
    tierDisplay: limitsData?.tier_display || tier,
    isSuperAdmin,
    isUnlimited: isUnlimited, // Boolean: overall unlimited status
    limits: limitsData?.limits || defaultLimits, // Always return safe defaults
    isLoading,
    error,
    hasFeature,
    getLimit,
    isLimitReached,
    getRemaining,
    isFeatureUnlimited: isFeatureUnlimited, // Function: check if specific feature is unlimited
    checkLimit,
    promptUpgrade,
    gateFeature,
    getUpgradeSuggestion,
    refetch,
  };
}

