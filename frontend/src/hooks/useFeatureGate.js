import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useToast } from '../context/ToastContext';
import { useAuth } from '../context/AuthContext';

export function useFeatureGate() {
  const navigate = useNavigate();
  const { showToast } = useToast();
  
  // ✅ Get tier and limits from AuthContext (no polling, instant access)
  const { tier, limits, tierLoading } = useAuth();
  
  // Map AuthContext data to match old format for backward compatibility
  const limitsData = limits ? {
    tier: tier || 'free',
    tier_display: (tier || 'free').charAt(0).toUpperCase() + (tier || 'free').slice(1),
    is_super_admin: false, // TODO: Add to AuthContext if needed
    unlimited: limits.analyses_per_month?.unlimited || false,
    limits: limits
  } : null;
  
  const isLoading = tierLoading;
  const error = null; // Errors handled in AuthContext
  
  // Extract tier info
  const tierName = tier || 'free';
  const isSuperAdmin = false; // TODO: Add to AuthContext if needed
  const isUnlimited = limits?.analyses_per_month?.unlimited || false;

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

