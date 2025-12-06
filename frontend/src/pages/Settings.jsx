import { useState, useEffect } from 'react';
import { Box, Typography, Tabs, Tab, Card, CardContent, Button, Switch, FormControlLabel, Slider, TextField, CircularProgress, Chip, LinearProgress, Table, TableBody, TableRow, TableCell, Dialog, DialogTitle, DialogContent, DialogActions, Alert } from '@mui/material';
import { CheckCircle, CreditCard, Receipt, TrendingUp, ExternalLink } from 'lucide-react';
import { useSettings } from '../hooks/useSettings';
import { useToast } from '../context/ToastContext';
import { useStripe } from '../context/StripeContext';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { supabase } from '../services/supabase';
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
  const { subscription, openPortal, cancelSubscription, reactivateSubscription, refreshSubscription } = useStripe();
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

  // Password change form state
  const [passwordForm, setPasswordForm] = useState({
    current_password: '',
    new_password: '',
    confirm_password: '',
  });
  const [passwordError, setPasswordError] = useState('');
  const [passwordSuccess, setPasswordSuccess] = useState(false);
  const [changingPassword, setChangingPassword] = useState(false);

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
    inbound_rate_per_lb: 0.35,
    default_prep_cost: 0.10,
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
        inbound_rate_per_lb: costSettings.inbound_rate_per_lb || costSettings.default_inbound_shipping || 0.35,
        default_prep_cost: costSettings.default_prep_cost || 0.10,
      });
    }
  }, [costSettings]);

  useEffect(() => {
    if (tab === 4) {
      // ✅ OPTIMIZATION: Fetch invoices and usage in parallel (2x faster)
      const loadBillingData = async () => {
        try {
          const [invoicesRes, usageRes] = await Promise.all([
            api.get('/billing/invoices'),
            api.get('/billing/usage')
          ]);
          setInvoices(invoicesRes.data.invoices || []);
          setUsage(usageRes.data);
        } catch (error) {
          console.error('Failed to fetch billing data:', error);
          // If one fails, try to set the other
          try {
            const invoicesRes = await api.get('/billing/invoices');
            setInvoices(invoicesRes.data.invoices || []);
          } catch (err) {
            console.error('Failed to fetch invoices:', err);
          }
          try {
            const usageRes = await api.get('/billing/usage');
            setUsage(usageRes.data);
          } catch (err) {
            console.error('Failed to fetch usage:', err);
          }
        }
      };
      loadBillingData();
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

  const handleCancel = async (immediately = false) => {
    setActionLoading(true);
    try {
      if (immediately) {
        // Cancel immediately (for trials)
        await api.post('/billing/cancel-immediately');
        showToast('Subscription cancelled. You\'ve been moved to the Free plan.', 'info');
      } else {
        // Cancel at period end
        await cancelSubscription(true);
        showToast('Subscription will cancel at end of billing period', 'info');
      }
      setCancelDialogOpen(false);
      // Refresh subscription data without page reload
      await refreshSubscription();
      // Also refresh usage data
      await fetchUsage();
    } catch (error) {
      showToast(error.response?.data?.detail || 'Failed to cancel subscription', 'error');
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
      // Map to backend field names (backend may use different names)
      const dataToSave = {
        inbound_rate_per_lb: costForm.inbound_rate_per_lb,
        default_prep_cost: costForm.default_prep_cost,
        // Also send legacy field names for compatibility
        default_inbound_shipping: costForm.inbound_rate_per_lb,
      };
      await updateCostSettings(dataToSave);
      showToast('Cost settings saved', 'success');
    } catch (error) {
      showToast(error.message || 'Failed to save cost settings', 'error');
    }
  };

  const handleChangePassword = async () => {
    setPasswordError('');
    setPasswordSuccess(false);

    // Validation
    if (passwordForm.new_password !== passwordForm.confirm_password) {
      setPasswordError('New passwords do not match');
      return;
    }

    if (passwordForm.new_password.length < 8) {
      setPasswordError('Password must be at least 8 characters');
      return;
    }

    setChangingPassword(true);
    try {
      // Verify current password by attempting to sign in
      const { data: { user } } = await supabase.auth.getUser();
      
      if (!user) {
        throw new Error('Not authenticated');
      }

      // Verify current password by attempting to sign in with it
      const { error: signInError } = await supabase.auth.signInWithPassword({
        email: user.email,
        password: passwordForm.current_password,
      });

      if (signInError) {
        setPasswordError('Current password is incorrect');
        showToast('Current password is incorrect', 'error');
        return;
      }

      // Update password using Supabase
      const { error: updateError } = await supabase.auth.updateUser({
        password: passwordForm.new_password,
      });

      if (updateError) {
        throw updateError;
      }

      setPasswordSuccess(true);
      setPasswordForm({
        current_password: '',
        new_password: '',
        confirm_password: '',
      });
      showToast('Password changed successfully', 'success');
    } catch (error) {
      setPasswordError(error.message || 'Failed to change password');
      showToast(error.message || 'Failed to change password', 'error');
    } finally {
      setChangingPassword(false);
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
        <>
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

          {/* Change Password Card */}
          <Card sx={{ mt: 3 }}>
          <CardContent>
            <Typography variant="h6" fontWeight={600} mb={3}>
              Change Password
            </Typography>
            <Box display="flex" flexDirection="column" gap={3}>
              {passwordError && (
                <Alert severity="error">{passwordError}</Alert>
              )}
              {passwordSuccess && (
                <Alert severity="success">Password changed successfully!</Alert>
              )}
              <TextField
                label="Current Password"
                type="password"
                autoComplete="current-password"
                value={passwordForm.current_password}
                onChange={(e) => setPasswordForm({ ...passwordForm, current_password: e.target.value })}
                fullWidth
                required
              />
              <TextField
                label="New Password"
                type="password"
                autoComplete="new-password"
                value={passwordForm.new_password}
                onChange={(e) => setPasswordForm({ ...passwordForm, new_password: e.target.value })}
                fullWidth
                required
                inputProps={{ minLength: 8 }}
                helperText="Must be at least 8 characters"
              />
              <TextField
                label="Confirm New Password"
                type="password"
                autoComplete="new-password"
                value={passwordForm.confirm_password}
                onChange={(e) => setPasswordForm({ ...passwordForm, confirm_password: e.target.value })}
                fullWidth
                required
              />
              <Button
                variant="contained"
                onClick={handleChangePassword}
                disabled={changingPassword}
                sx={{
                  backgroundColor: habexa.purple.main,
                  '&:hover': { backgroundColor: habexa.purple.dark },
                  alignSelf: 'flex-start',
                }}
              >
                {changingPassword ? 'Changing...' : 'Change Password'}
              </Button>
            </Box>
          </CardContent>
        </Card>
        </>
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
            <Typography variant="h6" fontWeight={600} mb={1}>
              📦 Shipping & Prep Costs
            </Typography>
            <Typography variant="body2" color="text.secondary" mb={3}>
              These costs are included in all profit calculations
            </Typography>
            <Box display="flex" flexDirection="column" gap={3}>
              <TextField
                label="Inbound Shipping Rate"
                type="number"
                step="0.01"
                value={costForm.inbound_rate_per_lb}
                onChange={(e) => setCostForm({ ...costForm, inbound_rate_per_lb: parseFloat(e.target.value) || 0 })}
                InputProps={{
                  startAdornment: <InputAdornment position="start">$</InputAdornment>,
                  endAdornment: <InputAdornment position="end">/lb</InputAdornment>,
                }}
                fullWidth
                helperText="Cost to ship TO Amazon (typical: $0.30-0.50/lb)"
              />
              <TextField
                label="Default Prep Cost"
                type="number"
                step="0.01"
                value={costForm.default_prep_cost}
                onChange={(e) => setCostForm({ ...costForm, default_prep_cost: parseFloat(e.target.value) || 0 })}
                InputProps={{
                  startAdornment: <InputAdornment position="start">$</InputAdornment>,
                  endAdornment: <InputAdornment position="end">/unit</InputAdornment>,
                }}
                fullWidth
                helperText="Labeling, poly bags, etc. (typical: $0.10-0.30)"
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
                  {subscription?.status === 'trialing' && subscription?.trial_end && (
                    <Alert severity="info" sx={{ mt: 1, mb: 1 }}>
                      🎉 Free trial ends {new Date(subscription.trial_end).toLocaleDateString()}
                    </Alert>
                  )}
                  {subscription?.current_period_end && subscription?.status !== 'trialing' && (
                    <Typography variant="body2" color="text.secondary">
                      Renews: {new Date(subscription.current_period_end).toLocaleDateString()}
                    </Typography>
                  )}
                  {subscription?.cancel_at_period_end && (
                    <Alert severity="warning" sx={{ mt: 1 }}>
                      ⚠️ Cancels on {subscription?.current_period_end ? new Date(subscription.current_period_end).toLocaleDateString() : 'period end'}
                    </Alert>
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
              {subscription?.status === 'trialing' ? (
                <>
                  <Alert severity="warning" sx={{ mb: 2 }}>
                    Your trial will end immediately and you'll be downgraded to the Free plan.
                  </Alert>
                  <Typography variant="body2" color="text.secondary">
                    You can resubscribe anytime, but won't be eligible for another free trial.
                  </Typography>
                </>
              ) : (
                <>
                  <Alert severity="warning" sx={{ mb: 2 }}>
                    Your subscription will remain active until the end of your current billing period.
                    You'll continue to have access to all features until then.
                  </Alert>
                  <Typography variant="body2" color="text.secondary">
                    After cancellation, you'll be moved to the Free plan. You can reactivate anytime.
                  </Typography>
                </>
              )}
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setCancelDialogOpen(false)}>Keep Subscription</Button>
              <Button
                onClick={() => handleCancel(subscription?.status === 'trialing')}
                color="error"
                variant="contained"
                disabled={actionLoading}
              >
                {actionLoading ? 'Canceling...' : 'Yes, Cancel'}
              </Button>
            </DialogActions>
          </Dialog>
        </Box>
      )}
    </Box>
  );
};

export default Settings;
