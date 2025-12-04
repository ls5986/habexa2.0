import React, { useState, useEffect } from 'react';
import {
  Button, Box, Typography, LinearProgress, IconButton,
  Dialog, DialogTitle, DialogContent, DialogActions, Alert, AlertTitle,
  List, ListItem, ListItemText, Collapse
} from '@mui/material';
import {
  PlayArrow, CheckCircle, Cancel, Close as CloseIcon, ExpandMore, ExpandLess
} from '@mui/icons-material';
import { CircularProgress } from '@mui/material';
import api from '../../../services/api';
import SupplierSelectionDialog from './SupplierSelectionDialog';
import { useFeatureGate } from '../../../hooks/useFeatureGate';
import { useToast } from '../../../context/ToastContext';

export default function BatchAnalyzeButton({ 
  productIds = null,  // Specific products
  analyzeAllPending = false,  // All pending
  onComplete = null,
  buttonText = "Analyze All",
  className = ""
}) {
  const { hasFeature, promptUpgrade } = useFeatureGate();
  const { showToast } = useToast();
  const [jobId, setJobId] = useState(null);
  const [job, setJob] = useState(null);
  const [starting, setStarting] = useState(false);
  const [showProgress, setShowProgress] = useState(false);
  const [showErrors, setShowErrors] = useState(false);
  const [showSupplierDialog, setShowSupplierDialog] = useState(false);
  const [productsWithoutSuppliers, setProductsWithoutSuppliers] = useState([]);
  const [groupedByFile, setGroupedByFile] = useState({});
  const [productCount, setProductCount] = useState(0);

  // Poll for job status
  useEffect(() => {
    if (!jobId) return;
    
    const interval = setInterval(async () => {
      try {
        const res = await api.get(`/jobs/${jobId}`);
        setJob(res.data);
        
        if (res.data.status === 'completed' || res.data.status === 'failed' || res.data.status === 'cancelled') {
          clearInterval(interval);
          if (res.data.status === 'completed' && onComplete) {
            onComplete(res.data);
          }
        }
      } catch (err) {
        console.error('Error polling job:', err);
        // If job not found, stop polling
        if (err.response?.status === 404) {
          clearInterval(interval);
        }
      }
    }, 2000);  // Poll every 2 seconds
    
    return () => clearInterval(interval);
  }, [jobId, onComplete]);

  const startAnalysis = async () => {
    // Check if user has bulk analyze feature
    if (!hasFeature('bulk_analyze')) {
      promptUpgrade('bulk_analyze');
      return;
    }
    
    setStarting(true);
    
    try {
      const payload = {};
      if (productIds) {
        payload.product_ids = productIds;
      } else if (analyzeAllPending) {
        payload.analyze_all_pending = true;
      }
      
      const res = await api.post('/batch/analyze', payload);
      setJobId(res.data.job_id);
      setJob({ status: 'pending', total_items: res.data.total, progress: 0 });
      setShowProgress(true);
    } catch (err) {
      console.error('Error starting batch:', err);
      console.error('Error response:', err.response?.data);
      console.error('Error response detail:', err.response?.data?.detail);
      
      // Check if error is about missing suppliers
      const errorDetail = err.response?.data?.detail;
      
      // Handle both string and object error details
      let errorObj = errorDetail;
      if (typeof errorDetail === 'string') {
        try {
          errorObj = JSON.parse(errorDetail);
        } catch {
          // Not JSON, treat as string
          errorObj = { message: errorDetail };
        }
      }
      
      console.log('Parsed error object:', errorObj);
      
      if (errorObj && typeof errorObj === 'object' && errorObj.error === 'products_missing_suppliers') {
        // Show supplier selection dialog
        console.log('Products without suppliers:', errorObj.products);
        console.log('Grouped by file:', errorObj.grouped_by_file);
        console.log('Count:', errorObj.count);
        
        // Use count from error response (backend found products but may not have fetched details)
        const productCount = errorObj.count || errorObj.products?.length || 0;
        const products = errorObj.products || [];
        
        // Store the actual count for the dialog
        setProductCount(productCount);
        
        // If we have count but no products, create placeholder products for the dialog
        let productsToShow = products;
        if (productCount > 0 && products.length === 0) {
          // Create placeholder products so the dialog shows the correct count
          productsToShow = Array(Math.min(productCount, 100)).fill(null).map((_, i) => ({
            id: `placeholder-${i}`,
            asin: `...`,
            title: 'Product details loading...'
          }));
        }
        
        setProductsWithoutSuppliers(productsToShow);
        // Store grouped data for the dialog
        setGroupedByFile(errorObj.grouped_by_file || {});
        setShowSupplierDialog(true);
      } else {
        // Other error - show toast with full details for debugging
        const errorMsg = errorObj?.message || errorDetail?.message || (typeof errorDetail === 'string' ? errorDetail : JSON.stringify(errorDetail)) || 'Failed to start analysis';
        console.error('Showing error toast:', errorMsg);
        showToast(errorMsg, 'error');
      }
    } finally {
      setStarting(false);
    }
  };

  const handleSupplierAssigned = async (supplierId) => {
    // Retry analysis after supplier is assigned
    setShowSupplierDialog(false);
    setProductsWithoutSuppliers([]);
    // Longer delay to ensure database transaction is committed and view is refreshed
    setTimeout(() => {
      startAnalysis();
    }, 2000);  // Increased from 500ms to 2 seconds
  };

  const cancelJob = async () => {
    if (!jobId) return;
    
    try {
      await api.post(`/jobs/${jobId}/cancel`);
      // Update local state immediately
      setJob(prev => ({ ...prev, status: 'cancelled' }));
      // Close the progress dialog after a moment
      setTimeout(() => {
        setShowProgress(false);
        reset();
      }, 1000);
    } catch (err) {
      console.error('Error cancelling:', err);
      const errorMsg = err.response?.data?.detail || err.message || 'Failed to cancel job';
      showToast(`Failed to cancel: ${errorMsg}`, 'error');
    }
  };

  const reset = () => {
    setJobId(null);
    setJob(null);
    setShowProgress(false);
    setShowErrors(false);
  };

  // Progress Dialog
  if (showProgress && job) {
    const isRunning = job.status === 'processing' || job.status === 'pending';
    const isComplete = job.status === 'completed';
    const isFailed = job.status === 'failed';
    const isCancelled = job.status === 'cancelled';
    
    const errors = job.errors || [];
    const estimatedSeconds = isRunning && job.processed_items > 0 
      ? Math.ceil((job.total_items - job.processed_items) / 5)
      : 0;
    
    return (
      <Dialog open={showProgress} onClose={isRunning ? undefined : reset} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h6">
            {isRunning && 'Analyzing Products...'}
            {isComplete && 'Analysis Complete'}
            {isFailed && 'Analysis Failed'}
            {isCancelled && 'Analysis Cancelled'}
          </Typography>
          {!isRunning && (
            <IconButton onClick={reset} size="small">
              <CloseIcon />
            </IconButton>
          )}
        </DialogTitle>
        
        <DialogContent>
          {/* Progress bar */}
          <Box sx={{ mb: 2 }}>
            <LinearProgress 
              variant="determinate" 
              value={job.progress || 0} 
              sx={{ mb: 1, height: 8, borderRadius: 1 }}
              color={isComplete ? 'success' : isFailed ? 'error' : 'primary'}
            />
            
            <Typography variant="body2" color="text.secondary">
              {job.processed_items || 0} / {job.total_items || 0} products
            </Typography>
          </Box>
          
          {/* Stats */}
          <Box sx={{ mb: 2 }}>
            {job.success_count > 0 && (
              <Typography variant="body2" color="success.main" sx={{ mb: 0.5 }}>
                ✓ Success: {job.success_count}
              </Typography>
            )}
            {job.error_count > 0 && (
              <Typography variant="body2" color="error.main" sx={{ mb: 0.5 }}>
                ✗ Errors: {job.error_count}
              </Typography>
            )}
          </Box>
          
          {/* Estimated time */}
          {isRunning && estimatedSeconds > 0 && (
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 2 }}>
              ~{estimatedSeconds} seconds remaining
            </Typography>
          )}
          
          {/* Success message */}
          {isComplete && (
            <Alert severity="success" sx={{ mb: 2 }}>
              <AlertTitle>Analysis Complete</AlertTitle>
              <Typography variant="body2">
                Successfully analyzed {job.success_count} products
                {job.error_count > 0 && `, {job.error_count} errors`}
              </Typography>
            </Alert>
          )}
          
          {/* Error message */}
          {isFailed && (
            <Alert severity="error" sx={{ mb: 2 }}>
              <AlertTitle>Analysis Failed</AlertTitle>
              <Typography variant="body2">{errors[0] || 'Unknown error'}</Typography>
            </Alert>
          )}
          
          {/* Errors list */}
          {errors.length > 0 && (
            <Box sx={{ mt: 2 }}>
              <Button
                size="small"
                onClick={() => setShowErrors(!showErrors)}
                endIcon={showErrors ? <ExpandLess /> : <ExpandMore />}
              >
                View {errors.length} {errors.length === 1 ? 'error' : 'errors'}
              </Button>
              <Collapse in={showErrors}>
                <List dense sx={{ maxHeight: 200, overflow: 'auto', mt: 1 }}>
                  {errors.slice(0, 20).map((e, i) => (
                    <ListItem key={i}>
                      <ListItemText 
                        primary={e} 
                        primaryTypographyProps={{ variant: 'caption' }} 
                      />
                    </ListItem>
                  ))}
                  {errors.length > 20 && (
                    <ListItem>
                      <ListItemText 
                        primary={`... and ${errors.length - 20} more errors`}
                        primaryTypographyProps={{ variant: 'caption', color: 'text.secondary' }}
                      />
                    </ListItem>
                  )}
                </List>
              </Collapse>
            </Box>
          )}
        </DialogContent>
        
        <DialogActions>
          {isRunning && (
            <Button onClick={cancelJob} color="error">
              Cancel
            </Button>
          )}
          {!isRunning && (
            <Button onClick={reset} variant="contained">
              {isComplete ? 'Done' : 'Close'}
            </Button>
          )}
        </DialogActions>
      </Dialog>
    );
  }

  // Button
  const canBulkAnalyze = hasFeature('bulk_analyze');
  
  return (
    <>
      <Button
        variant="contained"
        onClick={startAnalysis}
        disabled={starting || !canBulkAnalyze}
        startIcon={starting ? <CircularProgress size={16} /> : <PlayArrow />}
        className={className}
        title={!canBulkAnalyze ? 'Bulk analysis requires Starter or higher' : ''}
      >
        {starting ? 'Starting...' : buttonText}
      </Button>

      <SupplierSelectionDialog
        open={showSupplierDialog}
        onClose={() => {
          setShowSupplierDialog(false);
          setProductsWithoutSuppliers([]);
          setGroupedByFile({});
        }}
        productsWithoutSuppliers={productsWithoutSuppliers}
        groupedByFile={groupedByFile}
        productCount={productCount}
        onConfirm={handleSupplierAssigned}
      />
    </>
  );
}

