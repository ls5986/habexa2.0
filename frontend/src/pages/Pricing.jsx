import { useState, useEffect } from 'react';
import { Box, Container, Typography, Card, CardContent, Button, Grid, Chip, Switch, FormControlLabel, List, ListItem, ListItemIcon, ListItemText, CircularProgress, Alert } from '@mui/material';
import { Check, Star } from 'lucide-react';
import { useStripe } from '../context/StripeContext';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import api from '../services/api';
import { habexa } from '../theme';
import { formatCurrency } from '../utils/formatters';

const SUPER_ADMIN_EMAILS = ['lindsey@letsclink.com'];

const Pricing = () => {
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [yearly, setYearly] = useState(false);
  const [checkoutLoading, setCheckoutLoading] = useState(null);
  const [tierLoading, setTierLoading] = useState(null);
  const { subscription, createCheckout, setTier, resubscribe } = useStripe();
  const { user } = useAuth();
  const { showToast } = useToast();
  
  const isSuperAdmin = user?.email && SUPER_ADMIN_EMAILS.includes(user.email.toLowerCase());

  useEffect(() => {
    fetchPlans();
  }, []);

  const fetchPlans = async () => {
    try {
      const response = await api.get('/billing/plans');
      console.log('Plans response:', response.data);
      if (response.data && response.data.plans) {
        setPlans(response.data.plans);
      } else {
        console.error('No plans in response:', response.data);
        showToast('Failed to load plans', 'error');
      }
    } catch (error) {
      console.error('Failed to fetch plans:', error);
      showToast(error.response?.data?.detail || 'Failed to load pricing plans', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleSubscribe = async (plan) => {
    if (isSuperAdmin) {
      // Super admin: direct tier switch without payment
      setTierLoading(plan.tier);
      try {
        await setTier(plan.tier);
        showToast(`Tier switched to ${plan.name}`, 'success');
      } catch (error) {
        showToast(error.response?.data?.detail || 'Failed to switch tier', 'error');
      } finally {
        setTierLoading(null);
      }
    } else {
      // Regular user: check if cancelled/resubscribing
      const isCancelled = subscription?.status === 'canceled' || subscription?.status === 'none';
      const hadTrial = subscription?.had_free_trial === true;
      
      setCheckoutLoading(plan.tier);
      try {
        const priceKey = yearly ? plan.price_keys.yearly : plan.price_keys.monthly;
        
        if (isCancelled) {
          // Resubscribe (no trial if already had one)
          await resubscribe(priceKey);
        } else {
          // New subscription or upgrade (include trial if eligible)
          const includeTrial = !hadTrial;
          await createCheckout(priceKey, includeTrial);
        }
      } catch (error) {
        showToast(error.response?.data?.detail || 'Checkout failed', 'error');
      } finally {
        setCheckoutLoading(null);
      }
    }
  };

  const formatFeature = (key, value) => {
    if (typeof value === 'boolean') {
      return { text: formatKey(key), included: value };
    }
    if (value === -1) {
      return { text: `Unlimited ${formatKey(key)}`, included: true };
    }
    return { text: `${value} ${formatKey(key)}`, included: true };
  };

  const formatKey = (key) => {
    return key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
        <CircularProgress />
      </Box>
    );
  }

  if (plans.length === 0) {
    return (
      <Container maxWidth="lg" sx={{ py: 8 }}>
        <Box textAlign="center">
          <Typography variant="h4" fontWeight={700} mb={2}>
            No Plans Available
          </Typography>
          <Typography variant="body1" color="text.secondary" mb={3}>
            Unable to load pricing plans. Please try refreshing the page.
          </Typography>
          <Button
            variant="contained"
            onClick={fetchPlans}
            sx={{
              backgroundColor: habexa.purple.main,
              '&:hover': { backgroundColor: habexa.purple.dark },
            }}
          >
            Retry
          </Button>
        </Box>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ py: 8 }}>
      <Box textAlign="center" mb={6}>
        <Typography variant="h3" fontWeight={700} gutterBottom>
          Choose Your Plan
        </Typography>
        {isSuperAdmin && (
          <Alert severity="info" sx={{ mb: 2, maxWidth: 600, mx: 'auto' }}>
            Super Admin Mode: You can switch tiers instantly without payment.
          </Alert>
        )}
        <Typography variant="h6" color="text.secondary" mb={3}>
          {isSuperAdmin 
            ? 'Switch between tiers instantly' 
            : subscription?.had_free_trial 
              ? 'Choose your plan to continue using Habexa'
              : 'Start with a 7-day free trial. No credit card required.'}
        </Typography>
        <FormControlLabel
          control={
            <Switch
              checked={yearly}
              onChange={(e) => setYearly(e.target.checked)}
              sx={{
                '& .MuiSwitch-switchBase.Mui-checked': {
                  color: habexa.purple.main,
                },
                '& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track': {
                  backgroundColor: habexa.purple.main,
                },
              }}
            />
          }
          label={
            <Typography>
              Yearly <Chip label="Save 17%" size="small" sx={{ ml: 1, backgroundColor: habexa.success.light, color: habexa.success.main }} />
            </Typography>
          }
        />
      </Box>

      <Grid container spacing={4}>
        {plans.map((plan) => {
          const price = yearly ? plan.yearly_price : plan.monthly_price;
          const isCurrentPlan = subscription?.tier === plan.tier;
          const features = Object.entries(plan.features).map(([key, value]) => formatFeature(key, value));

          return (
            <Grid item xs={12} md={4} key={plan.tier}>
              <Card
                sx={{
                  height: '100%',
                  position: 'relative',
                  border: plan.popular ? `2px solid ${habexa.purple.main}` : '1px solid',
                  borderColor: plan.popular ? habexa.purple.main : 'divider',
                  boxShadow: plan.popular ? `0 8px 24px rgba(124, 106, 250, 0.2)` : 'none',
                }}
              >
                {plan.popular && (
                  <Chip
                    icon={<Star size={16} />}
                    label="Most Popular"
                    sx={{
                      position: 'absolute',
                      top: 16,
                      right: 16,
                      backgroundColor: habexa.purple.main,
                      color: 'white',
                      fontWeight: 600,
                    }}
                  />
                )}
                <CardContent sx={{ p: 4 }}>
                  <Typography variant="h5" fontWeight={700} mb={1}>
                    {plan.name}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" mb={3}>
                    {plan.description}
                  </Typography>
                  <Box mb={3}>
                    <Typography variant="h3" fontWeight={700} component="span">
                      {formatCurrency(price)}
                    </Typography>
                    <Typography variant="body2" color="text.secondary" component="span">
                      /{yearly ? 'year' : 'month'}
                    </Typography>
                  </Box>

                  <List sx={{ mb: 3 }}>
                    {features.map((feature, idx) => (
                      <ListItem key={idx} sx={{ px: 0 }}>
                        <ListItemIcon sx={{ minWidth: 32 }}>
                          {feature.included ? (
                            <Check size={20} style={{ color: habexa.success.main }} />
                          ) : (
                            <Box sx={{ width: 20, height: 20, borderRadius: '50%', border: `2px solid ${habexa.gray[300]}` }} />
                          )}
                        </ListItemIcon>
                        <ListItemText
                          primary={feature.text}
                          primaryTypographyProps={{
                            color: feature.included ? 'text.primary' : 'text.disabled',
                          }}
                        />
                      </ListItem>
                    ))}
                  </List>

                  <Button
                    fullWidth
                    variant={plan.popular ? 'contained' : 'outlined'}
                    onClick={() => handleSubscribe(plan)}
                    disabled={isCurrentPlan || checkoutLoading === plan.tier || tierLoading === plan.tier}
                    sx={{
                      backgroundColor: plan.popular ? habexa.purple.main : 'transparent',
                      borderColor: habexa.purple.main,
                      color: plan.popular ? 'white' : habexa.purple.main,
                      '&:hover': {
                        backgroundColor: plan.popular ? habexa.purple.dark : habexa.purple.lighter,
                      },
                      py: 1.5,
                    }}
                  >
                    {(checkoutLoading === plan.tier || tierLoading === plan.tier) ? (
                      <CircularProgress size={20} />
                    ) : isCurrentPlan ? (
                      'Current Plan'
                    ) : isSuperAdmin ? (
                      'Switch to This Plan'
                    ) : subscription?.status === 'canceled' || subscription?.status === 'none' ? (
                      'Resubscribe'
                    ) : (
                      subscription?.had_free_trial ? 'Subscribe' : 'Start Free Trial'
                    )}
                  </Button>
                </CardContent>
              </Card>
            </Grid>
          );
        })}
      </Grid>
    </Container>
  );
};

export default Pricing;

