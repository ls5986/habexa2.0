import React, { useState, useEffect } from 'react';
import {
  Dialog, DialogTitle, DialogContent, DialogActions, Button,
  Box, Typography, Chip, LinearProgress, Table, TableBody,
  TableCell, TableHead, TableRow, IconButton, Alert, CircularProgress
} from '@mui/material';
import { Close as CloseIcon, Stop as StopIcon, Refresh as RefreshIcon } from '@mui/icons-material';
import api from '../../../services/api';
import { useToast } from '../../../context/ToastContext';

export default function JobDetailPanel({ jobId, open, onClose, onCancel, onRetry }) {
  const [job, setJob] = useState(null);
  const [chunks, setChunks] = useState([]);
  const [loading, setLoading] = useState(true);
  const { showToast } = useToast();

  useEffect(() => {
    if (open && jobId) {
      fetchJobDetails();
      // Poll if job is active
      const interval = setInterval(() => {
        if (job?.status === 'processing') {
          fetchJobDetails();
        }
      }, 5000);
      return () => clearInterval(interval);
    }
  }, [open, jobId, job?.status]);

  const fetchJobDetails = async () => {
    try {
      const [jobRes, chunksRes] = await Promise.all([
        api.get(`/jobs/upload/${jobId}`),
        api.get(`/jobs/upload/${jobId}/chunks`)
      ]);

      setJob(jobRes.data);
      setChunks(chunksRes.data.chunks || []);
    } catch (err) {
      console.error('Error fetching job details:', err);
      showToast('Failed to load job details', 'error');
    } finally {
      setLoading(false);
    }
  };

  if (!open) return null;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="lg" fullWidth>
      <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h6">Job Details</Typography>
        <IconButton onClick={onClose} size="small">
          <CloseIcon />
        </IconButton>
      </DialogTitle>

      <DialogContent>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
            <CircularProgress />
          </Box>
        ) : !job ? (
          <Alert severity="error">Job not found</Alert>
        ) : (
          <Box>
            {/* Job Info */}
            <Box sx={{ mb: 3 }}>
              <Typography variant="subtitle1" gutterBottom>
                {job.filename}
              </Typography>
              <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
                <Chip label={job.status} color={job.status === 'complete' ? 'success' : job.status === 'failed' ? 'error' : 'primary'} />
                {job.supplier && <Chip label={job.supplier.name} variant="outlined" />}
              </Box>

              {/* Progress */}
              {job.progress && (
                <Box sx={{ mb: 2 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="body2">Progress</Typography>
                    <Typography variant="body2">{job.progress.percent.toFixed(1)}%</Typography>
                  </Box>
                  <LinearProgress variant="determinate" value={job.progress.percent} />
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 1 }}>
                    <Typography variant="caption">
                      {job.progress.processed_rows?.toLocaleString() || 0} / {job.progress.total_rows?.toLocaleString() || 0} rows
                    </Typography>
                    <Typography variant="caption" color="success.main">
                      ✅ {job.progress.successful_rows?.toLocaleString() || 0} successful
                    </Typography>
                    {job.progress.failed_rows > 0 && (
                      <Typography variant="caption" color="error.main">
                        ❌ {job.progress.failed_rows} failed
                      </Typography>
                    )}
                  </Box>
                </Box>
              )}

              {/* Chunk Summary */}
              {job.chunks && (
                <Box sx={{ mb: 2 }}>
                  <Typography variant="subtitle2" gutterBottom>Chunks</Typography>
                  <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                    <Chip label={`Total: ${job.chunks.total}`} size="small" />
                    <Chip label={`Complete: ${job.chunks.complete}`} size="small" color="success" />
                    <Chip label={`Processing: ${job.chunks.processing}`} size="small" color="primary" />
                    <Chip label={`Pending: ${job.chunks.pending}`} size="small" />
                    {job.chunks.failed > 0 && (
                      <Chip label={`Failed: ${job.chunks.failed}`} size="small" color="error" />
                    )}
                  </Box>
                </Box>
              )}

              {/* Error Summary */}
              {job.error_summary && job.error_summary.total_errors > 0 && (
                <Alert severity="warning" sx={{ mb: 2 }}>
                  <Typography variant="subtitle2">Errors: {job.error_summary.total_errors}</Typography>
                  {job.error_summary.by_type && (
                    <Box sx={{ mt: 1 }}>
                      {Object.entries(job.error_summary.by_type).map(([type, count]) => (
                        <Typography key={type} variant="caption" display="block">
                          {type}: {count}
                        </Typography>
                      ))}
                    </Box>
                  )}
                </Alert>
              )}
            </Box>

            {/* Chunks Table */}
            {chunks.length > 0 && (
              <Box>
                <Typography variant="subtitle2" gutterBottom>
                  Chunk Details
                </Typography>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Chunk</TableCell>
                      <TableCell>Rows</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell>Success</TableCell>
                      <TableCell>Errors</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {chunks.slice(0, 20).map(chunk => (
                      <TableRow key={chunk.id}>
                        <TableCell>#{chunk.chunk_index + 1}</TableCell>
                        <TableCell>
                          {chunk.start_row}-{chunk.end_row}
                        </TableCell>
                        <TableCell>
                          <Chip label={chunk.status} size="small" />
                        </TableCell>
                        <TableCell>{chunk.success_count || 0}</TableCell>
                        <TableCell>{chunk.error_count || 0}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
                {chunks.length > 20 && (
                  <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                    Showing first 20 of {chunks.length} chunks
                  </Typography>
                )}
              </Box>
            )}
          </Box>
        )}
      </DialogContent>

      <DialogActions>
        {job?.status === 'processing' && (
          <Button
            startIcon={<StopIcon />}
            onClick={() => {
              onCancel(jobId);
              onClose();
            }}
            color="error"
          >
            Cancel Job
          </Button>
        )}
        {job?.status === 'failed' && (
          <Button
            startIcon={<RefreshIcon />}
            onClick={() => {
              onRetry(jobId);
              onClose();
            }}
          >
            Retry Failed
          </Button>
        )}
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
}

