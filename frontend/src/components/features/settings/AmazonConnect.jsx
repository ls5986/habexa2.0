import React, { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Button,
  Box,
  Chip,
  CircularProgress,
  Alert,
} from '@mui/material';
import { Store, CheckCircle, Unlink } from 'lucide-react';
import { useSearchParams } from 'react-router-dom';
import api from '../../../services/api';
import { useToast } from '../../../context/ToastContext';
import { habexa } from '../../../theme';

export default function AmazonConnect() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [connection, setConnection] = useState(null);
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState(false);
  const [message, setMessage] = useState(null);
  const { showToast } = useToast();

  useEffect(() => {
    fetchConnection();
    
    // Check callback params
    if (searchParams.get('amazon_connected') === 'true') {
      setMessage({ type: 'success', text: 'Amazon connected successfully!' });
      showToast('Amazon account connected successfully!', 'success');
      searchParams.delete('amazon_connected');
      setSearchParams(searchParams, { replace: true });
      fetchConnection(); // Refresh connection status
    }
    if (searchParams.get('amazon_error')) {
      const errorMsg = searchParams.get('amazon_error');
      setMessage({ type: 'error', text: errorMsg });
      showToast(`Connection failed: ${errorMsg}`, 'error');
      searchParams.delete('amazon_error');
      setSearchParams(searchParams, { replace: true });
    }
  }, []);

  const fetchConnection = async () => {
    try {
      const res = await api.get('/integrations/amazon/connection');
      setConnection(res.data);
    } catch (err) {
      console.error('Failed to fetch connection:', err);
      setConnection({ connected: false });
    } finally {
      setLoading(false);
    }
  };

  const handleConnect = async () => {
    setConnecting(true);
    try {
      const res = await api.get('/integrations/amazon/oauth/authorize');
      // Redirect to Amazon OAuth
      window.location.href = res.data.authorization_url;
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Failed to start connection';
      setMessage({ type: 'error', text: errorMsg });
      showToast(errorMsg, 'error');
      setConnecting(false);
    }
  };

  const handleDisconnect = async () => {
    if (!confirm('Disconnect your Amazon account? You will need to reconnect to check gating status and get accurate fees.')) {
      return;
    }
    
    try {
      await api.delete('/integrations/amazon/disconnect');
      setConnection({ connected: false });
      setMessage({ type: 'success', text: 'Disconnected successfully' });
      showToast('Amazon account disconnected', 'success');
      fetchConnection();
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Failed to disconnect';
      setMessage({ type: 'error', text: errorMsg });
      showToast(errorMsg, 'error');
    }
  };

  if (loading) {
    return (
      <Card>
        <CardContent sx={{ textAlign: 'center', py: 4 }}>
          <CircularProgress />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent>
        <Box display="flex" alignItems="center" gap={2} mb={2}>
          <Store size={32} style={{ color: '#FF9900' }} />
          <Box flex={1}>
            <Typography variant="h6" fontWeight={600}>
              Amazon Seller Account
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Connect to check YOUR gating status and fees
            </Typography>
          </Box>
          {connection?.connected && (
            <Chip
              icon={<CheckCircle size={16} />}
              label="Connected"
              color="success"
            />
          )}
        </Box>

        {message && (
          <Alert
            severity={message.type}
            sx={{ mb: 2 }}
            onClose={() => setMessage(null)}
          >
            {message.text}
          </Alert>
        )}

        {connection?.connected ? (
          <Box>
            <Box mb={2}>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                <strong>Seller ID:</strong> {connection.seller_id || 'Not available'}
              </Typography>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                <strong>Marketplace:</strong> {connection.marketplace_id || 'US'}
              </Typography>
              {connection.connected_at && (
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  <strong>Connected:</strong>{' '}
                  {new Date(connection.connected_at).toLocaleDateString()}
                </Typography>
              )}
              {connection.last_used_at && (
                <Typography variant="body2" color="text.secondary">
                  <strong>Last used:</strong>{' '}
                  {new Date(connection.last_used_at).toLocaleString()}
                </Typography>
              )}
            </Box>
            <Button
              variant="outlined"
              color="error"
              startIcon={<Unlink size={18} />}
              onClick={handleDisconnect}
            >
              Disconnect
            </Button>
          </Box>
        ) : (
          <Box>
            <Alert severity="info" sx={{ mb: 2 }}>
              Connect your Amazon Seller account to see YOUR eligibility status on products.
              Each user connects their own account and sees their own gating status.
            </Alert>
            <Button
              variant="contained"
              size="large"
              startIcon={connecting ? <CircularProgress size={20} color="inherit" /> : <Store size={20} />}
              onClick={handleConnect}
              disabled={connecting}
              sx={{
                bgcolor: '#FF9900',
                '&:hover': { bgcolor: '#E88B00' },
                color: '#000'
              }}
            >
              {connecting ? 'Connecting...' : 'Connect Amazon'}
            </Button>
          </Box>
        )}

        {/* Benefits section */}
        {!connection?.connected && (
          <Box
            sx={{
              mt: 3,
              p: 2,
              bgcolor: habexa.gray[50],
              borderRadius: 2,
              border: '1px solid',
              borderColor: habexa.gray[200]
            }}
          >
            <Typography variant="subtitle2" fontWeight={600} gutterBottom>
              🔓 Why Connect?
            </Typography>
            <Box component="ul" sx={{ m: 0, pl: 2.5 }}>
              <li>
                <Typography variant="body2">
                  <strong>Real gating checks</strong> — Know if YOU can list a product, not just estimates
                </Typography>
              </li>
              <li>
                <Typography variant="body2">
                  <strong>Accurate FBA fees</strong> — Get exact fees from Amazon for your account
                </Typography>
              </li>
              <li>
                <Typography variant="body2">
                  <strong>Better analysis</strong> — More accurate profit calculations based on your account
                </Typography>
              </li>
            </Box>
          </Box>
        )}
      </CardContent>
    </Card>
  );
}
