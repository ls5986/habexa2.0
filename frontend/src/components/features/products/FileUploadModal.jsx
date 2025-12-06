import React, { useState, useEffect } from 'react';
import {
  Dialog, DialogTitle, DialogContent, DialogActions, Button,
  Select, MenuItem, FormControl, InputLabel, TextField,
  Box, Typography, LinearProgress, IconButton, Alert, AlertTitle,
  List, ListItem, ListItemText, Collapse, CircularProgress
} from '@mui/material';
import {
  Upload as UploadIcon, Add as AddIcon, Close as CloseIcon,
  CheckCircle, Cancel, ExpandMore, ExpandLess
} from '@mui/icons-material';
import api from '../../../services/api';
import PipelineProgressTracker from './PipelineProgressTracker';
import ColumnMappingDialog from '../../ColumnMappingDialog';

export default function FileUploadModal({ open, onClose, onComplete }) {
  const [suppliers, setSuppliers] = useState([]);
  const [selectedSupplier, setSelectedSupplier] = useState('');
  const [newSupplierName, setNewSupplierName] = useState('');
  const [showNewSupplier, setShowNewSupplier] = useState(false);
  const [creatingSupplier, setCreatingSupplier] = useState(false);
  
  const [file, setFile] = useState(null);
  const [jobId, setJobId] = useState(null);
  const [job, setJob] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [showErrors, setShowErrors] = useState(false);
  
  // Column mapping state
  const [previewData, setPreviewData] = useState(null);
  const [showColumnMapping, setShowColumnMapping] = useState(false);
  const [uploadedFileData, setUploadedFileData] = useState(null);

  // Fetch suppliers on open
  useEffect(() => {
    if (open) {
      fetchSuppliers();
      reset();
    }
  }, [open]);

  // Poll for job status ONLY when modal is open AND job is active
  useEffect(() => {
    // Don't poll if modal is closed, no jobId, or job is already complete/failed
    if (!open || !jobId || job?.status === 'completed' || job?.status === 'failed') {
      return;
    }
    
    const interval = setInterval(async () => {
      try {
        const res = await api.get(`/jobs/${jobId}`);
        const jobData = res.data;
        setJob(jobData);
        
        // Stop polling if job is complete or failed
        if (jobData.status === 'completed' || jobData.status === 'failed') {
          clearInterval(interval);
          setUploading(false);
          
          // Show error if job failed
          if (jobData.status === 'failed') {
            const errorMsg = jobData.errors?.[0] || jobData.error || 'Upload failed. Please check the errors.';
            setError(errorMsg);
          }
          
          if (jobData.status === 'completed' && onComplete) {
            // Small delay before calling onComplete to prevent race conditions
            setTimeout(() => {
              onComplete(jobData.result);
            }, 500);
          }
        }
      } catch (err) {
        console.error('Error polling job:', err);
        // If job not found (404), stop polling gracefully
        if (err.response?.status === 404) {
          clearInterval(interval);
          setUploading(false);
          setJob(null);
          setError('Job not found. The upload may have been cancelled or deleted.');
          return;
        }
        // On other errors, stop polling to prevent infinite loops
        clearInterval(interval);
        setUploading(false);
        setError(err.response?.data?.detail || 'Failed to check job status. Please refresh the page.');
      }
    }, 3000); // Poll every 3 seconds (reduced from 2)
    
    return () => clearInterval(interval);
  }, [open, jobId, job?.status, onComplete]); // Added 'open' and 'job?.status' to dependencies

  const fetchSuppliers = async () => {
    try {
      const res = await api.get('/suppliers');
      setSuppliers(res.data.suppliers || res.data || []);
    } catch (err) {
      console.error('Error fetching suppliers:', err);
    }
  };

  const reset = () => {
    setSelectedSupplier('');
    setNewSupplierName('');
    setShowNewSupplier(false);
    setFile(null);
    setJobId(null);
    setJob(null);
    setUploading(false);
    setError(null);
    setShowErrors(false);
  };

  const createSupplier = async () => {
    if (!newSupplierName.trim()) return;
    
    setCreatingSupplier(true);
    try {
      const res = await api.post('/suppliers', { name: newSupplierName.trim() });
      const newSupplier = res.data;
      
      setSuppliers([...suppliers, newSupplier]);
      setSelectedSupplier(newSupplier.id);
      setShowNewSupplier(false);
      setNewSupplierName('');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create supplier');
    } finally {
      setCreatingSupplier(false);
    }
  };

  const handleFileSelect = (e) => {
    const selected = e.target.files?.[0];
    if (!selected) return;
    
    const ext = selected.name.toLowerCase().slice(selected.name.lastIndexOf('.'));
    if (!['.csv', '.xlsx', '.xls'].includes(ext)) {
      setError('Please upload a .csv or .xlsx file');
      return;
    }
    
    setFile(selected);
    setError(null);
  };

  const handleUpload = async () => {
    if (!file || !selectedSupplier) {
      setError('Please select a supplier and file');
      return;
    }
    
    setUploading(true);
    setError(null);
    
    try {
      // Step 1: Upload for preview + AI column mapping
      const formData = new FormData();
      formData.append('file', file);
      
      const previewRes = await api.post('/products/upload/preview', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      // Store file data for later
      const fileBase64 = await new Promise((resolve) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result.split(',')[1]);
        reader.readAsDataURL(file);
      });
      setUploadedFileData(fileBase64);
      
      // Show column mapping dialog
      setPreviewData(previewRes.data);
      setShowColumnMapping(true);
      setUploading(false);
      
    } catch (err) {
      console.error('Preview error:', err);
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to preview file. Please try again.';
      setError(errorMessage);
      setUploading(false);
    }
  };
  
  const handleConfirmMapping = async (columnMapping) => {
    setShowColumnMapping(false);
    setUploading(true);
    setError(null);
    
    try {
      // Step 2: Confirm upload with column mapping
      const res = await api.post('/products/upload/confirm', {
        filename: file.name,
        file_data: uploadedFileData,
        column_mapping: columnMapping,
        supplier_id: selectedSupplier
      });
      
      // For now, use the old upload endpoint as fallback
      // The new confirm endpoint will be used once fully tested
      if (res.data.job_id) {
        setJobId(res.data.job_id);
      } else {
        // Fallback to old upload method
        const formData = new FormData();
        formData.append('file', file);
        formData.append('supplier_id', selectedSupplier);
        
        const uploadRes = await api.post('/products/upload', formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });
        setJobId(uploadRes.data.job_id);
      }
    } catch (err) {
      console.error('Upload error:', err);
      const errorMessage = err.response?.data?.detail || err.message || 'Upload failed. Please try again.';
      setError(errorMessage);
      setUploading(false);
      setJobId(null);
    }
  };

  const supplierName = suppliers.find(s => s.id === selectedSupplier)?.name || '';

  return (
    <>
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        Upload Price List
        <IconButton onClick={onClose} size="small">
          <CloseIcon fontSize="small" />
        </IconButton>
      </DialogTitle>
      
      <DialogContent>
        {/* COMPLETED STATE */}
        {job?.status === 'completed' && (
          <Box>
            <Alert 
              severity={job.error_count > 0 && job.success_count === 0 ? "error" : job.error_count > 0 ? "warning" : "success"} 
              sx={{ mb: 2 }}
            >
              <AlertTitle>
                {job.error_count > 0 && job.success_count === 0 
                  ? "Upload Completed with Errors" 
                  : job.error_count > 0 
                  ? "Upload Completed with Some Errors" 
                  : "Upload Complete"}
              </AlertTitle>
              <Typography variant="body2" sx={{ mt: 1 }}>
                Supplier: <strong>{job.metadata?.supplier_name || job.result?.supplier_name || 'Unknown'}</strong>
              </Typography>
              <Typography variant="body2">
                Products created: <strong>{job.result?.products_created || job.success_count || 0}</strong>
              </Typography>
              <Typography variant="body2">
                Deals processed: <strong>{job.result?.deals_processed || job.success_count || 0}</strong>
              </Typography>
              {(job.error_count > 0 || job.errors?.length > 0 || job.result?.errors?.length > 0) && (
                <Box sx={{ mt: 2 }}>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                    {job.error_count || job.errors?.length || job.result?.errors?.length} row(s) had errors
                  </Typography>
                  <Button
                    size="small"
                    onClick={() => setShowErrors(!showErrors)}
                    endIcon={showErrors ? <ExpandLess /> : <ExpandMore />}
                  >
                    {showErrors ? 'Hide' : 'Show'} Errors
                  </Button>
                  <Collapse in={showErrors}>
                    <List dense sx={{ maxHeight: 200, overflow: 'auto', mt: 1 }}>
                      {(job.errors || job.result?.errors || []).map((e, i) => (
                        <ListItem key={i}>
                          <ListItemText 
                            primary={e} 
                            primaryTypographyProps={{ variant: 'caption' }} 
                          />
                        </ListItem>
                      ))}
                    </List>
                  </Collapse>
                </Box>
              )}
            </Alert>
          </Box>
        )}

        {/* FAILED STATE */}
        {job?.status === 'failed' && (
          <Alert severity="error" sx={{ mb: 2 }}>
            <AlertTitle>Upload Failed</AlertTitle>
            <Typography variant="body2">{job.error}</Typography>
          </Alert>
        )}

        {/* PROCESSING STATE */}
        {(job?.status === 'processing' || job?.status === 'pending' || job?.status === 'parsing' || job?.status === 'analyzing') && (
          <Box sx={{ mb: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
              <CircularProgress size={20} />
              <Typography variant="body1">
                {job.status === 'parsing' ? 'Parsing file...' : 
                 job.status === 'analyzing' ? 'Analyzing products...' :
                 `Processing for ${supplierName}...`}
              </Typography>
            </Box>
            
            {/* Enhanced Progress Tracker */}
            <PipelineProgressTracker
              job={job}
              parsedData={job.metadata?.parsed_data || job.result?.parsed_data}
              conversionData={job.metadata?.conversion_data || job.result?.conversion_data}
              pricingData={job.metadata?.pricing_data || job.result?.pricing_data}
              keepaData={job.metadata?.keepa_data || job.result?.keepa_data}
            />
          </Box>
        )}

        {/* UPLOAD FORM */}
        {!job && (
          <>
            {/* Supplier Selection */}
            <Box sx={{ mb: 3 }}>
              <FormControl fullWidth sx={{ mb: 2 }}>
                <InputLabel>Supplier *</InputLabel>
                <Select
                  value={selectedSupplier}
                  label="Supplier *"
                  onChange={(e) => {
                    const supplierId = e.target.value;
                    console.log('Selected supplier ID:', supplierId);
                    setSelectedSupplier(supplierId);
                  }}
                  renderValue={(selected) => {
                    if (!selected) return <em style={{ color: '#999' }}>Select supplier...</em>;
                    const supplier = suppliers.find(s => s.id === selected);
                    return supplier?.name || 'Unknown';
                  }}
                  sx={{
                    width: '100%',
                    '& .MuiSelect-select': {
                      overflow: 'visible',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      paddingRight: '32px',
                    },
                  }}
                  MenuProps={{
                    PaperProps: {
                      sx: {
                        maxHeight: 300,
                        '& .MuiMenuItem-root': {
                          whiteSpace: 'normal',
                          wordBreak: 'break-word',
                        },
                      },
                    },
                  }}
                >
                  <MenuItem value="">Select supplier...</MenuItem>
                  {suppliers.map(s => (
                    <MenuItem key={s.id} value={s.id}>{s.name}</MenuItem>
                  ))}
                </Select>
              </FormControl>
              
              {!showNewSupplier ? (
                <Button
                  variant="outlined"
                  size="small"
                  startIcon={<AddIcon />}
                  onClick={() => setShowNewSupplier(true)}
                  fullWidth
                >
                  Add New Supplier
                </Button>
              ) : (
                <Box sx={{ display: 'flex', gap: 1 }}>
                  <TextField
                    fullWidth
                    size="small"
                    label="New supplier name"
                    value={newSupplierName}
                    onChange={(e) => setNewSupplierName(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && createSupplier()}
                    autoFocus
                  />
                  <Button
                    variant="contained"
                    size="small"
                    onClick={createSupplier}
                    disabled={creatingSupplier || !newSupplierName.trim()}
                  >
                    {creatingSupplier ? <CircularProgress size={16} /> : 'Add'}
                  </Button>
                  <IconButton
                    size="small"
                    onClick={() => {
                      setShowNewSupplier(false);
                      setNewSupplierName('');
                    }}
                  >
                    <CloseIcon fontSize="small" />
                  </IconButton>
                </Box>
              )}
            </Box>
            
            {/* File Drop Zone */}
            <Box sx={{ mb: 2 }}>
              <input
                type="file"
                id="file-upload"
                hidden
                accept=".csv,.xlsx,.xls"
                onChange={handleFileSelect}
              />
              <label htmlFor="file-upload">
                <Box
                  sx={{
                    border: '2px dashed',
                    borderColor: file ? 'primary.main' : 'divider',
                    borderRadius: 2,
                    p: 4,
                    textAlign: 'center',
                    cursor: 'pointer',
                    bgcolor: file ? 'primary.50' : 'background.paper',
                    '&:hover': {
                      borderColor: 'primary.main',
                      bgcolor: 'action.hover'
                    }
                  }}
                >
                  {file ? (
                    <Box>
                      <Typography variant="body1" fontWeight="600">
                        {file.name}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {(file.size / 1024).toFixed(1)} KB
                      </Typography>
                      <Typography variant="caption" color="primary" sx={{ display: 'block', mt: 1 }}>
                        Click to change
                      </Typography>
                    </Box>
                  ) : (
                    <Box>
                      <UploadIcon sx={{ fontSize: 32, color: 'text.secondary', mb: 1 }} />
                      <Typography variant="body2" color="text.secondary">
                        Drop CSV or Excel file here
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        .csv, .xlsx, .xls
                      </Typography>
                    </Box>
                  )}
                </Box>
              </label>
            </Box>
            
            {/* Error */}
            {error && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {error}
              </Alert>
            )}
            
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', textAlign: 'center' }}>
              All products in this file will be assigned to the selected supplier
            </Typography>
          </>
        )}
      </DialogContent>
      
      <DialogActions>
        {job?.status === 'completed' ? (
          <>
            <Button onClick={reset}>Upload Another</Button>
            <Button variant="contained" onClick={onClose}>Done</Button>
          </>
        ) : job?.status === 'failed' ? (
          <Button onClick={reset}>Try Again</Button>
        ) : (
          <>
            <Button onClick={onClose}>Cancel</Button>
            <Button
              variant="contained"
              onClick={handleUpload}
              disabled={!file || !selectedSupplier || uploading}
              startIcon={uploading ? null : <UploadIcon />}
              sx={{
                // Debug: log button state (remove in production)
                '&:disabled': {
                  opacity: 0.5,
                },
              }}
            >
              {uploading ? (
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <CircularProgress size={16} />
                  Starting...
                </Box>
              ) : (
                `Upload to ${supplierName || 'Supplier'}`
              )}
            </Button>
          </>
        )}
      </DialogActions>
    </Dialog>
    
    {/* Column Mapping Dialog */}
    <ColumnMappingDialog
      open={showColumnMapping}
      onClose={() => {
        setShowColumnMapping(false);
        setUploading(false);
      }}
      previewData={previewData}
      onConfirm={handleConfirmMapping}
    />
  </>
  );
}

