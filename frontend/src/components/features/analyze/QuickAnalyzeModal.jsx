import { Dialog, DialogTitle, DialogContent, DialogActions, TextField, Button, Box, Typography, CircularProgress, Card, CardContent, Chip, FormControl, InputLabel, Select, MenuItem, Alert, ToggleButtonGroup, ToggleButton } from '@mui/material';
import { X, Zap, TrendingUp } from 'lucide-react';
import { useState, useEffect } from 'react';
import { useAnalysis } from '../../../hooks/useAnalysis';
import { useSuppliers } from '../../../hooks/useSuppliers';
import { useToast } from '../../../context/ToastContext';
import { useFeatureGate } from '../../../hooks/useFeatureGate';
import { formatCurrency, formatROI } from '../../../utils/formatters';
import UsageDisplay from '../../common/UsageDisplay';
import { habexa } from '../../../theme';
import api from '../../../services/api';
import { useNavigate } from 'react-router-dom';

const QuickAnalyzeModal = ({ open, onClose, onViewDeal }) => {
  const [identifierType, setIdentifierType] = useState('asin'); // 'asin' or 'upc'
  const [asin, setAsin] = useState('');
  const [upc, setUpc] = useState('');
  const [quantity, setQuantity] = useState(1); // Pack quantity for UPC
  const [buyCost, setBuyCost] = useState('');
  const [moq, setMoq] = useState(1);
  const [supplierId, setSupplierId] = useState('');
  const [result, setResult] = useState(null);
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
    if (!identifier || !buyCost) {
      showToast(`Please enter ${identifierType.toUpperCase()} and buy cost`, 'error');
      return;
    }

    if (!analysisLimit.loading && limitReached) {
      showToast('You\'ve reached your analysis limit. Please upgrade for more.', 'warning');
      setTimeout(() => navigate('/pricing'), 1500);
      return;
    }

    try {
      // For UPC, we need to convert to ASIN first, but the backend can handle it
      const response = await analyzeSingle(
        identifier, 
        parseFloat(buyCost), 
        moq, 
        supplierId || null,
        identifierType,
        identifierType === 'upc' ? quantity : 1
      );
      
      // Response contains job_id - poll for completion
      if (response.job_id) {
        showToast('Analysis started! Waiting for results...', 'info');
        
        // Poll for job completion
        const pollJob = async () => {
          const maxAttempts = 60; // 60 seconds max
          let attempts = 0;
          
          const checkJob = async () => {
            try {
              const jobRes = await api.get(`/jobs/${response.job_id}`);
              const job = jobRes.data;
              
              if (job.status === 'completed') {
                // Fetch the product/analysis result
                const productRes = await api.get(`/products/${response.product_id}`);
                const product = productRes.data;
                
                // Format result for display
                setResult({
                  asin: product.asin,
                  title: product.title,
                  deal_score: product.deal_score || 'N/A',
                  net_profit: product.net_profit || 0,
                  roi: product.roi || 0,
                  gating_status: product.gating_status || 'unknown',
                  meets_threshold: product.meets_threshold || false,
                  is_profitable: (product.net_profit || 0) > 0
                });
                showToast('Analysis complete!', 'success');
                
                // Trigger refresh of products list if callback exists
                if (onViewDeal) {
                  setTimeout(() => {
                    window.location.reload(); // Simple refresh for now
                  }, 1000);
                }
              } else if (job.status === 'failed') {
                showToast('Analysis failed. Please try again.', 'error');
              } else if (attempts < maxAttempts) {
                // Still processing, poll again
                attempts++;
                setTimeout(checkJob, 1000);
              } else {
                showToast('Analysis is taking longer than expected. Check Products page for results.', 'warning');
              }
            } catch (err) {
              console.error('Error polling job:', err);
              if (attempts < maxAttempts) {
                attempts++;
                setTimeout(checkJob, 1000);
              } else {
                showToast('Could not check analysis status. Check Products page for results.', 'warning');
              }
            }
          };
          
          checkJob();
        };
        
        pollJob();
      } else {
        // Legacy: if result is returned directly (shouldn't happen)
        setResult(response);
        showToast('Analysis complete!', 'success');
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
    setIdentifierType('asin');
    setAsin('');
    setUpc('');
    setQuantity(1);
    setBuyCost('');
    setMoq(1);
    setSupplierId('');
    setResult(null);
    onClose();
  };

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
      PaperProps={{
        sx: {
          borderRadius: 3,
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

              <Box display="flex" gap={2}>
                <TextField
                  label="Your Cost"
                  type="number"
                  value={buyCost}
                  onChange={(e) => setBuyCost(e.target.value)}
                  required
                  InputProps={{ startAdornment: '$' }}
                  fullWidth
                  disabled={loading}
                  helperText={identifierType === 'upc' ? `Cost per pack of ${quantity}` : 'Cost per unit'}
                />
                <TextField
                  label="MOQ"
                  type="number"
                  value={moq}
                  onChange={(e) => setMoq(parseInt(e.target.value) || 1)}
                  fullWidth
                  disabled={loading}
                  helperText="Minimum order quantity"
                />
              </Box>

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
                disabled={loading || !(identifierType === 'asin' ? asin : upc) || !buyCost || limitReached}
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

            <Box display="flex" gap={2}>
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
          </Box>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default QuickAnalyzeModal;

