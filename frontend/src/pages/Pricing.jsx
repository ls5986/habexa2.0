import { useState, useEffect } from 'react';
import { Box, Container, Typography, Card, CardContent, Button, Grid, Chip, Switch, FormControlLabel, List, ListItem, ListItemIcon, ListItemText, CircularProgress } from '@mui/material';
import { Check, Star } from 'lucide-react';
import { useStripe } from '../context/StripeContext';
import api from '../services/api';
import { habexa } from '../theme';
import { formatCurrency } from '../utils/formatters';

const Pricing = () => {
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [yearly, setYearly] = useState(false);
  const [checkoutLoading, setCheckoutLoading] = useState(null);
  const { subscription, createCheckout } = useStripe();

  useEffect(() => {
    fetchPlans();
  }, []);

  const fetchPlans = async () => {
    try {
      const response = await api.get('/billing/plans');
      setPlans(response.data.plans);
    } catch (error) {
      console.error('Failed to fetch plans:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubscribe = async (plan) => {
    setCheckoutLoading(plan.tier);
    try {
      const priceKey = yearly ? plan.price_keys.yearly : plan.price_keys.monthly;
      await createCheckout(priceKey);
    } catch (error) {
      console.error('Checkout failed:', error);
    } finally {
      setCheckoutLoading(null);
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

  return (
    <Container maxWidth="lg" sx={{ py: 8 }}>
      <Box textAlign="center" mb={6}>
        <Typography variant="h3" fontWeight={700} gutterBottom>
          Choose Your Plan
        </Typography>
        <Typography variant="h6" color="text.secondary" mb={3}>
          Start with a 14-day free trial. No credit card required.
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
                    disabled={isCurrentPlan || checkoutLoading === plan.tier}
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
                    {checkoutLoading === plan.tier ? (
                      <CircularProgress size={20} />
                    ) : isCurrentPlan ? (
                      'Current Plan'
                    ) : (
                      'Get Started'
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

