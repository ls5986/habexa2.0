import { Card, CardContent, Typography, Box, Button, Divider } from '@mui/material';
import { TrendingUp } from 'lucide-react';
import { useStripe } from '../../../context/StripeContext';
import { useFeatureGate } from '../../../hooks/useFeatureGate';
import UsageDisplay from '../../common/UsageDisplay';
import { useNavigate } from 'react-router-dom';
import { habexa } from '../../../theme';

const UsageWidget = () => {
  const navigate = useNavigate();
  const { subscription } = useStripe();
  const { tier, getLimit, getUpgradeSuggestion } = useFeatureGate();
  
  const suggestion = getUpgradeSuggestion();

  // Get usage data
  const analyses = {
    used: subscription?.analyses_used || 0,
    limit: getLimit('analyses_per_month'),
  };

  return (
    <Card>
      <CardContent>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Typography variant="h6" fontWeight={600}>Usage</Typography>
          <Typography 
            variant="caption" 
            sx={{ 
              px: 1.5, 
              py: 0.5, 
              bgcolor: habexa.purple.lighter, 
              borderRadius: 1,
              color: habexa.purple.main,
              fontWeight: 600,
              textTransform: 'uppercase'
            }}
          >
            {tier}
          </Typography>
        </Box>

        <Box sx={{ '& > *:not(:last-child)': { mb: 2 } }}>
          <UsageDisplay
            label="Analyses This Month"
            used={analyses.used}
            limit={analyses.limit}
          />
        </Box>

        {suggestion && (
          <>
            <Divider sx={{ my: 2 }} />
            <Box 
              sx={{ 
                p: 1.5, 
                bgcolor: habexa.gray[100], 
                borderRadius: 2,
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}
            >
              <Box>
                <Typography variant="body2" fontWeight={600}>
                  Need more?
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Upgrade to {suggestion.name}
                </Typography>
              </Box>
              <Button 
                size="small" 
                variant="outlined"
                startIcon={<TrendingUp size={16} />}
                onClick={() => navigate('/pricing')}
                sx={{
                  borderColor: habexa.purple.main,
                  color: habexa.purple.main,
                  '&:hover': { borderColor: habexa.purple.dark, backgroundColor: habexa.purple.lighter },
                }}
              >
                Upgrade
              </Button>
            </Box>
          </>
        )}
      </CardContent>
    </Card>
  );
};

export default UsageWidget;

