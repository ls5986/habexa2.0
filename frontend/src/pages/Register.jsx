import { useState, useEffect } from 'react';
import { Box, Card, CardContent, TextField, Button, Typography, Link } from '@mui/material';
import { useAuth } from '../context/AuthContext';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useStripe } from '../context/StripeContext';
import { habexa } from '../theme';

const Register = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { signUp } = useAuth();
  const { createCheckout } = useStripe();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  
  const trialParam = searchParams.get('trial');
  const planParam = searchParams.get('plan');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await signUp(email, password, fullName);
      
      // If trial=true or plan is specified, redirect to checkout
      if (trialParam === 'true' || planParam) {
        // Determine price key based on plan
        const priceKeyMap = {
          'starter': 'starter_monthly',
          'pro': 'pro_monthly',
          'agency': 'agency_monthly'
        };
        const priceKey = planParam ? priceKeyMap[planParam] || 'starter_monthly' : 'starter_monthly';
        const includeTrial = trialParam === 'true' || !planParam; // Include trial if trial=true or no plan specified
        
        try {
          await createCheckout(priceKey, includeTrial);
          // createCheckout redirects to Stripe, so we don't need to navigate
        } catch (checkoutError) {
          console.error('Checkout error:', checkoutError);
          // If checkout fails, still navigate to dashboard
          navigate('/dashboard');
        }
      } else {
        // Normal signup - go to dashboard
        navigate('/dashboard');
      }
    } catch (err) {
      setError(err.message || 'Failed to create account');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: 'background.default',
      }}
    >
      <Card sx={{ width: '100%', maxWidth: 400 }}>
        <CardContent sx={{ p: 4 }}>
          <Box sx={{ display: 'flex', justifyContent: 'center', mb: 3 }}>
            <img 
              src="/logos/fulllogo@300x.png" 
              alt="Habexa" 
              style={{ height: 48, maxWidth: '100%' }}
            />
          </Box>
          <Typography variant="body2" color="text.secondary" mb={4} textAlign="center">
            Create your account
          </Typography>

          {error && (
            <Typography color="error" variant="body2" mb={2}>
              {error}
            </Typography>
          )}

          <form onSubmit={handleSubmit}>
            <TextField
              fullWidth
              label="Full Name"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              required
              sx={{ mb: 2 }}
            />
            <TextField
              fullWidth
              label="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              sx={{ mb: 2 }}
            />
            <TextField
              fullWidth
              label="Password"
              type="password"
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              sx={{ mb: 3 }}
            />
            <Button
              type="submit"
              fullWidth
              variant="contained"
              disabled={loading}
              sx={{
                backgroundColor: habexa.purple.main,
                '&:hover': { backgroundColor: habexa.purple.dark },
                mb: 2,
              }}
            >
              {loading ? 'Creating account...' : 'Sign Up'}
            </Button>
          </form>

          <Typography variant="body2" textAlign="center">
            Already have an account?{' '}
            <Link href="/login" sx={{ color: habexa.purple.main, fontWeight: 600 }}>
              Sign in
            </Link>
          </Typography>
        </CardContent>
      </Card>
    </Box>
  );
};

export default Register;

