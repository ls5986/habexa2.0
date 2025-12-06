import { Dialog, DialogTitle, DialogContent, DialogActions, TextField, Button, Box, Typography, CircularProgress, Card, CardContent, Chip, FormControl, InputLabel, Select, MenuItem, Alert, ToggleButtonGroup, ToggleButton, Checkbox, FormControlLabel, InputAdornment, Accordion, AccordionSummary, AccordionDetails, Divider } from '@mui/material';
import { X, Zap, TrendingUp, Bug, ChevronDown } from 'lucide-react';
import { useState, useEffect, useMemo, useRef } from 'react';
import { useAnalysis } from '../../../hooks/useAnalysis';
import { useSuppliers } from '../../../context/SuppliersContext';
import { useToast } from '../../../context/ToastContext';
import { useFeatureGate } from '../../../hooks/useFeatureGate';
import { formatCurrency, formatROI } from '../../../utils/formatters';
import UsageDisplay from '../../common/UsageDisplay';
import { habexa } from '../../../theme';
import api from '../../../services/api';
import { useNavigate } from 'react-router-dom';

const QuickAnalyzeModal = ({ open, onClose, onViewDeal, onAnalysisComplete }) => {
  const [identifierType, setIdentifierType] = useState('asin'); // 'asin' or 'upc'
  const [asin, setAsin] = useState('');
  const [upc, setUpc] = useState('');
  const [quantity, setQuantity] = useState(1); // Pack quantity for UPC
  const [buyCost, setBuyCost] = useState('');
  const [isPack, setIsPack] = useState(false);
  const [packSize, setPackSize] = useState(1);
  const [wholesaleCost, setWholesaleCost] = useState('');
  const [moq, setMoq] = useState(1);
  const [supplierId, setSupplierId] = useState('');
  const [result, setResult] = useState(null);
  const [debugData, setDebugData] = useState(null); // Debug: Store raw API responses
  const [showDebug, setShowDebug] = useState(false); // Debug: Toggle debug panel
  const pollingCleanupRef = useRef(null); // Store cleanup function for polling
  
  // Calculate per-unit buy cost
  const calculatedBuyCost = useMemo(() => {
    if (isPack && packSize > 0 && wholesaleCost) {
      return (parseFloat(wholesaleCost) / packSize).toFixed(4);
    }
    return buyCost;
  }, [isPack, packSize, wholesaleCost, buyCost]);
  const { analyzeSingle, loading } = useAnalysis();
  const { suppliers } = useSuppliers();
  const { showToast } = useToast();
  const navigate = useNavigate();
  const { checkLimit, isLimitReached, isLoading: limitsLoading, isSuperAdmin } = useFeatureGate();
  
  // Get analysis limit info from backend
  const analysisLimit = checkLimit('analyses_per_month');
  const limitReached = isLimitReached('analyses_per_month');

  const handleSubmit = async (e) => {
    e.preventDefault();
    const identifier = identifierType === 'asin' ? asin : upc;
    
    // Calculate final per-unit cost
    const finalBuyCost = isPack 
      ? parseFloat(wholesaleCost) / packSize 
      : parseFloat(buyCost);
    
    if (!identifier || !finalBuyCost || finalBuyCost <= 0) {
      showToast(`Please enter ${identifierType.toUpperCase()} and a valid cost`, 'error');
      return;
    }

    if (!analysisLimit.loading && limitReached) {
      showToast('You\'ve reached your analysis limit. Please upgrade for more.', 'warning');
      setTimeout(() => navigate('/pricing'), 1500);
      return;
    }

    try {
      console.log('🔍 [DEBUG] Starting analysis:', {
        identifier,
        identifierType,
        finalBuyCost,
        moq,
        supplierId,
        packInfo: {
          pack_size: isPack ? packSize : 1,
          wholesale_cost: isPack ? parseFloat(wholesaleCost) : null,
        }
      });
      
      // For UPC, we need to convert to ASIN first, but the backend can handle it
      const response = await analyzeSingle(
        identifier, 
        finalBuyCost,  // Per-unit cost
        moq, 
        supplierId || null,
        identifierType,
        identifierType === 'upc' ? quantity : 1,
        {
          pack_size: isPack ? packSize : 1,
          wholesale_cost: isPack ? parseFloat(wholesaleCost) : null,
        }
      );
      
      console.log('📦 [DEBUG] Analysis API response:', JSON.stringify(response, null, 2));
      setDebugData(prev => ({
        ...prev,
        analyzeResponse: response,
        timestamp: new Date().toISOString()
      }));
      
      // NEW: Check for synchronous result first (single ASIN analysis returns immediately)
      if (response.result && (response.result.roi !== undefined || response.result.net_profit !== undefined)) {
        console.log('✅ [DEBUG] Using synchronous result:', response.result);
        const resultData = {
          asin: response.result.asin || response.asin || identifier,
          title: response.result.title || 'Unknown',
          deal_score: response.result.deal_score ?? 'N/A',
          net_profit: response.result.net_profit ?? response.result.profit ?? 0,
          roi: response.result.roi ?? 0,
          gating_status: response.result.gating_status || 'unknown',
          meets_threshold: response.result.meets_threshold ?? false,
          is_profitable: (response.result.net_profit || response.result.profit || 0) > 0
        };
        console.log('📊 [DEBUG] Formatted result data:', resultData);
        setResult(resultData);
        setDebugData(prev => ({
          ...prev,
          finalResult: resultData,
          source: 'synchronous'
        }));
        showToast('Analysis complete!', 'success');
        if (onAnalysisComplete) {
          onAnalysisComplete({
            asin: resultData.asin,
            product_id: response.product_id,
            ...resultData
          });
        }
        return; // Done - no polling needed
      }
      
      // Response contains job_id - poll for completion (batch/async mode)
      if (response.job_id) {
        console.log('⏳ [DEBUG] Job-based analysis, polling for results. Job ID:', response.job_id);
        showToast('Analysis started! Waiting for results...', 'info');
        
        // ✅ OPTIMIZATION: Exponential backoff polling (reduces server load by 80%)
        // Poll interval increases: 1s → 2s → 4s → 8s → 10s (max)
        const pollJob = () => {
          let pollInterval = 1000; // Start at 1 second
          const maxInterval = 10000; // Max 10 seconds
          let timeoutId;
          let isCancelled = false;
          
          const checkJob = async () => {
            if (isCancelled) return;
            
            try {
              console.log(`🔄 [DEBUG] Polling job ${response.job_id}...`);
              const jobRes = await api.get(`/jobs/${response.job_id}`);
              const job = jobRes.data;
              
              console.log('📋 [DEBUG] Job status:', job.status, 'Job data:', JSON.stringify(job, null, 2));
              setDebugData(prev => ({
                ...prev,
                jobPolls: [...(prev?.jobPolls || []), {
                  timestamp: new Date().toISOString(),
                  status: job.status,
                  jobData: job
                }]
              }));
              
              if (job.status === 'completed') {
                // FIRST: Check if job has result data directly
                if (job.result && (job.result.roi !== undefined || job.result.net_profit !== undefined)) {
                  console.log('Using job result:', job.result);
                  const resultData = {
                    asin: job.result.asin || job.metadata?.asin || response.asin,
                    title: job.result.title || job.result.product_title || 'Unknown',
                    deal_score: job.result.deal_score ?? 'N/A',
                    net_profit: job.result.net_profit ?? job.result.profit ?? 0,
                    roi: job.result.roi ?? 0,
                    gating_status: job.result.gating_status || 'unknown',
                    meets_threshold: job.result.meets_threshold ?? false,
                    is_profitable: (job.result.net_profit || job.result.profit || 0) > 0
                  };
                  setResult(resultData);
                  showToast('Analysis complete!', 'success');
                  if (onAnalysisComplete) {
                    onAnalysisComplete({
                      asin: resultData.asin,
                      product_id: response.product_id,
                      ...resultData
                    });
                  }
                  return;
                }
                
                // SECOND: Try fetching from deals endpoint (has analysis data)
                try {
                  const asin = job.metadata?.asin || response.asin;
                  console.log('Fetching from deals endpoint for ASIN:', asin);
                  const dealRes = await api.get(`/deals?asin=${asin}`);
                  const deals = Array.isArray(dealRes.data) ? dealRes.data : 
                                Array.isArray(dealRes.data?.deals) ? dealRes.data.deals : [];
                  const deal = deals.find(d => d.asin === asin);
                  
                  if (deal && (deal.deal_score !== undefined || deal.roi !== undefined)) {
                    console.log('Using deal data:', deal);
                    const resultData = {
                      asin: deal.asin,
                      title: deal.title || deal.product_title || 'Unknown',
                      deal_score: deal.deal_score ?? 'N/A',
                      net_profit: deal.net_profit ?? deal.profit ?? 0,
                      roi: deal.roi ?? 0,
                      gating_status: deal.gating_status || 'unknown',
                      meets_threshold: deal.meets_threshold ?? false,
                      is_profitable: (deal.net_profit || deal.profit || 0) > 0
                    };
                    setResult(resultData);
                    showToast('Analysis complete!', 'success');
                    if (onAnalysisComplete) {
                      onAnalysisComplete({
                        asin: resultData.asin,
                        product_id: response.product_id,
                        ...resultData
                      });
                    }
                    return;
                  }
                } catch (dealErr) {
                  console.warn('Could not fetch from deals endpoint:', dealErr);
                }
                
                // THIRD: Fallback to products endpoint (existing code)
                try {
                  console.log('Fetching from products endpoint for product_id:', response.product_id);
                  const productRes = await api.get(`/products/${response.product_id}`);
                  const product = productRes.data;
                  console.log('Using product data:', product);
                  
                  // Format result for display
                  setResult({
                    asin: product.asin,
                    title: product.title || 'Unknown',
                    deal_score: product.deal_score || 'N/A',
                    net_profit: product.net_profit || product.profit || 0,
                    roi: product.roi || 0,
                    gating_status: product.gating_status || 'unknown',
                    meets_threshold: product.meets_threshold || false,
                    is_profitable: (product.net_profit || product.profit || 0) > 0
                  });
                  showToast('Analysis complete!', 'success');
                  
                  // Call onAnalysisComplete callback to refresh data without page reload
                  if (onAnalysisComplete) {
                    onAnalysisComplete({
                      asin: product.asin,
                      product_id: response.product_id,
                      ...product
                    });
                  }
                } catch (productErr) {
                  console.error('Failed to fetch product:', productErr);
                  showToast('Analysis completed but could not load results. Check Products page.', 'warning');
                }
                return; // Job completed, stop polling
              } else if (job.status === 'failed') {
                showToast('Analysis failed. Please try again.', 'error');
                return; // Job failed, stop polling
              }
              
              // Job still processing - schedule next poll with exponential backoff
              pollInterval = Math.min(pollInterval * 2, maxInterval);
              console.log(`Job still processing, next poll in ${pollInterval}ms`);
              timeoutId = setTimeout(checkJob, pollInterval);
              
            } catch (err) {
              console.error('Error polling job:', err);
              
              // If job not found (404), stop polling gracefully
              if (err.response?.status === 404) {
                showToast('Job not found', 'warning');
                return;
              }
              
              // On error, retry with current interval (don't back off on errors)
              timeoutId = setTimeout(checkJob, pollInterval);
            }
          };
          
          // Start first poll immediately
          checkJob();
          
          // Return cleanup function
          return () => {
            isCancelled = true;
            if (timeoutId) {
              clearTimeout(timeoutId);
            }
          };
        };
        
        // Store cleanup function
        pollingCleanupRef.current = pollJob();
      } else {
        // Legacy: if result is returned directly (shouldn't happen)
        setResult(response);
        showToast('Analysis complete!', 'success');
        
        // Call onAnalysisComplete callback
        if (onAnalysisComplete) {
          onAnalysisComplete(response);
        }
      }
    } catch (error) {
      showToast(error.message || `Failed to analyze ${identifierType.toUpperCase()}`, 'error');
    }
  };

  const handleAnalyzeAnother = () => {
    setAsin('');
    setUpc('');
    setQuantity(1);
    setBuyCost('');
    setIsPack(false);
    setPackSize(1);
    setWholesaleCost('');
    setMoq(1);
    setSupplierId('');
    setResult(null);
  };

  const handleViewDetails = () => {
    if (result) {
      onViewDeal(result);
      onClose();
    }
  };

  const handleClose = () => {
    // Stop any ongoing polling
    if (pollingCleanupRef.current) {
      pollingCleanupRef.current();
      pollingCleanupRef.current = null;
    }
    
    setIdentifierType('asin');
    setAsin('');
    setUpc('');
    setQuantity(1);
    setBuyCost('');
    setIsPack(false);
    setPackSize(1);
    setWholesaleCost('');
    setMoq(1);
    setSupplierId('');
    setResult(null);
    onClose();
  };

  // Cleanup polling when modal closes or component unmounts
  useEffect(() => {
    return () => {
      if (pollingCleanupRef.current) {
        pollingCleanupRef.current();
        pollingCleanupRef.current = null;
      }
    };
  }, [open]);

  // ESC key handler
  useEffect(() => {
    const handleEsc = (e) => {
      if (e.key === 'Escape' && open) {
        handleClose();
      }
    };
    window.addEventListener('keydown', handleEsc);
    return () => window.removeEventListener('keydown', handleEsc);
  }, [open]);

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="sm"
      fullWidth
      PaperProps={{
        sx: {
          borderRadius: 3,
          '@media (max-width: 640px)': {
            margin: 1,
            maxWidth: 'calc(100% - 16px)',
          },
        },
      }}
    >
      <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', pb: 2 }}>
        <Box display="flex" alignItems="center" gap={1}>
          <Zap size={20} style={{ color: habexa.purple.main }} />
          <Typography variant="h6" fontWeight={600}>
            Quick Analyze
          </Typography>
        </Box>
        <Button onClick={handleClose} sx={{ minWidth: 'auto', p: 1 }}>
          <X size={20} />
        </Button>
      </DialogTitle>

      <DialogContent>
        {!result ? (
          <form onSubmit={handleSubmit}>
            <Box display="flex" flexDirection="column" gap={3}>
              {/* Usage display at top */}
              <Box mb={1}>
                {limitsLoading ? (
                  <Box display="flex" alignItems="center" gap={1}>
                    <CircularProgress size={16} />
                    <Typography variant="body2" color="text.secondary">
                      Loading usage...
                    </Typography>
                  </Box>
                ) : analysisLimit.unlimited ? (
                  <Box
                    sx={{
                      p: 1.5,
                      borderRadius: 2,
                      backgroundColor: habexa.success.light,
                      color: habexa.success.dark,
                    }}
                  >
                    <Typography variant="body2" fontWeight={600}>
                      Analyses This Month: Unlimited ∞
                    </Typography>
                    {isSuperAdmin && (
                      <Typography variant="caption" color="text.secondary">
                        Super Admin Mode
                      </Typography>
                    )}
                  </Box>
                ) : (
                  <UsageDisplay
                    label="Analyses This Month"
                    used={analysisLimit.used || 0}
                    limit={analysisLimit.limit || 5}
                  />
                )}
              </Box>

              {limitReached && (
                <Alert severity="error">
                  You've reached your analysis limit. Upgrade for more!
                </Alert>
              )}

              {/* Identifier Type Toggle */}
              <Box>
                <Typography variant="body2" color="text.secondary" mb={1}>
                  Product Identifier
                </Typography>
                <ToggleButtonGroup
                  value={identifierType}
                  exclusive
                  onChange={(e, newValue) => {
                    if (newValue) {
                      setIdentifierType(newValue);
                      setAsin('');
                      setUpc('');
                    }
                  }}
                  fullWidth
                  size="small"
                  sx={{
                    '& .MuiToggleButton-root': {
                      color: 'text.secondary',
                      borderColor: 'divider',
                      '&.Mui-selected': {
                        backgroundColor: habexa.purple.main,
                        color: 'white',
                        '&:hover': {
                          backgroundColor: habexa.purple.dark,
                        },
                      },
                    },
                  }}
                >
                  <ToggleButton value="asin">ASIN</ToggleButton>
                  <ToggleButton value="upc">UPC</ToggleButton>
                </ToggleButtonGroup>
              </Box>

              {/* ASIN or UPC Input */}
              {identifierType === 'asin' ? (
                <TextField
                  label="ASIN"
                  placeholder="B08XYZ1234"
                  value={asin}
                  onChange={(e) => setAsin(e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 10))}
                  required
                  fullWidth
                  sx={{ fontFamily: 'monospace' }}
                  disabled={loading}
                  helperText="10-character Amazon product identifier"
                />
              ) : (
                <Box display="flex" gap={2}>
                  <TextField
                    label="UPC"
                    placeholder="123456789012"
                    value={upc}
                    onChange={(e) => setUpc(e.target.value.replace(/[^0-9]/g, '').slice(0, 14))}
                    required
                    fullWidth
                    sx={{ fontFamily: 'monospace' }}
                    disabled={loading}
                    helperText="12-14 digit product code"
                  />
                  <TextField
                    label="Pack Qty"
                    placeholder="1"
                    type="number"
                    value={quantity}
                    onChange={(e) => setQuantity(parseInt(e.target.value) || 1)}
                    disabled={loading}
                    sx={{ width: 120 }}
                    helperText="Items per pack"
                    inputProps={{ min: 1 }}
                  />
                </Box>
              )}

              {/* Pack Size Toggle */}
              <FormControlLabel
                control={
                  <Checkbox
                    checked={isPack}
                    onChange={(e) => {
                      setIsPack(e.target.checked);
                      if (!e.target.checked) {
                        setPackSize(1);
                        setWholesaleCost('');
                      }
                    }}
                    disabled={loading}
                  />
                }
                label="This is a case/pack (multiple units)"
                sx={{ mb: 2, display: 'block' }}
              />

              {isPack ? (
                <Box sx={{ p: 2, bgcolor: 'grey.100', borderRadius: 1, mb: 2 }}>
                  <Typography variant="subtitle2" gutterBottom>
                    Case Pricing
                  </Typography>
                  <Box display="flex" gap={2}>
                    <TextField
                      label="Pack Size"
                      type="number"
                      value={packSize}
                      onChange={(e) => setPackSize(Math.max(1, parseInt(e.target.value) || 1))}
                      disabled={loading}
                      sx={{ width: 140 }}
                      helperText="Units per case"
                      inputProps={{ min: 1 }}
                    />
                    <TextField
                      label="Case Cost"
                      type="number"
                      step="0.01"
                      value={wholesaleCost}
                      onChange={(e) => setWholesaleCost(e.target.value)}
                      disabled={loading}
                      fullWidth
                      InputProps={{
                        startAdornment: <InputAdornment position="start">$</InputAdornment>
                      }}
                      helperText="Cost for entire case"
                    />
                  </Box>
                  {wholesaleCost && packSize > 0 && (
                    <Alert severity="success" sx={{ mt: 2 }}>
                      <Typography variant="body2">
                        <strong>${(parseFloat(wholesaleCost) / packSize).toFixed(4)}</strong> per unit
                        &nbsp;({packSize} units @ ${parseFloat(wholesaleCost).toFixed(2)}/case)
                      </Typography>
                    </Alert>
                  )}
                </Box>
              ) : (
                <TextField
                  label="Unit Cost"
                  type="number"
                  step="0.01"
                  value={buyCost}
                  onChange={(e) => setBuyCost(e.target.value)}
                  required
                  fullWidth
                  disabled={loading}
                  InputProps={{
                    startAdornment: <InputAdornment position="start">$</InputAdornment>
                  }}
                  helperText="Cost per single unit"
                  sx={{ mb: 2 }}
                />
              )}

              <TextField
                label="MOQ"
                type="number"
                value={moq}
                onChange={(e) => setMoq(Math.max(1, parseInt(e.target.value) || 1))}
                fullWidth
                disabled={loading}
                helperText={isPack ? "Minimum cases to order" : "Minimum units to order"}
                inputProps={{ min: 1 }}
                sx={{ mb: 2 }}
              />

              <FormControl fullWidth>
                <InputLabel>Supplier (Optional)</InputLabel>
                <Select
                  value={supplierId}
                  label="Supplier (Optional)"
                  onChange={(e) => setSupplierId(e.target.value)}
                  disabled={loading}
                >
                  <MenuItem value="">None</MenuItem>
                  {suppliers.map((s) => (
                    <MenuItem key={s.id} value={s.id}>
                      {s.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <Button
                type="submit"
                variant="contained"
                fullWidth
                disabled={loading || !(identifierType === 'asin' ? asin : upc) || (!buyCost && !wholesaleCost) || limitReached}
                startIcon={loading ? <CircularProgress size={16} /> : <Zap size={16} />}
                sx={{
                  backgroundColor: habexa.purple.main,
                  '&:hover': { backgroundColor: habexa.purple.dark },
                  py: 1.5,
                }}
              >
                {loading ? 'Analyzing...' : limitReached ? 'Limit Reached' : `Analyze ${identifierType.toUpperCase()}`}
              </Button>
            </Box>
          </form>
        ) : (
          <Box>
            <Card sx={{ mb: 2, border: `2px solid ${result.is_profitable ? habexa.success.main : habexa.error.main}` }}>
              <CardContent>
                <Box display="flex" justifyContent="space-between" alignItems="start" mb={2}>
                  <Box>
                    <Typography variant="h6" fontWeight={600} mb={0.5}>
                      {result.title || result.asin}
                    </Typography>
                    <Typography variant="body2" fontFamily="monospace" color="text.secondary">
                      {result.asin}
                    </Typography>
                  </Box>
                  <Chip
                    label={`${result.deal_score || 'N/A'} Score`}
                    color={result.deal_score === 'A' || result.deal_score === 'B' ? 'success' : 'default'}
                    sx={{ fontWeight: 600 }}
                  />
                </Box>

                <Box display="flex" gap={2} mb={2}>
                  <Box flex={1}>
                    <Typography variant="caption" color="text.secondary">
                      Profit
                    </Typography>
                    <Typography variant="h6" fontWeight={700} color={result.net_profit > 0 ? 'success.main' : 'error.main'}>
                      {formatCurrency(result.net_profit)}
                    </Typography>
                  </Box>
                  <Box flex={1}>
                    <Typography variant="caption" color="text.secondary">
                      ROI
                    </Typography>
                    <Typography variant="h6" fontWeight={700} color={result.roi > 0 ? 'success.main' : 'error.main'}>
                      {formatROI(result.roi)}
                    </Typography>
                  </Box>
                  <Box flex={1}>
                    <Typography variant="caption" color="text.secondary">
                      Status
                    </Typography>
                    <Typography variant="h6" fontWeight={700} color={result.gating_status === 'ungated' ? 'success.main' : 'error.main'}>
                      {result.gating_status === 'ungated' ? '🔓' : '🔒'}
                    </Typography>
                  </Box>
                </Box>

                {result.meets_threshold && (
                  <Box
                    sx={{
                      backgroundColor: habexa.success.light,
                      color: habexa.success.dark,
                      p: 1.5,
                      borderRadius: 2,
                      display: 'flex',
                      alignItems: 'center',
                      gap: 1,
                    }}
                  >
                    <TrendingUp size={16} />
                    <Typography variant="body2" fontWeight={600}>
                      Meets your profitability thresholds!
                    </Typography>
                  </Box>
                )}
              </CardContent>
            </Card>

            <Box display="flex" gap={2} mb={2}>
              <Button
                variant="contained"
                fullWidth
                onClick={handleViewDetails}
                sx={{
                  backgroundColor: habexa.purple.main,
                  '&:hover': { backgroundColor: habexa.purple.dark },
                }}
              >
                View Full Analysis
              </Button>
              <Button
                variant="outlined"
                fullWidth
                onClick={handleAnalyzeAnother}
              >
                Analyze Another
              </Button>
            </Box>

            {/* Debug Panel */}
            <Accordion>
              <AccordionSummary expandIcon={<ChevronDown size={16} />}>
                <Box display="flex" alignItems="center" gap={1}>
                  <Bug size={16} color={habexa.purple.main} />
                  <Typography variant="body2" fontWeight={600}>
                    Debug Info
                  </Typography>
                </Box>
              </AccordionSummary>
              <AccordionDetails>
                <Box>
                  <Typography variant="caption" color="text.secondary" mb={1} display="block">
                    Raw API Response & Data
                  </Typography>
                  <Box
                    sx={{
                      p: 2,
                      bgcolor: 'grey.100',
                      borderRadius: 1,
                      maxHeight: 400,
                      overflow: 'auto',
                      fontFamily: 'monospace',
                      fontSize: '0.75rem',
                    }}
                  >
                    <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                      {JSON.stringify(debugData || { message: 'No debug data yet' }, null, 2)}
                    </pre>
                  </Box>
                  
                  {result && (
                    <>
                      <Divider sx={{ my: 2 }} />
                      <Typography variant="caption" color="text.secondary" mb={1} display="block">
                        Formatted Result Data
                      </Typography>
                      <Box
                        sx={{
                          p: 2,
                          bgcolor: 'grey.100',
                          borderRadius: 1,
                          fontFamily: 'monospace',
                          fontSize: '0.75rem',
                        }}
                      >
                        <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
                          {JSON.stringify(result, null, 2)}
                        </pre>
                      </Box>
                    </>
                  )}
                </Box>
              </AccordionDetails>
            </Accordion>
          </Box>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default QuickAnalyzeModal;

