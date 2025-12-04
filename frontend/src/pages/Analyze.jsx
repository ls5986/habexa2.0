import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Box, Typography, TextField, Button, Card, CardContent, 
  RadioGroup, FormControlLabel, Radio, Select, MenuItem, 
  FormControl, InputLabel, Alert, Chip, Divider 
} from '@mui/material';
import { Zap, ExternalLink, TrendingUp, DollarSign, RefreshCw } from 'lucide-react';
import { useAnalysis } from '../hooks/useAnalysis';
import { useSuppliers } from '../hooks/useSuppliers';
import { useToast } from '../context/ToastContext';
import { handleApiError } from '../utils/errorHandler';
import { habexa } from '../theme';

const Analyze = () => {
  const navigate = useNavigate();
  const [mode, setMode] = useState('single');
  const [asin, setAsin] = useState('');
  const [buyCost, setBuyCost] = useState('');
  const [moq, setMoq] = useState(1);
  const [supplierId, setSupplierId] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const { analyzeSingle, loading } = useAnalysis();
  const { suppliers } = useSuppliers();
  const { showToast } = useToast();

  const handleAnalyze = async () => {
    if (!asin || !buyCost) {
      showToast('Please enter ASIN and buy cost', 'error');
      return;
    }
    
    setResult(null);
    setError(null);
    
    try {
      const data = await analyzeSingle(asin, parseFloat(buyCost), moq, supplierId || null);
      
      // Handle job-based response (async analysis)
      if (data.job_id) {
        showToast('Analysis started! Check Products page for results.', 'info');
        // Could add polling here, but for now just notify user
        return;
      }
      
      // Handle direct result response
      if (data.asin || data.product_id) {
        setResult(data);
        showToast('Analysis complete!', 'success');
      } else {
        // If response structure is different, try to extract what we can
        setResult({
          asin: data.asin || asin,
          title: data.title || data.product_title || 'Product Analysis',
          roi: data.roi || data.analysis?.roi || 0,
          net_profit: data.net_profit || data.analysis?.net_profit || 0,
          deal_score: data.deal_score || data.analysis?.deal_score || null,
          gating_status: data.gating_status || 'unknown',
          meets_threshold: data.meets_threshold || false,
        });
        showToast('Analysis complete!', 'success');
      }
    } catch (err) {
      const errorMessage = handleApiError(err, showToast);
      setError(errorMessage);
    }
  };

  const handleAnalyzeAnother = () => {
    setResult(null);
    setError(null);
    setAsin('');
    setBuyCost('');
    setMoq(1);
    setSupplierId('');
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
            <RadioGroup value={mode} onChange={(e) => setMode(e.target.value)} row>
              <FormControlLabel value="single" control={<Radio />} label="Single ASIN" />
              <FormControlLabel value="bulk" control={<Radio />} label="Bulk Analysis" />
            </RadioGroup>

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
                startIcon={<Zap size={16} />}
                onClick={handleAnalyze}
                disabled={loading || !asin || !buyCost || !!result}
                sx={{
                  backgroundColor: habexa.purple.main,
                  '&:hover': { backgroundColor: habexa.purple.dark },
                  minWidth: 150,
                }}
              >
                {loading ? 'Analyzing...' : 'Analyze'}
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
                  startIcon={<ExternalLink size={16} />}
                  onClick={handleViewDetails}
                  sx={{
                    backgroundColor: habexa.purple.main,
                    '&:hover': { backgroundColor: habexa.purple.dark },
                    flex: 1,
                  }}
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

      {/* Recent Analyses Section - Only show when no result */}
      {!result && !error && (
        <>
          <Typography variant="h6" fontWeight={600} mb={2}>
            📋 Recent Analyses
          </Typography>
          <Typography color="text.secondary">No recent analyses</Typography>
        </>
      )}
    </Box>
  );
};

export default Analyze;
