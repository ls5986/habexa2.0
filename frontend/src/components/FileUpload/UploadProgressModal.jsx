import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  Box,
  Typography,
  LinearProgress,
  Chip,
  Alert,
  Button,
  Stack,
} from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import HourglassEmptyIcon from '@mui/icons-material/HourglassEmpty';
import api from '../../services/api';

export default function UploadProgressModal({ open, jobId, onClose }) {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!open || !jobId) return;

    // Poll for status every 2 seconds
    const interval = setInterval(async () => {
      try {
        const response = await api.get(`/upload/status/${jobId}`);

        setStatus(response.data);
        setLoading(false);

        // Stop polling if complete or failed
        if (response.data.status === 'complete' || response.data.status === 'failed') {
          clearInterval(interval);
        }
      } catch (err) {
        setError(err.message);
        setLoading(false);
        clearInterval(interval);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [open, jobId]);

  const formatTime = (seconds) => {
    if (!seconds) return '--';
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs}s`;
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'complete': return 'success';
      case 'failed': return 'error';
      case 'pending': return 'default';
      default: return 'primary';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'complete': return <CheckCircleIcon />;
      case 'failed': return <ErrorIcon />;
      default: return <HourglassEmptyIcon />;
    }
  };

  return (
    <Dialog 
      open={open} 
      onClose={status?.status === 'complete' || status?.status === 'failed' ? onClose : undefined} 
      maxWidth="sm" 
      fullWidth
    >
      <DialogTitle>
        <Box display="flex" alignItems="center" gap={2}>
          File Upload Progress
          {status && (
            <Chip
              label={status.current_phase}
              color={getStatusColor(status.status)}
              icon={getStatusIcon(status.status)}
              size="small"
            />
          )}
        </Box>
      </DialogTitle>

      <DialogContent>
        {loading && (
          <Box textAlign="center" py={4}>
            <LinearProgress />
            <Typography variant="body2" color="text.secondary" mt={2}>
              Loading status...
            </Typography>
          </Box>
        )}

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {status && !loading && (
          <Stack spacing={3}>
            {/* Progress Bar */}
            <Box>
              <Box display="flex" justifyContent="space-between" mb={1}>
                <Typography variant="body2" color="text.secondary">
                  Progress
                </Typography>
                <Typography variant="body2" fontWeight="bold">
                  {status.progress}%
                </Typography>
              </Box>
              <LinearProgress 
                variant="determinate" 
                value={status.progress} 
                sx={{ height: 8, borderRadius: 1 }}
              />
              <Typography variant="caption" color="text.secondary" mt={1} display="block">
                {status.processed_rows?.toLocaleString()} / {status.total_rows?.toLocaleString()} rows
              </Typography>
            </Box>

            {/* Stats Grid */}
            <Box 
              display="grid" 
              gridTemplateColumns="repeat(2, 1fr)" 
              gap={2}
              sx={{ bgcolor: 'grey.50', p: 2, borderRadius: 1 }}
            >
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Products Created
                </Typography>
                <Typography variant="h6">
                  {status.products_created?.toLocaleString() || 0}
                </Typography>
              </Box>

              <Box>
                <Typography variant="caption" color="text.secondary">
                  API Calls
                </Typography>
                <Typography variant="h6">
                  {status.api_calls_made?.toLocaleString() || 0}
                </Typography>
              </Box>

              <Box>
                <Typography variant="caption" color="text.secondary">
                  Cache Hits
                </Typography>
                <Typography variant="h6" color="success.main">
                  {status.cache_hits?.toLocaleString() || 0}
                </Typography>
              </Box>

              <Box>
                <Typography variant="caption" color="text.secondary">
                  Failed Rows
                </Typography>
                <Typography variant="h6" color={status.failed_rows > 0 ? 'error.main' : 'text.primary'}>
                  {status.failed_rows || 0}
                </Typography>
              </Box>
            </Box>

            {/* Time Estimates */}
            <Box>
              <Box display="flex" justifyContent="space-between" mb={1}>
                <Typography variant="body2" color="text.secondary">
                  Elapsed Time
                </Typography>
                <Typography variant="body2">
                  {formatTime(status.duration_seconds)}
                </Typography>
              </Box>

              {status.estimated_remaining_seconds && status.status !== 'complete' && (
                <Box display="flex" justifyContent="space-between">
                  <Typography variant="body2" color="text.secondary">
                    Estimated Remaining
                  </Typography>
                  <Typography variant="body2" color="primary">
                    {formatTime(status.estimated_remaining_seconds)}
                  </Typography>
                </Box>
              )}
            </Box>

            {/* Success Message */}
            {status.status === 'complete' && (
              <Alert severity="success" icon={<CheckCircleIcon />}>
                <Typography variant="body2" fontWeight="bold">
                  Upload Complete!
                </Typography>
                <Typography variant="caption">
                  {status.products_created} products created in {formatTime(status.duration_seconds)}
                </Typography>
              </Alert>
            )}

            {/* Error Message */}
            {status.status === 'failed' && (
              <Alert severity="error">
                <Typography variant="body2" fontWeight="bold">
                  Upload Failed
                </Typography>
                {status.error && (
                  <Typography variant="caption">
                    {status.error.error || 'An error occurred during processing'}
                  </Typography>
                )}
              </Alert>
            )}

            {/* Actions */}
            <Box display="flex" gap={2} justifyContent="flex-end">
              {status.status === 'complete' && (
                <Button 
                  variant="contained" 
                  onClick={onClose}
                  fullWidth
                >
                  View Products
                </Button>
              )}

              {status.status !== 'complete' && status.status !== 'failed' && (
                <Button 
                  variant="outlined" 
                  color="error"
                  onClick={async () => {
                    try {
                      await api.delete(`/upload/job/${jobId}`);
                      onClose();
                    } catch (err) {
                      console.error('Cancel failed:', err);
                    }
                  }}
                >
                  Cancel
                </Button>
              )}

              {status.status === 'failed' && (
                <Button variant="outlined" onClick={onClose}>
                  Close
                </Button>
              )}
            </Box>
          </Stack>
        )}
      </DialogContent>
    </Dialog>
  );
}

