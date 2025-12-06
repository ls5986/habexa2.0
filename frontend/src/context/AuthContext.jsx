import { createContext, useContext, useState, useEffect } from 'react';
import { supabase } from '../services/supabase';
import api from '../services/api';

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [tier, setTier] = useState(null);
  const [limits, setLimits] = useState(null);
  const [tierLoading, setTierLoading] = useState(false);

  // Load user tier and limits
  const loadUserTier = async (userId) => {
    if (!userId) {
      setTier(null);
      setLimits(null);
      return;
    }

    try {
      setTierLoading(true);
      const response = await api.get('/auth/me');
      setTier(response.data.tier);
      setLimits(response.data.limits);
    } catch (error) {
      console.error('Failed to load user tier:', error);
      // Fallback to free tier on error
      setTier('free');
      setLimits({
        analyses_per_month: { limit: 5, used: 0, remaining: 5, unlimited: false },
        telegram_channels: { limit: 1, used: 0, remaining: 1, unlimited: false },
        suppliers: { limit: 3, used: 0, remaining: 3, unlimited: false },
      });
    } finally {
      setTierLoading(false);
    }
  };

  // Refresh tier (called after subscription changes)
  const refreshTier = async () => {
    if (user?.id) {
      await loadUserTier(user.id);
    }
  };

  useEffect(() => {
    // Check for existing session
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session) {
        setUser(session.user);
        localStorage.setItem('auth_token', session.access_token);
        // Load tier and limits
        loadUserTier(session.user.id);
      }
      setLoading(false);
    });

    // Listen for auth changes
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      if (session) {
        setUser(session.user);
        localStorage.setItem('auth_token', session.access_token);
        // Load tier and limits
        loadUserTier(session.user.id);
      } else {
        setUser(null);
        setTier(null);
        setLimits(null);
        localStorage.removeItem('auth_token');
      }
      setLoading(false);
    });

    // ✅ Listen for tier refresh events (from StripeContext after subscription changes)
    const handleRefreshTier = () => {
      if (user?.id) {
        loadUserTier(user.id);
      }
    };
    window.addEventListener('refreshTier', handleRefreshTier);

    return () => {
      subscription.unsubscribe();
      window.removeEventListener('refreshTier', handleRefreshTier);
    };
  }, [user?.id]);

  const signUp = async (email, password, fullName) => {
    try {
      // Step 1: Create auth user
      const { data, error: signUpError } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: {
            full_name: fullName,
          },
        },
      });

      // Handle Supabase auth errors with specific messages
      if (signUpError) {
        // Email already exists
        if (signUpError.message?.includes('already registered') || 
            signUpError.message?.includes('already exists') ||
            signUpError.message?.includes('User already registered')) {
          throw new Error('An account with this email already exists. Please sign in instead.');
        }

        // Invalid email format
        if (signUpError.message?.includes('Invalid email') || 
            signUpError.message?.includes('email format') ||
            signUpError.status === 400 && signUpError.message?.includes('email')) {
          throw new Error('Please enter a valid email address.');
        }

        // Password too weak
        if (signUpError.message?.includes('Password') || 
            signUpError.message?.includes('password') ||
            signUpError.message?.includes('weak')) {
          throw new Error('Password is too weak. Please use at least 8 characters with a mix of letters, numbers, and symbols.');
        }

        // Supabase service error (500)
        if (signUpError.status === 500 || signUpError.message?.includes('Internal Server Error')) {
          throw new Error('Registration service temporarily unavailable. Please try again in a moment.');
        }

        // Network error
        if (signUpError.message?.includes('Network') || 
            signUpError.message?.includes('fetch') ||
            signUpError.message?.includes('Failed to fetch')) {
          throw new Error('Network error. Please check your internet connection and try again.');
        }

        // Rate limiting
        if (signUpError.status === 429 || signUpError.message?.includes('rate limit')) {
          throw new Error('Too many signup attempts. Please wait a few minutes and try again.');
        }

        // Generic Supabase error - use the actual error message if available
        throw new Error(signUpError.message || 'Registration failed. Please try again.');
      }

      // Check if user was created
      if (!data.user) {
        throw new Error('Registration failed. Please try again.');
      }

      // Step 2: Create profile (non-blocking - don't fail signup if this fails)
      let profileCreated = false;
      try {
        const { error: profileError } = await supabase.from('profiles').insert({
          id: data.user.id,
          email: data.user.email,
          full_name: fullName,
        });

        if (profileError) {
          console.error('Profile creation failed:', profileError);
          
          // If profile insert fails due to duplicate, that's okay (profile might already exist)
          if (profileError.code === '23505' || profileError.message?.includes('duplicate')) {
            console.warn('Profile already exists, continuing...');
            profileCreated = true;
          } else {
            // For other errors, log but continue - user can complete profile later
            console.warn('Profile creation failed, but signup succeeded. User can complete profile later.');
          }
        } else {
          profileCreated = true;
        }
      } catch (profileErr) {
        console.error('Profile creation error:', profileErr);
        // Don't throw - allow signup to succeed even if profile creation fails
        // User can complete profile setup later
      }

      // Step 3: Initialize subscription and send welcome email (non-blocking)
      try {
        await api.post('/billing/initialize-subscription');
      } catch (initError) {
        // Log but don't fail signup if initialization fails
        console.warn('Failed to initialize subscription:', initError);
        // This is not critical - subscription can be initialized later
      }

      // Return success - maintain backward compatibility with original data structure
      // Also include additional info for debugging
      return {
        ...data, // Include original Supabase response (user, session, etc.)
        profileCreated, // Additional info about profile creation status
      };
    } catch (error) {
      // Re-throw our custom errors, or wrap unexpected errors
      if (error instanceof Error) {
        throw error;
      }
      // If it's not an Error object, wrap it
      throw new Error(error.message || 'Registration failed. Please try again.');
    }
  };

  const signIn = async (email, password) => {
    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    if (error) throw error;
    return data;
  };

  const signOut = async () => {
    const { error } = await supabase.auth.signOut();
    if (error) throw error;
  };

  const value = {
    user,
    loading,
    tier,
    limits,
    tierLoading,
    signUp,
    signIn,
    signOut,
    refreshTier,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

