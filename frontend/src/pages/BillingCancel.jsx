import { Box, Typography, Button, Card, CardContent } from '@mui/material';
import { XCircle, ArrowLeft } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { habexa } from '../theme';

const BillingCancel = () => {
  const navigate = useNavigate();

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
          <XCircle size={64} style={{ color: habexa.error.main, marginBottom: 16 }} />
          <Typography variant="h4" fontWeight={700} mb={2}>
            Payment Canceled
          </Typography>
          <Typography variant="body1" color="text.secondary" mb={4}>
            Your payment was canceled. No charges were made. You can try again anytime.
          </Typography>
          <Button
            variant="outlined"
            fullWidth
            onClick={() => navigate('/settings?tab=billing')}
            startIcon={<ArrowLeft size={18} />}
            sx={{
              borderColor: habexa.purple.main,
              color: habexa.purple.main,
              '&:hover': { borderColor: habexa.purple.dark, backgroundColor: habexa.purple.lighter },
              py: 1.5,
            }}
          >
            Back to Billing
          </Button>
        </CardContent>
      </Card>
    </Box>
  );
};

export default BillingCancel;

