import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Box, Typography, TextField, Button, Card, CardContent, 
  RadioGroup, FormControlLabel, Radio, Select, MenuItem, 
  FormControl, InputLabel, Alert, Chip, Divider, CircularProgress, Grid
} from '@mui/material';
import { Zap, ExternalLink, TrendingUp, DollarSign, RefreshCw, Plus, Trash2 } from 'lucide-react';
import { useAnalysis } from '../hooks/useAnalysis';
import { useSuppliers } from '../hooks/useSuppliers';
import { useToast } from '../context/ToastContext';
import { handleApiError } from '../utils/errorHandler';
import { habexa } from '../theme';
import api from '../services/api';

const Analyze = () => {
  const navigate = useNavigate();
  const [mode, setMode] = useState('single');
  const [asin, setAsin] = useState('');
  const [buyCost, setBuyCost] = useState('');
  const [moq, setMoq] = useState(1);
  const [supplierId, setSupplierId] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [addingToProducts, setAddingToProducts] = useState(false);
  const [recentAnalyses, setRecentAnalyses] = useState([]);
  const pollingCleanupRef = useRef(null);
  
  // Batch mode state
  const [batchItems, setBatchItems] = useState([{ asin: '', buy_cost: '', moq: 1 }]);
  const [batchResults, setBatchResults] = useState(null);
  
  const { analyzeSingle, analyzeBatch, loading } = useAnalysis();
  const { suppliers } = useSuppliers();
  const { showToast } = useToast();

  // Load recent analyses from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem('recentAnalyses');
      if (stored) {
        setRecentAnalyses(JSON.parse(stored));
      }
    } catch (err) {
      console.error('Failed to load recent analyses:', err);
    }
  }, []);

  // Save recent analyses to localStorage
  useEffect(() => {
    if (recentAnalyses.length > 0) {
      try {
        localStorage.setItem('recentAnalyses', JSON.stringify(recentAnalyses.slice(0, 10)));
      } catch (err) {
        console.error('Failed to save recent analyses:', err);
      }
    }
  }, [recentAnalyses]);

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollingCleanupRef.current) {
        pollingCleanupRef.current();
        pollingCleanupRef.current = null;
      }
    };
  }, []);

  const handleAnalyze = async () => {
    if (mode === 'single') {
      await handleSingleAnalyze();
    } else {
      await handleBatchAnalyze();
    }
  };

  const handleSingleAnalyze = async () => {
    if (!asin || !buyCost) {
      showToast('Please enter ASIN and buy cost', 'error');
      return;
    }
    
    setResult(null);
    setError(null);
    setAnalyzing(true);
    
    // Stop any existing polling
    if (pollingCleanupRef.current) {
      pollingCleanupRef.current();
      pollingCleanupRef.current = null;
    }
    
    try {
      const response = await analyzeSingle(asin, parseFloat(buyCost), moq, supplierId || null);
      
      console.log('✅ Analysis API response:', response); // DEBUG
      
      // NEW: Single ASIN is now synchronous - results returned immediately!
      if (response && response.result && response.status === 'completed') {
        console.log('✅ Analysis completed synchronously:', response.result); // DEBUG
        const resultData = {
          asin: response.asin,
          title: response.result.title || 'Unknown',
          deal_score: response.result.deal_score ?? 'N/A',
          net_profit: response.result.net_profit ?? 0,
          roi: response.result.roi ?? 0,
          gating_status: response.result.gating_status || 'unknown',
          meets_threshold: response.result.meets_threshold ?? false,
          is_profitable: (response.result.net_profit || 0) > 0,
          sell_price: response.result.sell_price,
          buy_cost: response.result.buy_cost || parseFloat(buyCost),
          product_id: response.product_id,
          image_url: response.result.image_url,
          brand: response.result.brand,
          category: response.result.category,
        };
        setResult(resultData);
        setAnalyzing(false);
        showToast('Analysis complete!', 'success');
        setRecentAnalyses(prev => [resultData, ...prev].slice(0, 10));
        return;
      }
      
      // LEGACY: Handle job-based response (only for batch operations now)
      if (response && response.job_id) {
        console.log('⚠️ Got job_id response (should only happen for batch):', response.job_id); // DEBUG
        showToast('Analysis started! Waiting for results...', 'info');
        
        // ✅ OPTIMIZATION: Exponential backoff polling (same as QuickAnalyzeModal)
        const pollJob = () => {
          let pollInterval = 1000; // Start at 1 second
          const maxInterval = 10000; // Max 10 seconds
          let timeoutId;
          let isCancelled = false;
          const jobId = response.job_id; // Capture job_id in closure
          
          const checkJob = async () => {
            if (isCancelled) {
              console.log('❌ Polling cancelled'); // DEBUG
              return;
            }
            
            try {
              console.log(`🔄 Polling job: ${jobId} (interval: ${pollInterval}ms)`); // DEBUG
              const jobRes = await api.get(`/jobs/${jobId}`);
              const job = jobRes.data;
              console.log(`📊 Job status: ${job.status}`, job); // DEBUG
              
              if (job.status === 'completed') {
                console.log('✅ Job completed! Fetching results...'); // DEBUG
                // Job completed - fetch product/deal data
                try {
                  const productId = response.product_id || job.metadata?.product_id;
                  const jobAsin = response.asin || job.metadata?.asin;
                  console.log('📦 Fetching data for product_id:', productId, 'asin:', jobAsin); // DEBUG
                  
                  // Try fetching from deals endpoint first (has full analysis data)
                  try {
                    const dealRes = await api.get(`/deals?asin=${jobAsin}`);
                    const deals = Array.isArray(dealRes.data) ? dealRes.data : 
                                  Array.isArray(dealRes.data?.deals) ? dealRes.data.deals : [];
                    const deal = deals.find(d => d.asin === jobAsin);
                    
                    if (deal && (deal.deal_score !== undefined || deal.roi !== undefined)) {
                      const resultData = {
                        asin: deal.asin,
                        title: deal.title || deal.product_title || 'Unknown',
                        deal_score: deal.deal_score ?? 'N/A',
                        net_profit: deal.net_profit ?? deal.profit ?? 0,
                        roi: deal.roi ?? 0,
                        gating_status: deal.gating_status || 'unknown',
                        meets_threshold: deal.meets_threshold ?? false,
                        is_profitable: (deal.net_profit || deal.profit || 0) > 0,
                        sell_price: deal.sell_price,
                        buy_cost: deal.buy_cost || parseFloat(buyCost),
                        product_id: productId,
                        image_url: deal.image_url,
                        brand: deal.brand,
                        category: deal.category,
                      };
                      setResult(resultData);
                      setAnalyzing(false);
                      showToast('Analysis complete!', 'success');
                      
                      // Add to recent analyses
                      setRecentAnalyses(prev => [resultData, ...prev].slice(0, 10));
                      return;
                    }
                  } catch (dealErr) {
                    console.warn('Could not fetch from deals endpoint:', dealErr);
                  }
                  
                  // Fallback to products endpoint
                  if (productId) {
                    const productRes = await api.get(`/products/${productId}`);
                    const product = productRes.data;
                    
                    const resultData = {
                      asin: product.asin,
                      title: product.title || 'Unknown',
                      deal_score: product.deal_score || 'N/A',
                      net_profit: product.net_profit || product.profit || 0,
                      roi: product.roi || 0,
                      gating_status: product.gating_status || 'unknown',
                      meets_threshold: product.meets_threshold ?? false,
                      is_profitable: (product.net_profit || product.profit || 0) > 0,
                      sell_price: product.sell_price,
                      buy_cost: product.buy_cost || parseFloat(buyCost),
                      product_id: productId,
                      image_url: product.image_url,
                      brand: product.brand,
                      category: product.category,
                    };
                    setResult(resultData);
                    setAnalyzing(false);
                    showToast('Analysis complete!', 'success');
                    
                    // Add to recent analyses
                    setRecentAnalyses(prev => [resultData, ...prev].slice(0, 10));
                    return;
                  }
                  
                  // If we can't fetch product, show job result if available
                  if (job.result) {
                    console.log('✅ Using job.result:', job.result); // DEBUG
                    const resultData = {
                      asin: job.result.asin || job.metadata?.asin || asin,
                      title: job.result.title || job.result.product_title || 'Unknown',
                      deal_score: job.result.deal_score ?? 'N/A',
                      net_profit: job.result.net_profit ?? job.result.profit ?? 0,
                      roi: job.result.roi ?? 0,
                      gating_status: job.result.gating_status || 'unknown',
                      meets_threshold: job.result.meets_threshold ?? false,
                      is_profitable: (job.result.net_profit || job.result.profit || 0) > 0,
                      product_id: response.product_id,
                    };
                    setResult(resultData);
                    setAnalyzing(false);
                    showToast('Analysis complete!', 'success');
                    setRecentAnalyses(prev => [resultData, ...prev].slice(0, 10));
                    return;
                  }
                  
                  // Last resort - show basic info
                  console.log('⚠️ No product/deal data found, showing basic info'); // DEBUG
                  setResult({
                    asin: response.asin || asin,
                    title: 'Analysis completed - check Products page for details',
                    product_id: response.product_id,
                  });
                  setAnalyzing(false);
                  showToast('Analysis complete! Check Products page for full details.', 'success');
                  
                } catch (fetchErr) {
                  console.error('Failed to fetch analysis results:', fetchErr);
                  setAnalyzing(false);
                  showToast('Analysis completed but could not load results. Check Products page.', 'warning');
                }
                return; // Job completed, stop polling
              } else if (job.status === 'failed') {
                setAnalyzing(false);
                showToast('Analysis failed. Please try again.', 'error');
                setError('Analysis job failed');
                return; // Job failed, stop polling
              }
              
              // Job still processing - schedule next poll with exponential backoff
              pollInterval = Math.min(pollInterval * 2, maxInterval);
              timeoutId = setTimeout(checkJob, pollInterval);
              
            } catch (err) {
              console.error('❌ Error polling job:', err);
              console.error('Error details:', err.response?.data, err.message); // DEBUG
              
              // If job not found (404), stop polling gracefully
              if (err.response?.status === 404) {
                console.error('❌ Job not found (404)'); // DEBUG
                setAnalyzing(false);
                showToast('Job not found', 'warning');
                setError('Analysis job not found');
                return;
              }
              
              // On error, retry with current interval (don't back off on errors)
              console.log(`⚠️ Retrying poll in ${pollInterval}ms after error`); // DEBUG
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
        
        // Store cleanup function and start polling immediately
        pollingCleanupRef.current = pollJob();
        console.log('✅ Polling function started, cleanup stored'); // DEBUG
        return;
      }
      
      // Handle direct result response (shouldn't happen with async jobs)
      if (response.asin || response.product_id) {
        console.log('✅ Direct result (no job_id):', response); // DEBUG
        setResult(response);
        setAnalyzing(false);
        showToast('Analysis complete!', 'success');
        setRecentAnalyses(prev => [response, ...prev].slice(0, 10));
      } else {
        console.error('❌ Unexpected response format:', response); // DEBUG
        setAnalyzing(false);
        setError('Unexpected response format from analysis API. Expected job_id or product data.');
      }
    } catch (err) {
      console.error('❌ Analysis error:', err); // DEBUG
      setAnalyzing(false);
      const errorMessage = handleApiError(err, showToast);
      setError(errorMessage);
    }
  };

  const handleBatchAnalyze = async () => {
    // Validate all batch items
    const validItems = batchItems.filter(item => item.asin && item.buy_cost);
    if (validItems.length === 0) {
      showToast('Please enter at least one ASIN and buy cost', 'error');
      return;
    }
    
    setBatchResults(null);
    setError(null);
    setAnalyzing(true);
    
    // Stop any existing polling
    if (pollingCleanupRef.current) {
      pollingCleanupRef.current();
      pollingCleanupRef.current = null;
    }
    
    try {
      // Format items for API
      const items = validItems.map(item => ({
        asin: item.asin.trim().toUpperCase(),
        buy_cost: parseFloat(item.buy_cost),
        moq: parseInt(item.moq) || 1,
        supplier_id: supplierId || null
      }));
      
      const response = await analyzeBatch(items);
      console.log('✅ Batch analysis response:', response); // DEBUG
      
      if (response.mode === 'sync') {
        // INSTANT RESULTS!
        console.log('✅ Synchronous batch analysis - instant results!');
        setBatchResults({
          mode: 'sync',
          total: response.total,
          results: response.results || []
        });
        setAnalyzing(false);
        showToast(`✅ Analyzed ${response.total} product${response.total > 1 ? 's' : ''} instantly!`, 'success');
      } else if (response.mode === 'async') {
        // BACKGROUND PROCESSING
        console.log('⏳ Async batch analysis - polling job:', response.job_id);
        showToast(`⏳ Analyzing ${response.total} products in background...`, 'info');
        
        // Navigate to jobs page or start polling
        navigate(`/jobs/${response.job_id}`);
        setAnalyzing(false);
      } else {
        throw new Error('Unexpected response format');
      }
    } catch (err) {
      console.error('❌ Batch analysis error:', err);
      setAnalyzing(false);
      const errorMessage = handleApiError(err, showToast);
      setError(errorMessage);
    }
  };

  const handleAddBatchRow = () => {
    setBatchItems([...batchItems, { asin: '', buy_cost: '', moq: 1 }]);
  };

  const handleRemoveBatchRow = (index) => {
    if (batchItems.length > 1) {
      setBatchItems(batchItems.filter((_, i) => i !== index));
    }
  };

  const handleBatchItemChange = (index, field, value) => {
    const newItems = [...batchItems];
    newItems[index] = { ...newItems[index], [field]: value };
    setBatchItems(newItems);
  };

  const handleAnalyzeAnother = () => {
    // Stop polling
    if (pollingCleanupRef.current) {
      pollingCleanupRef.current();
      pollingCleanupRef.current = null;
    }
    
    setResult(null);
    setBatchResults(null);
    setError(null);
    setAnalyzing(false);
    setAsin('');
    setBuyCost('');
    setMoq(1);
    setSupplierId('');
    setBatchItems([{ asin: '', buy_cost: '', moq: 1 }]);
  };

  const handleAddToProducts = async () => {
    if (!result) {
      showToast('No analysis result to add.', 'warning');
      return;
    }
    
    setAddingToProducts(true);
    
    try {
      // Product is already created during analysis, just navigate to products page
      // Optionally update product source stage if needed
      if (result.product_id) {
        try {
          // Try to update product source stage to make it visible
          // This is optional - if it fails, we still navigate
          await api.patch(`/products/deal/${result.product_id}`, {
            stage: 'new',
            ...(supplierId && { supplier_id: supplierId }),
          }).catch(() => {
            // Ignore errors - product is already created
          });
        } catch (updateErr) {
          // Ignore update errors - product exists and can be viewed
          console.log('Product already exists, navigating to view it');
        }
      }
      
      showToast('Product is in your list! Redirecting...', 'success');
      
      // Navigate to products page - filter by ASIN if available
      setTimeout(() => {
        if (result.asin) {
          navigate(`/products?asin=${result.asin}`);
        } else {
          navigate('/products');
        }
      }, 1000);
      
    } catch (err) {
      console.error('Failed to navigate to product:', err);
      // Still navigate even if there's an error
      showToast('Redirecting to products page...', 'info');
      setTimeout(() => {
        if (result.asin) {
          navigate(`/products?asin=${result.asin}`);
        } else {
          navigate('/products');
        }
      }, 500);
    } finally {
      setAddingToProducts(false);
    }
  };

  const handleViewRecent = (analysis) => {
    setResult(analysis);
  };

  const handleViewDetails = () => {
    if (result?.asin) {
      navigate(`/products?asin=${result.asin}`);
    } else if (result?.product_id) {
      navigate(`/products?product_id=${result.product_id}`);
    } else {
      navigate('/products');
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(amount || 0);
  };

  const formatROI = (roi) => {
    if (!roi && roi !== 0) return 'N/A';
    return `${roi >= 0 ? '+' : ''}${roi.toFixed(1)}%`;
  };

  return (
    <Box>
      <Typography variant="h4" fontWeight={700} mb={1}>
        Analyze Products
      </Typography>
      <Typography variant="body1" color="text.secondary" mb={4}>
        Enter an ASIN to get instant profitability analysis
      </Typography>

      <Card sx={{ mb: 4 }}>
        <CardContent>
          <Box display="flex" flexDirection="column" gap={3}>
            <RadioGroup value={mode} onChange={(e) => {
              setMode(e.target.value);
              setResult(null);
              setBatchResults(null);
              setError(null);
            }} row>
              <FormControlLabel value="single" control={<Radio />} label="Single ASIN" />
              <FormControlLabel value="bulk" control={<Radio />} label="Bulk Analysis" />
            </RadioGroup>

            {mode === 'single' ? (
              <>
                <Box display="flex" gap={2}>
                  <TextField
                    fullWidth
                    label="ASIN"
                    placeholder="B08XYZ1234"
                    value={asin}
                    onChange={(e) => setAsin(e.target.value.toUpperCase())}
                    sx={{ fontFamily: 'monospace' }}
                    disabled={!!result}
                  />
                  <Button
                    variant="contained"
                    startIcon={analyzing ? <CircularProgress size={16} color="inherit" /> : <Zap size={16} />}
                    onClick={handleAnalyze}
                    disabled={loading || analyzing || !asin || !buyCost || !!result}
                    sx={{
                      backgroundColor: habexa.purple.main,
                      '&:hover': { backgroundColor: habexa.purple.dark },
                      minWidth: 150,
                    }}
                  >
                    {analyzing ? 'Analyzing...' : loading ? 'Starting...' : 'Analyze'}
                  </Button>
                </Box>

                <Box display="flex" gap={2}>
                  <TextField
                    label="Your Cost"
                    type="number"
                    value={buyCost}
                    onChange={(e) => setBuyCost(e.target.value)}
                    InputProps={{ startAdornment: '$' }}
                    sx={{ flex: 1 }}
                    disabled={!!result}
                  />
                  <TextField
                    label="MOQ"
                    type="number"
                    value={moq}
                    onChange={(e) => setMoq(parseInt(e.target.value) || 1)}
                    sx={{ flex: 1 }}
                    disabled={!!result}
                  />
                  <FormControl sx={{ flex: 1 }}>
                    <InputLabel>Supplier</InputLabel>
                    <Select
                      value={supplierId}
                      label="Supplier"
                      onChange={(e) => setSupplierId(e.target.value)}
                      disabled={!!result}
                    >
                      <MenuItem value="">None</MenuItem>
                      {suppliers.map((s) => (
                        <MenuItem key={s.id} value={s.id}>
                          {s.name}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Box>
              </>
            ) : (
              <>
                <Box display="flex" flexDirection="column" gap={2}>
                  {batchItems.map((item, index) => (
                    <Box key={index} display="flex" gap={2} alignItems="center">
                      <TextField
                        label="ASIN"
                        placeholder="B08XYZ1234"
                        value={item.asin}
                        onChange={(e) => handleBatchItemChange(index, 'asin', e.target.value.toUpperCase())}
                        sx={{ fontFamily: 'monospace', flex: 2 }}
                        disabled={!!batchResults}
                      />
                      <TextField
                        label="Cost"
                        type="number"
                        value={item.buy_cost}
                        onChange={(e) => handleBatchItemChange(index, 'buy_cost', e.target.value)}
                        InputProps={{ startAdornment: '$' }}
                        sx={{ flex: 1 }}
                        disabled={!!batchResults}
                      />
                      <TextField
                        label="MOQ"
                        type="number"
                        value={item.moq}
                        onChange={(e) => handleBatchItemChange(index, 'moq', e.target.value)}
                        sx={{ width: 100 }}
                        disabled={!!batchResults}
                      />
                      {batchItems.length > 1 && (
                        <Button
                          variant="outlined"
                          color="error"
                          onClick={() => handleRemoveBatchRow(index)}
                          disabled={!!batchResults}
                          sx={{ minWidth: 40 }}
                        >
                          <Trash2 size={16} />
                        </Button>
                      )}
                    </Box>
                  ))}
                  
                  <Box display="flex" gap={2} alignItems="center">
                    <Button
                      variant="outlined"
                      startIcon={<Plus size={16} />}
                      onClick={handleAddBatchRow}
                      disabled={!!batchResults}
                    >
                      Add Another ASIN
                    </Button>
                    
                    <FormControl sx={{ flex: 1, maxWidth: 200 }}>
                      <InputLabel>Supplier (All)</InputLabel>
                      <Select
                        value={supplierId}
                        label="Supplier (All)"
                        onChange={(e) => setSupplierId(e.target.value)}
                        disabled={!!batchResults}
                      >
                        <MenuItem value="">None</MenuItem>
                        {suppliers.map((s) => (
                          <MenuItem key={s.id} value={s.id}>
                            {s.name}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  </Box>
                  
                  <Button
                    variant="contained"
                    startIcon={analyzing ? <CircularProgress size={16} color="inherit" /> : <Zap size={16} />}
                    onClick={handleBatchAnalyze}
                    disabled={loading || analyzing || !!batchResults || batchItems.filter(item => item.asin && item.buy_cost).length === 0}
                    sx={{
                      backgroundColor: habexa.purple.main,
                      '&:hover': { backgroundColor: habexa.purple.dark },
                      mt: 1,
                    }}
                  >
                    {analyzing ? 'Analyzing...' : `Analyze ${batchItems.filter(item => item.asin && item.buy_cost).length} Product${batchItems.filter(item => item.asin && item.buy_cost).length !== 1 ? 's' : ''}`}
                  </Button>
                  
                  <Typography variant="caption" color="text.secondary" sx={{ mt: -1 }}>
                    {batchItems.filter(item => item.asin && item.buy_cost).length <= 10 
                      ? '⚡ Results will appear instantly (≤10 products)'
                      : '⏳ Analysis will run in background (track progress on Jobs page)'
                    }
                  </Typography>
                </Box>
              </>
            )}
          </Box>
        </CardContent>
      </Card>

      {/* Error Display */}
      {error && (
        <Card sx={{ mb: 4, borderColor: 'error.main', border: 1 }}>
          <CardContent>
            <Alert severity="error" sx={{ mb: 2 }}>
              <Typography variant="body1" fontWeight={600}>
                Analysis Failed
              </Typography>
              <Typography variant="body2" mt={1}>
                {error}
              </Typography>
            </Alert>
            <Button
              variant="outlined"
              startIcon={<RefreshCw size={16} />}
              onClick={handleAnalyzeAnother}
            >
              Try Again
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Result Display */}
      {result && (
        <Card sx={{ mb: 4, borderColor: result.roi >= 30 ? 'success.main' : result.roi > 0 ? 'warning.main' : 'error.main', border: 2 }}>
          <CardContent>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
              <Typography variant="h5" fontWeight={700}>
                Analysis Results
              </Typography>
              <Chip
                label={result.roi >= 30 ? 'Highly Profitable' : result.roi > 0 ? 'Profitable' : 'Unprofitable'}
                color={result.roi >= 30 ? 'success' : result.roi > 0 ? 'warning' : 'error'}
                sx={{ fontWeight: 600 }}
              />
            </Box>

            <Divider sx={{ my: 2 }} />

            <Box display="flex" flexDirection="column" gap={2}>
              {/* Product Info */}
              <Box>
                <Typography variant="body2" color="text.secondary" mb={0.5}>
                  Product Title
                </Typography>
                <Typography variant="body1" fontWeight={600}>
                  {result.title || 'N/A'}
                </Typography>
              </Box>

              <Box>
                <Typography variant="body2" color="text.secondary" mb={0.5}>
                  ASIN
                </Typography>
                <Typography variant="body1" fontFamily="monospace" fontWeight={600}>
                  {result.asin || 'N/A'}
                </Typography>
              </Box>

              {/* Key Metrics */}
              <Box display="grid" gridTemplateColumns="repeat(2, 1fr)" gap={2} mt={2}>
                <Box
                  sx={{
                    p: 2,
                    borderRadius: 2,
                    bgcolor: 'background.paper',
                    border: '1px solid',
                    borderColor: 'divider',
                  }}
                >
                  <Box display="flex" alignItems="center" gap={1} mb={1}>
                    <TrendingUp size={20} color={result.roi >= 30 ? habexa.success.main : result.roi > 0 ? habexa.warning.main : habexa.error.main} />
                    <Typography variant="body2" color="text.secondary">
                      ROI
                    </Typography>
                  </Box>
                  <Typography
                    variant="h4"
                    fontWeight={700}
                    color={result.roi >= 30 ? 'success.main' : result.roi > 0 ? 'warning.main' : 'error.main'}
                  >
                    {formatROI(result.roi)}
                  </Typography>
                </Box>

                <Box
                  sx={{
                    p: 2,
                    borderRadius: 2,
                    bgcolor: 'background.paper',
                    border: '1px solid',
                    borderColor: 'divider',
                  }}
                >
                  <Box display="flex" alignItems="center" gap={1} mb={1}>
                    <DollarSign size={20} color={result.net_profit > 0 ? habexa.success.main : habexa.error.main} />
                    <Typography variant="body2" color="text.secondary">
                      Net Profit
                    </Typography>
                  </Box>
                  <Typography
                    variant="h4"
                    fontWeight={700}
                    color={result.net_profit > 0 ? 'success.main' : 'error.main'}
                  >
                    {formatCurrency(result.net_profit)}
                  </Typography>
                </Box>
              </Box>

              {/* Additional Info */}
              {result.deal_score && (
                <Box>
                  <Typography variant="body2" color="text.secondary" mb={0.5}>
                    Deal Score
                  </Typography>
                  <Typography variant="body1" fontWeight={600}>
                    {result.deal_score}
                  </Typography>
                </Box>
              )}

              {result.gating_status && (
                <Box>
                  <Typography variant="body2" color="text.secondary" mb={0.5}>
                    Gating Status
                  </Typography>
                  <Chip
                    label={result.gating_status}
                    size="small"
                    color={result.gating_status === 'ungated' ? 'success' : 'warning'}
                  />
                </Box>
              )}

              {/* Action Buttons */}
              <Box display="flex" gap={2} mt={3}>
                <Button
                  variant="contained"
                  startIcon={<Plus size={16} />}
                  onClick={handleAddToProducts}
                  disabled={addingToProducts || !result?.product_id}
                  sx={{
                    backgroundColor: habexa.purple.main,
                    '&:hover': { backgroundColor: habexa.purple.dark },
                    flex: 1,
                  }}
                >
                  {addingToProducts ? 'Adding...' : 'Add to Products'}
                </Button>
                <Button
                  variant="outlined"
                  startIcon={<ExternalLink size={16} />}
                  onClick={handleViewDetails}
                  sx={{ flex: 1 }}
                >
                  View Full Details
                </Button>
                <Button
                  variant="outlined"
                  startIcon={<RefreshCw size={16} />}
                  onClick={handleAnalyzeAnother}
                  sx={{ flex: 1 }}
                >
                  Analyze Another
                </Button>
              </Box>
            </Box>
          </CardContent>
        </Card>
      )}

      {/* Batch Results Display */}
      {batchResults && batchResults.mode === 'sync' && (
        <Card sx={{ mb: 4, borderColor: 'success.main', border: 2 }}>
          <CardContent>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
              <Typography variant="h5" fontWeight={700}>
                Batch Analysis Results
              </Typography>
              <Chip
                label={`${batchResults.results.filter(r => r.status === 'success').length}/${batchResults.total} Successful`}
                color="success"
                sx={{ fontWeight: 600 }}
              />
            </Box>

            <Divider sx={{ my: 2 }} />

            <Box display="flex" flexDirection="column" gap={2}>
              {batchResults.results.map((result, index) => (
                <Card
                  key={index}
                  sx={{
                    p: 2,
                    border: '1px solid',
                    borderColor: result.status === 'success' ? 'success.main' : 'error.main',
                    bgcolor: result.status === 'success' ? 'success.50' : 'error.50',
                  }}
                >
                  <Box display="flex" justifyContent="space-between" alignItems="start">
                    <Box sx={{ flex: 1 }}>
                      <Typography variant="subtitle1" fontWeight={600}>
                        {result.asin}
                      </Typography>
                      {result.status === 'success' && result.result && (
                        <Box mt={1}>
                          <Typography variant="body2" color="text.secondary">
                            {result.result.title || 'Unknown'}
                          </Typography>
                          <Box display="flex" gap={2} mt={1}>
                            <Typography variant="body2">
                              <strong>Profit:</strong> {formatCurrency(result.result.net_profit || 0)}
                            </Typography>
                            <Typography variant="body2">
                              <strong>ROI:</strong> {formatROI(result.result.roi || 0)}
                            </Typography>
                          </Box>
                        </Box>
                      )}
                      {result.status === 'failed' && (
                        <Typography variant="body2" color="error.main" mt={1}>
                          {result.error || 'Analysis failed'}
                        </Typography>
                      )}
                    </Box>
                    <Chip
                      label={result.status === 'success' ? 'Success' : 'Failed'}
                      color={result.status === 'success' ? 'success' : 'error'}
                      size="small"
                    />
                  </Box>
                </Card>
              ))}
            </Box>

            <Box display="flex" gap={2} mt={3}>
              <Button
                variant="contained"
                onClick={() => navigate('/products')}
                sx={{
                  backgroundColor: habexa.purple.main,
                  '&:hover': { backgroundColor: habexa.purple.dark },
                }}
              >
                View All Products
              </Button>
              <Button
                variant="outlined"
                onClick={handleAnalyzeAnother}
              >
                Analyze More
              </Button>
            </Box>
          </CardContent>
        </Card>
      )}

      {/* Recent Analyses Section - Only show when no result */}
      {!result && !batchResults && !error && !analyzing && (
        <>
          <Typography variant="h6" fontWeight={600} mb={2}>
            📋 Recent Analyses
          </Typography>
          {recentAnalyses.length === 0 ? (
            <Typography color="text.secondary">No recent analyses</Typography>
          ) : (
            <Grid container spacing={2}>
              {recentAnalyses.slice(0, 6).map((analysis, index) => (
                <Grid item xs={12} md={6} key={index}>
                  <Card sx={{ cursor: 'pointer', '&:hover': { boxShadow: 3 } }} onClick={() => handleViewRecent(analysis)}>
                    <CardContent>
                      <Box display="flex" gap={2} alignItems="center">
                        {analysis.image_url && (
                          <img 
                            src={analysis.image_url} 
                            alt={analysis.title}
                            style={{ width: 60, height: 60, objectFit: 'contain', borderRadius: 4 }}
                          />
                        )}
                        <Box sx={{ flex: 1, minWidth: 0 }}>
                          <Typography variant="subtitle2" noWrap fontWeight={600}>
                            {analysis.title || 'Unknown Product'}
                          </Typography>
                          <Typography variant="caption" color="text.secondary" fontFamily="monospace">
                            {analysis.asin}
                          </Typography>
                          <Box display="flex" gap={1} mt={1} flexWrap="wrap">
                            {analysis.net_profit !== undefined && (
                              <Chip 
                                label={`Profit: ${formatCurrency(analysis.net_profit)}`} 
                                size="small" 
                                color={analysis.net_profit > 0 ? 'success' : 'error'}
                              />
                            )}
                            {analysis.roi !== undefined && (
                              <Chip 
                                label={`ROI: ${formatROI(analysis.roi)}`} 
                                size="small"
                                color={analysis.roi >= 30 ? 'success' : analysis.roi > 0 ? 'warning' : 'error'}
                              />
                            )}
                          </Box>
                        </Box>
                        <Button size="small" variant="outlined" onClick={(e) => { e.stopPropagation(); handleViewRecent(analysis); }}>
                          View
                        </Button>
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          )}
        </>
      )}

      {/* Loading indicator when analyzing */}
      {analyzing && (
        <Card sx={{ mb: 4 }}>
          <CardContent>
            <Box display="flex" flexDirection="column" alignItems="center" gap={2} py={3}>
              <CircularProgress size={40} />
              <Typography variant="body1" color="text.secondary">
                Analyzing product... This may take a few seconds.
              </Typography>
            </Box>
          </CardContent>
        </Card>
      )}
    </Box>
  );
};

export default Analyze;
