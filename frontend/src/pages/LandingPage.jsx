import { Box, Typography, Button, Container, Grid, Card, CardContent, Chip } from '@mui/material';
import { Link, useNavigate } from 'react-router-dom';
import { Zap, TrendingUp, Users, Shield, Check } from 'lucide-react';
import { habexa } from '../theme';

const LandingPage = () => {
  const navigate = useNavigate();

  const features = [
    {
      icon: <Zap size={32} />,
      title: 'Quick Analyze',
      description: 'Instant profitability analysis for any ASIN or UPC. Get profit margins, ROI, and deal scores in seconds.',
    },
    {
      icon: <TrendingUp size={32} />,
      title: 'Product Tracking',
      description: 'Monitor prices, rankings, and inventory across your product portfolio. Never miss a profitable opportunity.',
    },
    {
      icon: <Users size={32} />,
      title: 'Supplier Management',
      description: 'Organize suppliers, calculate margins, and track MOQ requirements. Streamline your sourcing workflow.',
    },
    {
      icon: <Shield size={32} />,
      title: 'Keepa Integration',
      description: 'Deep market analysis with historical pricing data, sales rank trends, and competitive intelligence.',
    },
  ];

  const pricingTiers = [
    {
      tier: 'Starter',
      price: 29,
      period: 'month',
      features: [
        '100 analyses/month',
        '250 products tracked',
        '3 suppliers',
        'Bulk analysis',
        'Data export',
      ],
      cta: 'Start Trial',
      href: '/register?plan=starter',
      highlighted: false,
    },
    {
      tier: 'Pro',
      price: 79,
      period: 'month',
      features: [
        '500 analyses/month',
        '1,000 products tracked',
        '50 suppliers',
        'Bulk analysis',
        'API access',
        'Priority support',
      ],
      cta: 'Start Trial',
      href: '/register?plan=pro',
      highlighted: true,
    },
    {
      tier: 'Agency',
      price: 199,
      period: 'month',
      features: [
        'Unlimited analyses',
        'Unlimited products',
        'Unlimited suppliers',
        'Bulk analysis',
        'API access',
        'Dedicated support',
        'Team collaboration',
      ],
      cta: 'Start Trial',
      href: '/register?plan=agency',
      highlighted: false,
    },
  ];

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
      {/* Navigation */}
      <Box
        sx={{
          position: 'sticky',
          top: 0,
          zIndex: 1000,
          bgcolor: 'background.paper',
          borderBottom: 1,
          borderColor: 'divider',
          py: 2,
        }}
      >
        <Container maxWidth="lg">
          <Box display="flex" justifyContent="space-between" alignItems="center">
            <Typography variant="h5" fontWeight={700} sx={{ color: habexa.purple.light }}>
              Habexa
            </Typography>
            <Box display="flex" gap={2}>
              <Button component={Link} to="/login" variant="text" color="inherit">
                Login
              </Button>
              <Button
                component={Link}
                to="/register"
                variant="contained"
                sx={{
                  bgcolor: habexa.purple.main,
                  '&:hover': { bgcolor: habexa.purple.dark },
                }}
              >
                Start Free Trial
              </Button>
            </Box>
          </Box>
        </Container>
      </Box>

      {/* Hero Section */}
      <Box
        sx={{
          py: { xs: 8, md: 12 },
          px: 2,
          background: `linear-gradient(135deg, ${habexa.purple.main}15 0%, ${habexa.purple.dark}15 100%)`,
        }}
      >
        <Container maxWidth="lg">
          <Box textAlign="center" maxWidth="800px" mx="auto">
            <Typography
              variant="h2"
              fontWeight={800}
              gutterBottom
              sx={{
                fontSize: { xs: '2.5rem', md: '3.5rem' },
                lineHeight: 1.2,
              }}
            >
              Amazon Product Research,{' '}
              <Box component="span" sx={{ color: habexa.purple.light }}>
                Simplified
              </Box>
            </Typography>
            <Typography
              variant="h6"
              color="text.secondary"
              sx={{ mt: 2, mb: 4, fontSize: { xs: '1rem', md: '1.25rem' } }}
            >
              Analyze ASINs, track products, find profitable opportunities — all in one platform.
              Start your 7-day free trial today.
            </Typography>
            <Box display="flex" gap={2} justifyContent="center" flexWrap="wrap">
              <Button
                component={Link}
                to="/register?trial=true"
                variant="contained"
                size="large"
                sx={{
                  bgcolor: habexa.purple.main,
                  px: 4,
                  py: 1.5,
                  fontSize: '1.1rem',
                  '&:hover': { bgcolor: habexa.purple.dark },
                }}
              >
                Start 7-Day Free Trial
              </Button>
              <Button
                onClick={() => {
                  const pricingSection = document.getElementById('pricing');
                  if (pricingSection) {
                    pricingSection.scrollIntoView({ behavior: 'smooth' });
                  }
                }}
                variant="outlined"
                size="large"
                sx={{
                  px: 4,
                  py: 1.5,
                  fontSize: '1.1rem',
                  borderColor: habexa.purple.main,
                  color: habexa.purple.light, // Changed for better contrast on dark bg
                  '&:hover': {
                    borderColor: habexa.purple.dark,
                    bgcolor: `${habexa.purple.main}10`,
                  },
                }}
              >
                View Pricing
              </Button>
            </Box>
          </Box>
        </Container>
      </Box>

      {/* Features Section */}
      <Box sx={{ py: { xs: 8, md: 12 }, px: 2 }}>
        <Container maxWidth="lg">
          <Typography
            variant="h3"
            fontWeight={700}
            textAlign="center"
            gutterBottom
            sx={{ mb: 6 }}
          >
            Everything You Need
          </Typography>
          <Grid container spacing={4}>
            {features.map((feature, index) => (
              <Grid item xs={12} sm={6} md={3} key={index}>
                <Card
                  sx={{
                    height: '100%',
                    p: 3,
                    textAlign: 'center',
                    transition: 'transform 0.2s, box-shadow 0.2s',
                    '&:hover': {
                      transform: 'translateY(-4px)',
                      boxShadow: 4,
                    },
                  }}
                >
                  <CardContent>
                    <Box
                      sx={{
                        color: habexa.purple.light, // Changed from purple.main for better contrast on dark bg
                        mb: 2,
                        display: 'flex',
                        justifyContent: 'center',
                      }}
                    >
                      {feature.icon}
                    </Box>
                    <Typography variant="h6" fontWeight={600} gutterBottom>
                      {feature.title}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {feature.description}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </Container>
      </Box>

      {/* Pricing Section */}
      <Box id="pricing" sx={{ py: { xs: 8, md: 12 }, px: 2, bgcolor: 'grey.50' }}>
        <Container maxWidth="lg">
          <Typography
            variant="h3"
            fontWeight={700}
            textAlign="center"
            gutterBottom
            sx={{ mb: 6 }}
          >
            Simple Pricing
          </Typography>
          <Grid container spacing={4} justifyContent="center">
            {pricingTiers.map((tier, index) => (
              <Grid item xs={12} sm={6} md={4} key={index}>
                <Card
                  sx={{
                    height: '100%',
                    p: 4,
                    position: 'relative',
                    border: tier.highlighted ? `2px solid ${habexa.purple.main}` : '1px solid',
                    borderColor: tier.highlighted ? habexa.purple.main : 'divider',
                    bgcolor: tier.highlighted ? `${habexa.purple.main}05` : 'background.paper',
                  }}
                >
                  {tier.highlighted && (
                    <Chip
                      label="Most Popular"
                      color="primary"
                      sx={{
                        position: 'absolute',
                        top: 16,
                        right: 16,
                        bgcolor: habexa.purple.main,
                      }}
                    />
                  )}
                  <Typography variant="h5" fontWeight={700} gutterBottom>
                    {tier.tier}
                  </Typography>
                  <Box display="flex" alignItems="baseline" mb={3}>
                    <Typography variant="h3" fontWeight={800} sx={{ color: habexa.purple.light }}>
                      ${tier.price}
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ ml: 1 }}>
                      /{tier.period}
                    </Typography>
                  </Box>
                  <Box component="ul" sx={{ listStyle: 'none', p: 0, m: 0, mb: 3 }}>
                    {tier.features.map((feature, i) => (
                      <Box
                        component="li"
                        key={i}
                        display="flex"
                        alignItems="center"
                        sx={{ mb: 1.5 }}
                      >
                        <Check size={18} style={{ color: habexa.success.main, marginRight: 8 }} />
                        <Typography variant="body2">{feature}</Typography>
                      </Box>
                    ))}
                  </Box>
                  <Button
                    component={Link}
                    to={tier.href}
                    variant={tier.highlighted ? 'contained' : 'outlined'}
                    fullWidth
                    sx={{
                      bgcolor: tier.highlighted ? habexa.purple.main : 'transparent',
                      borderColor: habexa.purple.main,
                      color: tier.highlighted ? 'white' : habexa.purple.light, // Changed for better contrast on dark bg
                      '&:hover': {
                        bgcolor: tier.highlighted ? habexa.purple.dark : `${habexa.purple.main}10`,
                        borderColor: habexa.purple.dark,
                      },
                    }}
                  >
                    {tier.cta}
                  </Button>
                </Card>
              </Grid>
            ))}
          </Grid>
        </Container>
      </Box>

      {/* Footer */}
      <Box sx={{ py: 6, px: 2, bgcolor: 'background.paper', borderTop: 1, borderColor: 'divider' }}>
        <Container maxWidth="lg">
          <Box textAlign="center">
            <Typography variant="body2" color="text.secondary">
              © {new Date().getFullYear()} Habexa. All rights reserved.
            </Typography>
          </Box>
        </Container>
      </Box>
    </Box>
  );
};

export default LandingPage;

