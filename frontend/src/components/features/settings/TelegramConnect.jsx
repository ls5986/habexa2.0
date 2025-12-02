import { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Button,
  Box,
  TextField,
  Chip,
  CircularProgress,
  Alert,
  Stepper,
  Step,
  StepLabel,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Tooltip,
  FormControlLabel,
  Checkbox,
  Divider,
} from '@mui/material';
import { CheckCircle, MessageCircle, Unlink, Play, Square, Plus, Trash2, RotateCw } from 'lucide-react';
import api from '../../../services/api';
import { useToast } from '../../../context/ToastContext';
import { useFeatureGate } from '../../../hooks/useFeatureGate';
import UsageDisplay from '../../common/UsageDisplay';
import { useTheme } from '@mui/material/styles';

const AUTH_STEPS = ['Enter Phone', 'Verify Code', 'Connected'];

const TelegramConnect = () => {
  const theme = useTheme();
  
  // Connection state
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  
  // Auth flow state
  const [authStep, setAuthStep] = useState(0);
  const [phone, setPhone] = useState('');
  const [code, setCode] = useState('');
  const [password, setPassword] = useState('');
  const [needs2FA, setNeeds2FA] = useState(false);
  const [authLoading, setAuthLoading] = useState(false);
  
  // Channel management
  const [channels, setChannels] = useState([]);
  const [availableChannels, setAvailableChannels] = useState([]);
  const [showChannelDialog, setShowChannelDialog] = useState(false);
  const [channelsLoading, setChannelsLoading] = useState(false);
  const [syncing, setSyncing] = useState({}); // Track which channel is syncing
  const [selectedChannel, setSelectedChannel] = useState(null);
  const [supplierDetails, setSupplierDetails] = useState({
    createSupplier: true,
    supplierName: '',
    supplierWebsite: '',
    supplierEmail: '',
    supplierNotes: '',
  });
  
  const { showToast } = useToast();
  const { getLimit, isLimitReached } = useFeatureGate();

  useEffect(() => {
    fetchStatus();
  }, []);

  const fetchStatus = async () => {
    try {
      const response = await api.get('/integrations/telegram/status');
      setStatus(response.data);
      
      if (response.data.connected) {
        fetchChannels();
      }
    } catch (error) {
      console.error('Failed to fetch Telegram status:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchChannels = async () => {
    try {
      const response = await api.get('/integrations/telegram/channels');
      setChannels(response.data.channels || []);
    } catch (error) {
      console.error('Failed to fetch channels:', error);
    }
  };

  // ==========================================
  // AUTH HANDLERS
  // ==========================================

  const handleStartAuth = async () => {
    if (!phone.trim()) {
      showToast('Please enter your phone number', 'error');
      return;
    }

    setAuthLoading(true);
    try {
      const response = await api.post('/integrations/telegram/auth/start', {
        phone_number: phone
      });
      
      showToast('Verification code sent to your Telegram app', 'success');
      setAuthStep(1);
    } catch (error) {
      showToast(error.response?.data?.detail || 'Failed to send code', 'error');
    } finally {
      setAuthLoading(false);
    }
  };

  const handleVerifyCode = async () => {
    if (!code.trim()) {
      showToast('Please enter the verification code', 'error');
      return;
    }

    setAuthLoading(true);
    try {
      const response = await api.post('/integrations/telegram/auth/verify', {
        code: code,
        password: needs2FA ? password : undefined
      });
      
      if (response.data.status === '2fa_required') {
        setNeeds2FA(true);
        showToast('Please enter your 2FA password', 'warning');
      } else if (response.data.status === 'connected') {
        showToast('Telegram connected successfully!', 'success');
        setAuthStep(2);
        fetchStatus();
      }
    } catch (error) {
      showToast(error.response?.data?.detail || 'Verification failed', 'error');
    } finally {
      setAuthLoading(false);
    }
  };

  const handleDisconnect = async () => {
    if (!confirm('Disconnect Telegram? You will stop receiving deals from your channels.')) {
      return;
    }

    try {
      await api.delete('/integrations/telegram/disconnect');
      setStatus({ connected: false });
      setChannels([]);
      setAuthStep(0);
      setPhone('');
      setCode('');
      showToast('Telegram disconnected', 'success');
    } catch (error) {
      showToast('Failed to disconnect', 'error');
    }
  };

  // ==========================================
  // CHANNEL HANDLERS
  // ==========================================

  const handleFetchAvailableChannels = async () => {
    setChannelsLoading(true);
    try {
      const response = await api.get('/integrations/telegram/channels/available');
      setAvailableChannels(response.data.channels || []);
      setShowChannelDialog(true);
    } catch (error) {
      showToast(error.response?.data?.detail || 'Failed to fetch channels', 'error');
    } finally {
      setChannelsLoading(false);
    }
  };

  const handleSelectChannel = (channel) => {
    setSelectedChannel(channel);
    setSupplierDetails({
      ...supplierDetails,
      supplierName: channel.title || channel.name || '',
    });
  };

  const handleAddChannel = async (channel = null) => {
    const targetChannel = channel || selectedChannel;
    if (!targetChannel) return;
    
    try {
      const payload = {
        channel_id: targetChannel.id,
        channel_name: targetChannel.name || targetChannel.title,
        channel_username: targetChannel.username,
        channel_type: targetChannel.type || 'channel',
        create_supplier: supplierDetails.createSupplier,
        supplier_name: supplierDetails.supplierName || targetChannel.name || targetChannel.title,
        supplier_website: supplierDetails.supplierWebsite || null,
        supplier_contact_email: supplierDetails.supplierEmail || null,
        supplier_notes: supplierDetails.supplierNotes || null,
      };
      
      const res = await api.post('/integrations/telegram/channels', payload);
      
      showToast(
        `Added ${targetChannel.name}${res.data.supplier_id ? ' and created supplier' : ''}`,
        'success'
      );
      
      // Reset form
      setSelectedChannel(null);
      setSupplierDetails({
        createSupplier: true,
        supplierName: '',
        supplierWebsite: '',
        supplierEmail: '',
        supplierNotes: '',
      });
      
      fetchChannels();
      fetchStatus();
      
      // Update available channels list
      setAvailableChannels(prev => 
        prev.map(c => c.id === targetChannel.id ? { ...c, is_monitored: true } : c)
      );
      
      // Close dialog if open
      if (showChannelDialog) {
        setShowChannelDialog(false);
      }
    } catch (error) {
      showToast(error.response?.data?.detail || 'Failed to add channel', 'error');
    }
  };

  const handleBackfill = async (channelId) => {
    setSyncing(prev => ({ ...prev, [channelId]: true }));
    try {
      const response = await api.post(`/integrations/telegram/channels/${channelId}/backfill?days=14`);
      showToast(
        `Synced ${response.data.messages} messages, found ${response.data.deals} deals`,
        'success'
      );
      fetchChannels(); // Refresh channel list to update stats
    } catch (error) {
      showToast(
        'Failed to sync: ' + (error.response?.data?.detail || error.message),
        'error'
      );
    } finally {
      setSyncing(prev => ({ ...prev, [channelId]: false }));
    }
  };

  const handleRemoveChannel = async (channelId) => {
    try {
      await api.delete(`/integrations/telegram/channels/${channelId}`);
      showToast('Channel removed', 'success');
      fetchChannels();
      fetchStatus();
    } catch (error) {
      showToast('Failed to remove channel', 'error');
    }
  };

  // ==========================================
  // MONITORING HANDLERS
  // ==========================================

  const handleStartMonitoring = async () => {
    try {
      const response = await api.post('/integrations/telegram/monitoring/start');
      showToast(`Monitoring ${response.data.channels} channels`, 'success');
      fetchStatus();
    } catch (error) {
      showToast(error.response?.data?.detail || 'Failed to start monitoring', 'error');
    }
  };

  const handleStopMonitoring = async () => {
    try {
      await api.post('/integrations/telegram/monitoring/stop');
      showToast('Monitoring stopped', 'success');
      fetchStatus();
    } catch (error) {
      showToast('Failed to stop monitoring', 'error');
    }
  };

  // ==========================================
  // RENDER
  // ==========================================

  if (loading) {
    return (
      <Card>
        <CardContent sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
          <CircularProgress />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent>
        {/* Header */}
        <Box display="flex" alignItems="flex-start" justifyContent="space-between" mb={2}>
          <Box>
            <Box display="flex" alignItems="center" gap={1} mb={1}>
              <MessageCircle size={20} style={{ color: '#0088cc' }} />
              <Typography variant="h6" fontWeight={600}>Telegram Monitoring</Typography>
              <Chip
                icon={status?.connected ? <CheckCircle size={16} /> : undefined}
                label={status?.connected ? 'Connected' : 'Not Connected'}
                color={status?.connected ? 'success' : 'default'}
                size="small"
              />
              {status?.monitoring && (
                <Chip
                  label="Monitoring"
                  color="primary"
                  size="small"
                />
              )}
            </Box>
            <Typography variant="body2" color="text.secondary">
              Auto-extract deals from supplier channels
            </Typography>
          </Box>

          {status?.connected && (
            <Button
              variant="outlined"
              color="error"
              size="small"
              startIcon={<Unlink size={18} />}
              onClick={handleDisconnect}
            >
              Disconnect
            </Button>
          )}
        </Box>

        {/* Not Connected - Auth Flow */}
        {!status?.connected && (
          <Box>
            <Stepper activeStep={authStep} sx={{ mb: 3 }}>
              {AUTH_STEPS.map((label) => (
                <Step key={label}>
                  <StepLabel>{label}</StepLabel>
                </Step>
              ))}
            </Stepper>

            {authStep === 0 && (
              <Box>
                <Typography variant="body2" color="text.secondary" mb={2}>
                  Enter your phone number to connect your Telegram account.
                  We'll send a verification code to your Telegram app.
                </Typography>
                <TextField
                  label="Phone Number"
                  placeholder="+1 234 567 8900"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  fullWidth
                  sx={{ mb: 2 }}
                  helperText="Include country code (e.g., +1 for US)"
                />
                <Button
                  variant="contained"
                  onClick={handleStartAuth}
                  disabled={authLoading}
                  startIcon={authLoading ? <CircularProgress size={16} /> : <MessageCircle size={18} />}
                  sx={{ bgcolor: '#0088cc', '&:hover': { bgcolor: '#006699' } }}
                >
                  {authLoading ? 'Sending...' : 'Send Code'}
                </Button>
              </Box>
            )}

            {authStep === 1 && (
              <Box>
                <Alert severity="info" sx={{ mb: 2 }}>
                  Check your Telegram app for the verification code
                </Alert>
                <TextField
                  label="Verification Code"
                  placeholder="12345"
                  value={code}
                  onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
                  fullWidth
                  autoFocus
                  inputProps={{
                    maxLength: 5,
                    inputMode: 'numeric',
                    pattern: '[0-9]*'
                  }}
                  sx={{ mb: 2 }}
                  helperText="Enter the 5-digit code from Telegram"
                />
                {needs2FA && (
                  <TextField
                    label="2FA Password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    fullWidth
                    sx={{ mb: 2 }}
                    helperText="Your Telegram 2FA password"
                  />
                )}
                <Box display="flex" gap={1}>
                  <Button
                    variant="outlined"
                    onClick={() => {
                      setAuthStep(0);
                      setCode('');
                      setNeeds2FA(false);
                    }}
                  >
                    Back
                  </Button>
                  <Button
                    variant="contained"
                    onClick={handleVerifyCode}
                    disabled={authLoading}
                    startIcon={authLoading ? <CircularProgress size={16} /> : <CheckCircle size={18} />}
                  >
                    {authLoading ? 'Verifying...' : 'Verify'}
                  </Button>
                </Box>
              </Box>
            )}
          </Box>
        )}

        {/* Connected - Channel Management */}
        {status?.connected && (
          <Box>
            {/* Channel Limit Display */}
            <Box mb={2}>
              <UsageDisplay
                label="Monitored Channels"
                used={channels.length}
                limit={status?.channel_limit || getLimit('telegram_channels')}
              />
            </Box>

            {/* Monitoring Controls */}
            <Box display="flex" gap={1} mb={2}>
              {status?.monitoring ? (
                <Button
                  variant="outlined"
                  color="warning"
                  startIcon={<Square size={18} />}
                  onClick={handleStopMonitoring}
                >
                  Stop Monitoring
                </Button>
              ) : (
                <Button
                  variant="contained"
                  color="success"
                  startIcon={<Play size={18} />}
                  onClick={handleStartMonitoring}
                  disabled={channels.length === 0}
                >
                  Start Monitoring
                </Button>
              )}
              <Button
                variant="outlined"
                startIcon={channelsLoading ? <CircularProgress size={16} /> : <Plus size={18} />}
                onClick={handleFetchAvailableChannels}
                disabled={channelsLoading || isLimitReached('telegram_channels', channels.length)}
              >
                Add Channel
              </Button>
            </Box>

            {/* Channel List */}
            {(channels || []).length > 0 ? (
              <List dense>
                {(channels || []).map((channel) => (
                  <ListItem key={channel.id}>
                    <ListItemIcon>
                      <MessageCircle size={18} style={{ color: theme.palette.primary.main }} />
                    </ListItemIcon>
                    <ListItemText
                      primary={channel.channel_name}
                      secondary={
                        <Box display="flex" gap={2}>
                          <span>{channel.messages_received || 0} messages</span>
                          <span>{channel.deals_extracted || 0} deals</span>
                        </Box>
                      }
                      secondaryTypographyProps={{ component: 'div' }}
                    />
                    <ListItemSecondaryAction>
                      <Box display="flex" gap={1} alignItems="center">
                        <Tooltip title="Sync last 14 days of messages">
                          <Button
                            size="small"
                            variant="outlined"
                            onClick={() => handleBackfill(channel.channel_id)}
                            disabled={syncing[channel.channel_id]}
                            startIcon={syncing[channel.channel_id] ? <CircularProgress size={14} /> : <RotateCw size={14} />}
                          >
                            {syncing[channel.channel_id] ? 'Syncing...' : 'Sync 14 Days'}
                          </Button>
                        </Tooltip>
                        <Tooltip title="Remove channel">
                          <IconButton
                            edge="end"
                            size="small"
                            onClick={() => handleRemoveChannel(channel.channel_id)}
                          >
                            <Trash2 size={18} />
                          </IconButton>
                        </Tooltip>
                      </Box>
                    </ListItemSecondaryAction>
                  </ListItem>
                ))}
              </List>
            ) : (
              <Alert severity="info">
                No channels added yet. Click "Add Channel" to select channels to monitor.
              </Alert>
            )}

            {/* Stats */}
            {status?.monitoring && (
              <Box mt={2} p={2} sx={{ bgcolor: 'rgba(255, 255, 255, 0.05)', borderRadius: 2 }}>
                <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                  Monitoring Active
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Deals will be automatically extracted and appear in your feed.
                </Typography>
              </Box>
            )}
          </Box>
        )}

        {/* Channel Selection Dialog */}
        <Dialog
          open={showChannelDialog}
          onClose={() => {
            setShowChannelDialog(false);
            setSelectedChannel(null);
            setSupplierDetails({
              createSupplier: true,
              supplierName: '',
              supplierWebsite: '',
              supplierEmail: '',
              supplierNotes: '',
            });
          }}
          maxWidth="sm"
          fullWidth
        >
          <DialogTitle>Add Telegram Channel</DialogTitle>
          <DialogContent dividers>
            {(availableChannels || []).length > 0 ? (
              <>
                <List>
                  {(availableChannels || []).map((channel) => (
                    <ListItem 
                      key={channel.id}
                      button
                      selected={selectedChannel?.id === channel.id}
                      onClick={() => handleSelectChannel(channel)}
                    >
                      <ListItemIcon>
                        <MessageCircle size={20} />
                      </ListItemIcon>
                      <ListItemText
                        primary={channel.name}
                        secondary={`${channel.type} • ${channel.member_count || '?'} members`}
                      />
                      {channel.is_monitored && (
                        <Chip label="Monitoring" size="small" color="success" sx={{ ml: 2 }} />
                      )}
                    </ListItem>
                  ))}
                </List>
                
                {selectedChannel && (
                  <>
                    <Divider sx={{ my: 2 }} />
                    
                    <Box sx={{ mb: 2, p: 2, bgcolor: '#252540', borderRadius: 2 }}>
                      <Typography variant="subtitle2" color="primary">
                        Selected: {selectedChannel.name || selectedChannel.title}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        @{selectedChannel.username || 'no-username'}
                      </Typography>
                    </Box>
                    
                    {/* Supplier creation */}
                    <FormControlLabel
                      control={
                        <Checkbox
                          checked={supplierDetails.createSupplier}
                          onChange={(e) => setSupplierDetails({
                            ...supplierDetails,
                            createSupplier: e.target.checked
                          })}
                        />
                      }
                      label="Create as Supplier"
                    />
                    
                    {supplierDetails.createSupplier && (
                      <Box sx={{ mt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
                        <TextField
                          label="Supplier Name"
                          value={supplierDetails.supplierName}
                          onChange={(e) => setSupplierDetails({
                            ...supplierDetails,
                            supplierName: e.target.value
                          })}
                          placeholder={selectedChannel?.name || selectedChannel?.title || 'Supplier name'}
                          fullWidth
                          size="small"
                        />
                        
                        <TextField
                          label="Website (optional)"
                          value={supplierDetails.supplierWebsite}
                          onChange={(e) => setSupplierDetails({
                            ...supplierDetails,
                            supplierWebsite: e.target.value
                          })}
                          placeholder="https://..."
                          fullWidth
                          size="small"
                        />
                        
                        <TextField
                          label="Contact Email (optional)"
                          value={supplierDetails.supplierEmail}
                          onChange={(e) => setSupplierDetails({
                            ...supplierDetails,
                            supplierEmail: e.target.value
                          })}
                          placeholder="contact@supplier.com"
                          fullWidth
                          size="small"
                        />
                        
                        <TextField
                          label="Notes (optional)"
                          value={supplierDetails.supplierNotes}
                          onChange={(e) => setSupplierDetails({
                            ...supplierDetails,
                            supplierNotes: e.target.value
                          })}
                          placeholder="Any notes about this supplier..."
                          multiline
                          rows={2}
                          fullWidth
                          size="small"
                        />
                      </Box>
                    )}
                  </>
                )}
              </>
            ) : (
              <Typography color="text.secondary" textAlign="center" py={4}>
                No channels found. Make sure you're a member of some Telegram channels or groups.
              </Typography>
            )}
          </DialogContent>
          <DialogActions>
            <Button onClick={() => {
              setShowChannelDialog(false);
              setSelectedChannel(null);
              setSupplierDetails({
                createSupplier: true,
                supplierName: '',
                supplierWebsite: '',
                supplierEmail: '',
                supplierNotes: '',
              });
            }}>
              Cancel
            </Button>
            <Button
              variant="contained"
              onClick={() => handleAddChannel()}
              disabled={!selectedChannel || isLimitReached('telegram_channels', channels.length)}
            >
              Add Channel
            </Button>
          </DialogActions>
        </Dialog>
      </CardContent>
    </Card>
  );
};

export default TelegramConnect;

