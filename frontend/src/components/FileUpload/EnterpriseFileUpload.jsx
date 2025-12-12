import React, { useState } from 'react';
import {
  Box,
  Button,
  Typography,
  Alert,
  Paper,
  LinearProgress,
} from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import UploadProgressModal from './UploadProgressModal';
import api from '../../services/api';

export default function EnterpriseFileUpload({ supplierId, onUploadComplete }) {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [jobId, setJobId] = useState(null);
  const [showProgress, setShowProgress] = useState(false);

  const handleFileSelect = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    // Validate file size (max 100MB)
    if (file.size > 100 * 1024 * 1024) {
      setError('File size exceeds 100MB limit');
      return;
    }

    // Validate file type
    if (!file.name.match(/\.(csv|xlsx|xls)$/i)) {
      setError('Only CSV and Excel files are supported');
      return;
    }

    setUploading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', file);
      
      if (supplierId) {
        formData.append('supplier_id', supplierId);
      }

      const response = await api.post('/upload/file', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      setJobId(response.data.job_id);
      setShowProgress(true);
      setUploading(false);

    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Upload failed');
      setUploading(false);
    }
  };

  return (
    <Box>
      <Paper sx={{ p: 4, textAlign: 'center', bgcolor: 'grey.50' }}>
        <CloudUploadIcon sx={{ fontSize: 64, color: 'primary.main', mb: 2 }} />
        
        <Typography variant="h6" gutterBottom>
          Upload Product Catalog
        </Typography>
        
        <Typography variant="body2" color="text.secondary" mb={3}>
          Supports CSV and Excel files up to 100MB
          <br />
          <strong>Can handle 50,000+ products efficiently</strong>
        </Typography>

        <input
          type="file"
          id="file-upload"
          accept=".csv,.xlsx,.xls"
          style={{ display: 'none' }}
          onChange={handleFileSelect}
          disabled={uploading}
        />

        <label htmlFor="file-upload">
          <Button
            variant="contained"
            component="span"
            size="large"
            disabled={uploading}
            startIcon={<CloudUploadIcon />}
          >
            {uploading ? 'Uploading...' : 'Select File'}
          </Button>
        </label>

        {uploading && (
          <Box mt={2}>
            <LinearProgress />
            <Typography variant="caption" color="text.secondary" mt={1}>
              Uploading file and queuing processing job...
            </Typography>
          </Box>
        )}

        {error && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {error}
          </Alert>
        )}
      </Paper>

      {/* Progress Modal */}
      <UploadProgressModal
        open={showProgress}
        jobId={jobId}
        onClose={() => {
          setShowProgress(false);
          if (onUploadComplete) {
            onUploadComplete();
          }
        }}
      />
    </Box>
  );
}

