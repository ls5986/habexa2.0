import { useCallback } from 'react';
import { useStripe } from '../context/StripeContext';
import { useNavigate } from 'react-router-dom';
import { useToast } from '../context/ToastContext';

// Tier limits (mirror of backend)
const TIER_LIMITS = {
  free: {
    telegram_channels: 1,
    analyses_per_month: 10,
    suppliers: 3,
    alerts: false,
    bulk_analyze: false,
    api_access: false,
    team_seats: 1,
    export_data: false,
  },
  starter: {
    telegram_channels: 3,
    analyses_per_month: 100,
    suppliers: 10,
    alerts: true,
    bulk_analyze: false,
    api_access: false,
    team_seats: 1,
    export_data: true,
  },
  pro: {
    telegram_channels: 10,
    analyses_per_month: 500,
    suppliers: 50,
    alerts: true,
    bulk_analyze: true,
    api_access: false,
    team_seats: 3,
    export_data: true,
  },
  agency: {
    telegram_channels: -1,
    analyses_per_month: -1,
    suppliers: -1,
    alerts: true,
    bulk_analyze: true,
    api_access: true,
    team_seats: 10,
    export_data: true,
  },
};

export function useFeatureGate() {
  const { subscription } = useStripe();
  const navigate = useNavigate();
  const { showToast } = useToast();

  const tier = subscription?.tier || 'free';
  const limits = TIER_LIMITS[tier] || TIER_LIMITS.free;

  /**
   * Check if user has access to a boolean feature
   */
  const hasFeature = useCallback((feature) => {
    return limits[feature] === true;
  }, [limits]);

  /**
   * Get the limit for a numeric feature
   * Returns -1 for unlimited
   */
  const getLimit = useCallback((feature) => {
    return limits[feature] ?? 0;
  }, [limits]);

  /**
   * Check if a numeric limit has been reached
   */
  const isLimitReached = useCallback((feature, currentUsage) => {
    const limit = limits[feature];
    if (limit === -1) return false; // Unlimited
    return currentUsage >= limit;
  }, [limits]);

  /**
   * Get remaining count for a numeric feature
   */
  const getRemaining = useCallback((feature, currentUsage) => {
    const limit = limits[feature];
    if (limit === -1) return Infinity;
    return Math.max(0, limit - currentUsage);
  }, [limits]);

  /**
   * Check if feature is unlimited
   */
  const isUnlimited = useCallback((feature) => {
    return limits[feature] === -1;
  }, [limits]);

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
    // Boolean feature
    if (typeof limits[feature] === 'boolean') {
      if (!limits[feature]) {
        promptUpgrade(feature);
        return false;
      }
      return true;
    }

    // Numeric limit
    if (isLimitReached(feature, currentUsage)) {
      promptUpgrade(feature);
      return false;
    }

    return true;
  }, [limits, isLimitReached, promptUpgrade]);

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

  return {
    tier,
    limits,
    hasFeature,
    getLimit,
    isLimitReached,
    getRemaining,
    isUnlimited,
    promptUpgrade,
    gateFeature,
    getUpgradeSuggestion,
  };
}

