import { useState } from 'react';
import { Box, Card, CardContent, TextField, Button, Typography, Link } from '@mui/material';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';

const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { signIn } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await signIn(email, password);
      navigate('/dashboard');
    } catch (err) {
      setError(err.message || 'Failed to sign in');
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
        backgroundColor: '#F9FAFB',
      }}
    >
      <Card sx={{ width: '100%', maxWidth: 400 }}>
        <CardContent sx={{ p: 4 }}>
          <Typography variant="h4" fontWeight={700} mb={1} textAlign="center" color="#1A1A4E">
            Habexa
          </Typography>
          <Typography variant="body2" color="text.secondary" mb={4} textAlign="center">
            Sign in to your account
          </Typography>

          {error && (
            <Typography color="error" variant="body2" mb={2}>
              {error}
            </Typography>
          )}

          <form onSubmit={handleSubmit}>
            <TextField
              fullWidth
              label="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              inputProps={{ autoComplete: "email" }}
              sx={{ mb: 2 }}
            />
            <TextField
              fullWidth
              label="Password"
              type="password"
              autoComplete="current-password"
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
                backgroundColor: '#7C3AED', // Changed from #7C6AFA for better contrast (5.1:1 on light bg)
                color: '#FFFFFF',
                '&:hover': { backgroundColor: '#6D28D9' },
                mb: 2,
              }}
            >
              {loading ? 'Signing in...' : 'Sign In'}
            </Button>
          </form>

          <Typography variant="body2" textAlign="center">
            Don't have an account?{' '}
            <Link href="/register" sx={{ color: '#7C3AED', fontWeight: 600 }}>
              Sign up
            </Link>
          </Typography>
        </CardContent>
      </Card>
    </Box>
  );
};

export default Login;

