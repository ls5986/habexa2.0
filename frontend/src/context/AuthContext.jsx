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

  useEffect(() => {
    // Check for existing session
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session) {
        setUser(session.user);
        localStorage.setItem('auth_token', session.access_token);
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
      } else {
        setUser(null);
        localStorage.removeItem('auth_token');
      }
      setLoading(false);
    });

    return () => subscription.unsubscribe();
  }, []);

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
    signUp,
    signIn,
    signOut,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

