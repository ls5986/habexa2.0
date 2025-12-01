import { useState, useEffect } from 'react';
import { Box, Typography, Tabs, Tab, Card, CardContent, Button, Switch, FormControlLabel, Slider, TextField, CircularProgress, Chip, LinearProgress, Table, TableBody, TableRow, TableCell, Dialog, DialogTitle, DialogContent, DialogActions, Alert } from '@mui/material';
import { CheckCircle, CreditCard, Receipt, TrendingUp, ExternalLink } from 'lucide-react';
import { useSettings } from '../hooks/useSettings';
import { useToast } from '../context/ToastContext';
import { useStripe } from '../context/StripeContext';
import { useNavigate, useSearchParams } from 'react-router-dom';
import api from '../services/api';
import AmazonConnect from '../components/features/settings/AmazonConnect';
import TelegramConnect from '../components/features/settings/TelegramConnect';
import { habexa } from '../theme';
import { formatCurrency } from '../utils/formatters';

const Settings = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const tabParam = searchParams.get('tab');
  
  // Map tab names to indices
  const tabMap = {
    'profile': 0,
    'integrations': 1,
    'alerts': 2,
    'costs': 3,
    'billing': 4,
  };
  
  const initialTab = tabParam && tabMap[tabParam] !== undefined ? tabMap[tabParam] : 0;
  const [tab, setTab] = useState(initialTab);
  
  // Update tab when URL param changes
  useEffect(() => {
    if (tabParam && tabMap[tabParam] !== undefined) {
      setTab(tabMap[tabParam]);
    }
  }, [tabParam, searchParams]);
  const { profile, alertSettings, costSettings, loading, updateProfile, updateAlertSettings, updateCostSettings } = useSettings();
  const { showToast } = useToast();
  const { subscription, openPortal, cancelSubscription, reactivateSubscription } = useStripe();
  const navigate = useNavigate();
  
  // Billing state
  const [invoices, setInvoices] = useState([]);
  const [usage, setUsage] = useState(null);
  const [cancelDialogOpen, setCancelDialogOpen] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  // Profile form state
  const [profileForm, setProfileForm] = useState({
    full_name: '',
    avatar_url: '',
  });

  // Alert settings form state
  const [alertForm, setAlertForm] = useState({
    min_roi: 20,
    min_profit: 3,
    max_rank: 100000,
    alerts_enabled: true,
    alert_min_roi: 30,
    alert_channels: ['push', 'email'],
  });

  // Cost settings form state
  const [costForm, setCostForm] = useState({
    default_prep_cost: 0.50,
    default_inbound_shipping: 0.50,
  });

  // Load data into forms
  useEffect(() => {
    if (profile) {
      setProfileForm({
        full_name: profile.full_name || '',
        avatar_url: profile.avatar_url || '',
      });
    }
  }, [profile]);

  useEffect(() => {
    if (alertSettings) {
      setAlertForm({
        min_roi: alertSettings.min_roi || 20,
        min_profit: alertSettings.min_profit || 3,
        max_rank: alertSettings.max_rank || 100000,
        alerts_enabled: alertSettings.alerts_enabled !== false,
        alert_min_roi: alertSettings.alert_min_roi || 30,
        alert_channels: alertSettings.alert_channels || ['push', 'email'],
      });
    }
  }, [alertSettings]);

  useEffect(() => {
    if (costSettings) {
      setCostForm({
        default_prep_cost: costSettings.default_prep_cost || 0.50,
        default_inbound_shipping: costSettings.default_inbound_shipping || 0.50,
      });
    }
  }, [costSettings]);

  useEffect(() => {
    if (tab === 4) {
      fetchInvoices();
      fetchUsage();
    }
  }, [tab]);

  const fetchInvoices = async () => {
    try {
      const response = await api.get('/billing/invoices');
      setInvoices(response.data.invoices || []);
    } catch (error) {
      console.error('Failed to fetch invoices:', error);
    }
  };

  const fetchUsage = async () => {
    try {
      const response = await api.get('/billing/usage');
      setUsage(response.data);
    } catch (error) {
      console.error('Failed to fetch usage:', error);
    }
  };

  const handleCancel = async () => {
    setActionLoading(true);
    try {
      await cancelSubscription(true);
      setCancelDialogOpen(false);
      showToast('Subscription will cancel at end of billing period', 'info');
    } catch (error) {
      showToast('Failed to cancel subscription', 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const handleReactivate = async () => {
    setActionLoading(true);
    try {
      await reactivateSubscription();
      showToast('Subscription reactivated', 'success');
    } catch (error) {
      showToast('Failed to reactivate subscription', 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const handleManageBilling = async () => {
    setActionLoading(true);
    try {
      await openPortal();
    } catch (error) {
      showToast('Failed to open billing portal', 'error');
      setActionLoading(false);
    }
  };

  const handleSaveProfile = async () => {
    try {
      await updateProfile(profileForm);
      showToast('Profile updated successfully', 'success');
    } catch (error) {
      showToast(error.message || 'Failed to update profile', 'error');
    }
  };

  const handleSaveAlerts = async () => {
    try {
      await updateAlertSettings(alertForm);
      showToast('Alert settings saved', 'success');
    } catch (error) {
      showToast(error.message || 'Failed to save alert settings', 'error');
    }
  };

  const handleSaveCosts = async () => {
    try {
      await updateCostSettings(costForm);
      showToast('Cost settings saved', 'success');
    } catch (error) {
      showToast(error.message || 'Failed to save cost settings', 'error');
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h4" fontWeight={700} mb={4}>
        Settings
      </Typography>

      <Tabs value={tab} onChange={(e, v) => setTab(v)} sx={{ mb: 4 }}>
        <Tab label="Profile" />
        <Tab label="Integrations" />
        <Tab label="Alerts" />
        <Tab label="Costs" />
        <Tab label="Billing" />
      </Tabs>

      {/* Profile Tab */}
      {tab === 0 && (
        <Card>
          <CardContent>
            <Typography variant="h6" fontWeight={600} mb={3}>
              Profile Settings
            </Typography>
            <Box display="flex" flexDirection="column" gap={3}>
              <TextField
                label="Full Name"
                value={profileForm.full_name}
                onChange={(e) => setProfileForm({ ...profileForm, full_name: e.target.value })}
                fullWidth
              />
              <TextField
                label="Avatar URL"
                value={profileForm.avatar_url}
                onChange={(e) => setProfileForm({ ...profileForm, avatar_url: e.target.value })}
                fullWidth
                placeholder="https://..."
              />
              <Button
                variant="contained"
                onClick={handleSaveProfile}
                sx={{
                  backgroundColor: habexa.purple.main,
                  '&:hover': { backgroundColor: habexa.purple.dark },
                  alignSelf: 'flex-start',
                }}
              >
                Save Profile
              </Button>
            </Box>
          </CardContent>
        </Card>
      )}

      {/* Integrations Tab */}
      {tab === 1 && (
        <Box display="flex" flexDirection="column" gap={2}>
          <AmazonConnect />
          <TelegramConnect />
        </Box>
      )}

      {/* Alerts Tab */}
      {tab === 2 && (
        <Card>
          <CardContent>
            <Typography variant="h6" fontWeight={600} mb={3}>
              Alert Settings
            </Typography>
            <Box display="flex" flexDirection="column" gap={3}>
              <Box>
                <Typography variant="body2" color="text.secondary" mb={1}>
                  Minimum ROI for alerts
                </Typography>
                <Slider
                  value={alertForm.alert_min_roi}
                  onChange={(e, v) => setAlertForm({ ...alertForm, alert_min_roi: v })}
                  min={0}
                  max={100}
                  valueLabelDisplay="auto"
                  valueLabelFormat={(value) => `${value}%`}
                />
              </Box>
              <Box>
                <Typography variant="body2" color="text.secondary" mb={1}>
                  Minimum ROI to consider profitable
                </Typography>
                <Slider
                  value={alertForm.min_roi}
                  onChange={(e, v) => setAlertForm({ ...alertForm, min_roi: v })}
                  min={0}
                  max={100}
                  valueLabelDisplay="auto"
                  valueLabelFormat={(value) => `${value}%`}
                />
              </Box>
              <TextField
                label="Minimum profit per unit"
                type="number"
                value={alertForm.min_profit}
                onChange={(e) => setAlertForm({ ...alertForm, min_profit: parseFloat(e.target.value) || 0 })}
                InputProps={{ startAdornment: '$' }}
                fullWidth
              />
              <TextField
                label="Maximum sales rank"
                type="number"
                value={alertForm.max_rank}
                onChange={(e) => setAlertForm({ ...alertForm, max_rank: parseInt(e.target.value) || 0 })}
                fullWidth
              />
              <FormControlLabel
                control={
                  <Switch
                    checked={alertForm.alerts_enabled}
                    onChange={(e) => setAlertForm({ ...alertForm, alerts_enabled: e.target.checked })}
                  />
                }
                label="Enable alerts"
              />
              <Box>
                <Typography variant="body2" color="text.secondary" mb={1}>
                  Notification Channels
                </Typography>
                <FormControlLabel
                  control={
                    <Switch
                      checked={alertForm.alert_channels?.includes('push')}
                      onChange={(e) => {
                        const channels = alertForm.alert_channels || [];
                        if (e.target.checked) {
                          setAlertForm({ ...alertForm, alert_channels: [...channels, 'push'] });
                        } else {
                          setAlertForm({ ...alertForm, alert_channels: channels.filter(c => c !== 'push') });
                        }
                      }}
                    />
                  }
                  label="Push notifications"
                />
                <FormControlLabel
                  control={
                    <Switch
                      checked={alertForm.alert_channels?.includes('email')}
                      onChange={(e) => {
                        const channels = alertForm.alert_channels || [];
                        if (e.target.checked) {
                          setAlertForm({ ...alertForm, alert_channels: [...channels, 'email'] });
                        } else {
                          setAlertForm({ ...alertForm, alert_channels: channels.filter(c => c !== 'email') });
                        }
                      }}
                    />
                  }
                  label="Email alerts"
                />
              </Box>
              <Button
                variant="contained"
                onClick={handleSaveAlerts}
                sx={{
                  backgroundColor: habexa.purple.main,
                  '&:hover': { backgroundColor: habexa.purple.dark },
                  alignSelf: 'flex-start',
                }}
              >
                Save Settings
              </Button>
            </Box>
          </CardContent>
        </Card>
      )}

      {/* Costs Tab */}
      {tab === 3 && (
        <Card>
          <CardContent>
            <Typography variant="h6" fontWeight={600} mb={3}>
              Cost Settings
            </Typography>
            <Box display="flex" flexDirection="column" gap={3}>
              <TextField
                label="Default Prep Cost"
                type="number"
                value={costForm.default_prep_cost}
                onChange={(e) => setCostForm({ ...costForm, default_prep_cost: parseFloat(e.target.value) || 0 })}
                InputProps={{ startAdornment: '$' }}
                fullWidth
                helperText="Default cost per unit for prep/packaging"
              />
              <TextField
                label="Default Inbound Shipping"
                type="number"
                value={costForm.default_inbound_shipping}
                onChange={(e) => setCostForm({ ...costForm, default_inbound_shipping: parseFloat(e.target.value) || 0 })}
                InputProps={{ startAdornment: '$' }}
                fullWidth
                helperText="Default cost per unit for inbound shipping to Amazon"
              />
              <Button
                variant="contained"
                onClick={handleSaveCosts}
                sx={{
                  backgroundColor: habexa.purple.main,
                  '&:hover': { backgroundColor: habexa.purple.dark },
                  alignSelf: 'flex-start',
                }}
              >
                Save Cost Settings
              </Button>
            </Box>
          </CardContent>
        </Card>
      )}

      {/* Billing Tab */}
      {tab === 4 && (
        <Box display="flex" flexDirection="column" gap={3}>
          {/* Current Plan */}
          <Card>
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={2}>
                <Box>
                  <Typography variant="h6" fontWeight={600} gutterBottom>
                    Current Plan
                  </Typography>
                  <Box display="flex" alignItems="center" gap={1} mb={1}>
                    <Chip
                      label={subscription?.tier?.toUpperCase() || 'FREE'}
                      color={subscription?.tier === 'free' ? 'default' : 'primary'}
                      sx={{ fontWeight: 600 }}
                    />
                    {subscription?.cancel_at_period_end && (
                      <Chip
                        label="Cancels at period end"
                        color="warning"
                        size="small"
                      />
                    )}
                  </Box>
                  {subscription?.current_period_end && (
                    <Typography variant="body2" color="text.secondary">
                      Renews: {new Date(subscription.current_period_end).toLocaleDateString()}
                    </Typography>
                  )}
                </Box>
                <Box display="flex" gap={1}>
                  {subscription?.cancel_at_period_end ? (
                    <Button
                      variant="outlined"
                      onClick={handleReactivate}
                      disabled={actionLoading}
                    >
                      Reactivate
                    </Button>
                  ) : subscription?.tier !== 'free' ? (
                    <Button
                      variant="outlined"
                      color="error"
                      onClick={() => setCancelDialogOpen(true)}
                      disabled={actionLoading}
                    >
                      Cancel
                    </Button>
                  ) : null}
                  <Button
                    variant="contained"
                    onClick={() => navigate('/pricing')}
                    sx={{
                      backgroundColor: habexa.purple.main,
                      '&:hover': { backgroundColor: habexa.purple.dark },
                    }}
                  >
                    {subscription?.tier === 'free' ? 'Upgrade' : 'Change Plan'}
                  </Button>
                </Box>
              </Box>

              {subscription?.tier !== 'free' && (
                <Button
                  fullWidth
                  variant="outlined"
                  startIcon={<CreditCard size={18} />}
                  onClick={handleManageBilling}
                  disabled={actionLoading}
                  sx={{ mt: 2 }}
                >
                  Manage Billing & Payment Methods
                </Button>
              )}
            </CardContent>
          </Card>

          {/* Usage Stats */}
          {usage && (
            <Card>
              <CardContent>
                <Typography variant="h6" fontWeight={600} mb={2}>
                  Usage This Period
                </Typography>
                <Box mb={2}>
                  <Box display="flex" justifyContent="space-between" mb={1}>
                    <Typography variant="body2" color="text.secondary">
                      Analyses
                    </Typography>
                    <Typography variant="body2" fontWeight={600}>
                      {usage.analyses.used} / {usage.analyses.unlimited ? '∞' : usage.analyses.limit}
                    </Typography>
                  </Box>
                  {!usage.analyses.unlimited && (
                    <LinearProgress
                      variant="determinate"
                      value={Math.min((usage.analyses.used / usage.analyses.limit) * 100, 100)}
                      sx={{
                        height: 8,
                        borderRadius: 4,
                        backgroundColor: habexa.gray[200],
                        '& .MuiLinearProgress-bar': {
                          backgroundColor: usage.analyses.used >= usage.analyses.limit * 0.9 ? habexa.error.main : habexa.purple.main,
                        },
                      }}
                    />
                  )}
                </Box>
              </CardContent>
            </Card>
          )}

          {/* Invoices */}
          <Card>
            <CardContent>
              <Typography variant="h6" fontWeight={600} mb={2}>
                Invoice History
              </Typography>
              {invoices.length === 0 ? (
                <Typography variant="body2" color="text.secondary">
                  No invoices yet
                </Typography>
              ) : (
                <Table size="small">
                  <TableBody>
                    {invoices.map((invoice) => (
                      <TableRow key={invoice.id}>
                        <TableCell>
                          <Typography variant="body2" fontWeight={600}>
                            {new Date(invoice.created_at).toLocaleDateString()}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" color="text.secondary">
                            {formatCurrency((invoice.amount_paid || invoice.amount_due || 0) / 100)}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={invoice.status}
                            size="small"
                            color={invoice.status === 'paid' ? 'success' : 'default'}
                          />
                        </TableCell>
                        <TableCell align="right">
                          {invoice.stripe_invoice_url && (
                            <Button
                              size="small"
                              startIcon={<ExternalLink size={14} />}
                              href={invoice.stripe_invoice_url}
                              target="_blank"
                            >
                              View
                            </Button>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>

          {/* Cancel Dialog */}
          <Dialog open={cancelDialogOpen} onClose={() => setCancelDialogOpen(false)}>
            <DialogTitle>Cancel Subscription?</DialogTitle>
            <DialogContent>
              <Alert severity="warning" sx={{ mb: 2 }}>
                Your subscription will remain active until the end of your current billing period.
                You'll continue to have access to all features until then.
              </Alert>
              <Typography variant="body2" color="text.secondary">
                After cancellation, you'll be moved to the Free plan. You can reactivate anytime.
              </Typography>
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setCancelDialogOpen(false)}>Keep Subscription</Button>
              <Button
                onClick={handleCancel}
                color="error"
                variant="contained"
                disabled={actionLoading}
              >
                {actionLoading ? 'Canceling...' : 'Cancel Subscription'}
              </Button>
            </DialogActions>
          </Dialog>
        </Box>
      )}
    </Box>
  );
};

export default Settings;
