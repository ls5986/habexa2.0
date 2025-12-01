import { Box, Dialog, DialogTitle, DialogContent, DialogActions, Button, Typography, Chip, Alert } from '@mui/material';
import { Rocket, Check } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useFeatureGate } from '../../hooks/useFeatureGate';
import { habexa } from '../../theme';

const FEATURE_BENEFITS = {
  telegram_channels: {
    title: 'More Telegram Channels',
    benefits: [
      'Monitor more supplier channels',
      'Never miss a deal',
      'Auto-extract from all channels',
    ],
  },
  analyses_per_month: {
    title: 'More Analyses',
    benefits: [
      'Analyze more products',
      'Find more profitable deals',
      'Scale your sourcing',
    ],
  },
  suppliers: {
    title: 'More Suppliers',
    benefits: [
      'Track more suppliers',
      'Better deal flow',
      'More opportunities',
    ],
  },
  bulk_analyze: {
    title: 'Bulk Analysis',
    benefits: [
      'Analyze 100s at once',
      'Save hours of time',
      'Process entire lists',
    ],
  },
  alerts: {
    title: 'Smart Alerts',
    benefits: [
      'Instant notifications',
      'Never miss a deal',
      'Custom thresholds',
    ],
  },
  api_access: {
    title: 'API Access',
    benefits: [
      'Build custom integrations',
      'Automate workflows',
      'Connect your tools',
    ],
  },
};

const UpgradePrompt = ({ 
  open, 
  onClose, 
  feature,
  currentUsage,
  limit 
}) => {
  const navigate = useNavigate();
  const { getUpgradeSuggestion, tier } = useFeatureGate();
  
  const suggestion = getUpgradeSuggestion();
  const featureInfo = FEATURE_BENEFITS[feature] || {
    title: 'Upgrade Required',
    benefits: ['Access premium features', 'Increase your limits', 'Scale your business'],
  };

  const handleUpgrade = () => {
    onClose();
    navigate('/pricing');
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        <Box display="flex" alignItems="center" gap={1}>
          <Rocket size={20} style={{ color: habexa.purple.main }} />
          <Typography variant="h6">
            {featureInfo.title}
          </Typography>
        </Box>
      </DialogTitle>
      
      <DialogContent>
        {currentUsage !== undefined && limit !== undefined && (
          <Alert severity="warning" sx={{ mb: 2 }}>
            You've used <strong>{currentUsage}</strong> of <strong>{limit}</strong> {feature.replace(/_/g, ' ')}.
          </Alert>
        )}

        <Typography variant="body1" gutterBottom>
          Upgrade to <strong>{suggestion?.name}</strong> to get:
        </Typography>

        <Box sx={{ my: 2 }}>
          {featureInfo.benefits.map((benefit, i) => (
            <Box key={i} display="flex" alignItems="center" gap={1} mb={1}>
              <Check size={16} style={{ color: habexa.success.main }} />
              <Typography variant="body2">{benefit}</Typography>
            </Box>
          ))}
        </Box>

        {suggestion && (
          <Box 
            sx={{ 
              p: 2, 
              bgcolor: habexa.purple.lighter, 
              borderRadius: 2,
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}
          >
            <Box>
              <Typography variant="subtitle2" fontWeight={600} color={habexa.purple.main}>
                {suggestion.name} Plan
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Starting at ${suggestion.price}/month
              </Typography>
            </Box>
            <Chip label="Recommended" size="small" sx={{ backgroundColor: habexa.purple.main, color: 'white' }} />
          </Box>
        )}
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose}>Maybe Later</Button>
        <Button 
          variant="contained" 
          onClick={handleUpgrade}
          startIcon={<Rocket size={18} />}
          sx={{
            backgroundColor: habexa.purple.main,
            '&:hover': { backgroundColor: habexa.purple.dark },
          }}
        >
          View Plans
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default UpgradePrompt;

