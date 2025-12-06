import React, { useState, useEffect } from 'react';
import {
  Box, Typography, Button, Table, TableBody, TableCell, TableHead,
  TableRow, Chip, IconButton, LinearProgress, Tabs, Tab, CircularProgress
} from '@mui/material';
import { Stop as StopIcon, Refresh as RefreshIcon, Visibility as ViewIcon } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import { useToast } from '../context/ToastContext';
import JobDetailPanel from '../components/features/jobs/JobDetailPanel';

function formatRelativeTime(dateString) {
  if (!dateString) return '—';
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

function StatusChip({ status }) {
  const colors = {
    pending: 'default',
    mapping: 'info',
    validating: 'info',
    processing: 'primary',
    complete: 'success',
    failed: 'error',
    cancelled: 'warning'
  };

  return <Chip label={status} color={colors[status] || 'default'} size="small" />;
}

export default function Jobs() {
  const [jobs, setJobs] = useState([]);
  const [filter, setFilter] = useState('all');
  const [loading, setLoading] = useState(true);
  const [selectedJob, setSelectedJob] = useState(null);
  const { showToast } = useToast();
  const navigate = useNavigate();

  // Check if there are active jobs for polling
  const hasActiveJobs = jobs.some(j =>
    ['processing', 'pending', 'mapping', 'validating'].includes(j.status)
  );

  useEffect(() => {
    fetchJobs();
  }, [filter]);

  // ✅ OPTIMIZATION: Smart polling - only polls when there are active jobs
  // Stops automatically when all jobs are complete
  // 5 second interval is reasonable for job status updates
  // This prevents unnecessary API calls when no jobs are running
  useEffect(() => {
    if (!hasActiveJobs) return;

    const interval = setInterval(fetchJobs, 5000);
    return () => clearInterval(interval);
  }, [hasActiveJobs]);

  const fetchJobs = async () => {
    try {
      const params = {};
      if (filter !== 'all') {
        if (filter === 'active') {
          params.status = 'processing';
        } else {
          params.status = filter;
        }
      }

      const res = await api.get('/jobs/upload', { params });
      setJobs(res.data.jobs || []);
    } catch (err) {
      console.error('Error fetching jobs:', err);
      showToast('Failed to load jobs', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = async (jobId) => {
    if (!confirm('Cancel this upload? Products already created will remain.')) return;

    try {
      await api.post(`/jobs/upload/${jobId}/cancel`);
      showToast('Job cancelled', 'success');
      fetchJobs();
    } catch (err) {
      showToast(err.response?.data?.detail || 'Failed to cancel job', 'error');
    }
  };

  const handleRetry = async (jobId) => {
    try {
      await api.post(`/jobs/upload/${jobId}/retry`);
      showToast('Retrying failed chunks', 'success');
      fetchJobs();
    } catch (err) {
      showToast(err.response?.data?.detail || 'Failed to retry job', 'error');
    }
  };

  const filteredJobs = filter === 'active'
    ? jobs.filter(j => ['processing', 'pending', 'mapping', 'validating'].includes(j.status))
    : filter === 'all'
    ? jobs
    : jobs.filter(j => j.status === filter);

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Upload Jobs</Typography>
        <Button
          variant="contained"
          onClick={() => navigate('/products?upload=true')}
        >
          + New Upload
        </Button>
      </Box>

      <Tabs value={filter} onChange={(e, v) => setFilter(v)} sx={{ mb: 3 }}>
        <Tab label="All" value="all" />
        <Tab label="Active" value="active" />
        <Tab label="Complete" value="complete" />
        <Tab label="Failed" value="failed" />
      </Tabs>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
          <CircularProgress />
        </Box>
      ) : filteredJobs.length === 0 ? (
        <Box sx={{ textAlign: 'center', p: 4 }}>
          <Typography variant="body1" color="text.secondary">
            No jobs found
          </Typography>
        </Box>
      ) : (
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>File / Supplier</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Progress</TableCell>
              <TableCell>Created</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filteredJobs.map(job => {
              const progressPercent = job.progress?.percent || 0;
              return (
                <TableRow key={job.id} hover>
                  <TableCell>
                    <Typography variant="body2" fontWeight={600}>
                      {job.filename}
                    </Typography>
                    {job.supplier && (
                      <Typography variant="caption" color="text.secondary">
                        {job.supplier.name}
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell>
                    <StatusChip status={job.status} />
                  </TableCell>
                  <TableCell>
                    {job.status === 'processing' ? (
                      <Box>
                        <LinearProgress
                          variant="determinate"
                          value={progressPercent}
                          sx={{ mb: 0.5 }}
                        />
                        <Typography variant="caption" color="text.secondary">
                          {job.progress?.processed_rows?.toLocaleString() || 0} / {job.progress?.total_rows?.toLocaleString() || 0}
                        </Typography>
                      </Box>
                    ) : job.status === 'complete' ? (
                      <Typography variant="body2" color="success.main">
                        ✅ {job.progress?.successful_rows?.toLocaleString() || 0} products
                      </Typography>
                    ) : job.status === 'failed' ? (
                      <Typography variant="body2" color="error.main">
                        ❌ {job.progress?.failed_rows || 0} errors
                      </Typography>
                    ) : (
                      <Typography variant="body2" color="text.secondary">—</Typography>
                    )}
                  </TableCell>
                  <TableCell>
                    <Typography variant="caption">
                      {formatRelativeTime(job.created_at)}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', gap: 0.5 }}>
                      {job.status === 'processing' && (
                        <IconButton
                          size="small"
                          onClick={() => handleCancel(job.id)}
                          title="Cancel"
                        >
                          <StopIcon fontSize="small" />
                        </IconButton>
                      )}
                      {job.status === 'failed' && (
                        <IconButton
                          size="small"
                          onClick={() => handleRetry(job.id)}
                          title="Retry Failed"
                        >
                          <RefreshIcon fontSize="small" />
                        </IconButton>
                      )}
                      <IconButton
                        size="small"
                        onClick={() => setSelectedJob(job.id)}
                        title="View Details"
                      >
                        <ViewIcon fontSize="small" />
                      </IconButton>
                    </Box>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      )}

      {/* Job Detail Panel */}
      {selectedJob && (
        <JobDetailPanel
          jobId={selectedJob}
          open={!!selectedJob}
          onClose={() => setSelectedJob(null)}
          onCancel={handleCancel}
          onRetry={handleRetry}
        />
      )}
    </Box>
  );
}

