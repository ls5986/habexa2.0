import { useEffect } from 'react';
import { Box, Typography, Button, Card, CardContent } from '@mui/material';
import { CheckCircle, ArrowRight } from 'lucide-react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useStripe } from '../context/StripeContext';
import { habexa } from '../theme';
import api from '../services/api';

const BillingSuccess = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { refreshSubscription } = useStripe();
  const sessionId = searchParams.get('session_id');

  useEffect(() => {
    if (sessionId) {
      // First try to sync from session, then refresh
      const syncAndRefresh = async () => {
        try {
          await api.post(`/billing/sync?session_id=${sessionId}`);
        } catch (error) {
          console.warn('Failed to sync subscription from session:', error);
        }
        // Always refresh subscription after sync attempt
        refreshSubscription();
      };
      syncAndRefresh();
    }
  }, [sessionId, refreshSubscription]);

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        p: 3,
        backgroundColor: habexa.gray[50],
      }}
    >
      <Card sx={{ maxWidth: 500, width: '100%' }}>
        <CardContent sx={{ textAlign: 'center', p: 4 }}>
          <CheckCircle size={64} style={{ color: habexa.success.main, marginBottom: 16 }} />
          <Typography variant="h4" fontWeight={700} mb={2}>
            Payment Successful!
          </Typography>
          <Typography variant="body1" color="text.secondary" mb={4}>
            Your subscription has been activated. You now have access to all Pro features.
          </Typography>
          <Button
            variant="contained"
            fullWidth
            onClick={() => navigate('/dashboard')}
            endIcon={<ArrowRight size={18} />}
            sx={{
              backgroundColor: habexa.purple.main,
              '&:hover': { backgroundColor: habexa.purple.dark },
              py: 1.5,
            }}
          >
            Go to Dashboard
          </Button>
        </CardContent>
      </Card>
    </Box>
  );
};

export default BillingSuccess;

