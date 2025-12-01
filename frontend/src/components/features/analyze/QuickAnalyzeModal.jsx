import { Dialog, DialogTitle, DialogContent, DialogActions, TextField, Button, Box, Typography, CircularProgress, Card, CardContent, Chip, FormControl, InputLabel, Select, MenuItem, Alert } from '@mui/material';
import { X, Zap, TrendingUp } from 'lucide-react';
import { useState } from 'react';
import { useAnalysis } from '../../../hooks/useAnalysis';
import { useSuppliers } from '../../../hooks/useSuppliers';
import { useToast } from '../../../context/ToastContext';
import { useStripe } from '../../../context/StripeContext';
import { useFeatureGate } from '../../../hooks/useFeatureGate';
import { formatCurrency, formatROI } from '../../../utils/formatters';
import UsageDisplay from '../../common/UsageDisplay';
import { habexa } from '../../../theme';

const QuickAnalyzeModal = ({ open, onClose, onViewDeal }) => {
  const [asin, setAsin] = useState('');
  const [buyCost, setBuyCost] = useState('');
  const [moq, setMoq] = useState(1);
  const [supplierId, setSupplierId] = useState('');
  const [result, setResult] = useState(null);
  const { analyzeSingle, loading } = useAnalysis();
  const { suppliers } = useSuppliers();
  const { showToast } = useToast();
  const { subscription } = useStripe();
  const { isLimitReached, getLimit, promptUpgrade } = useFeatureGate();
  
  const analysesUsed = subscription?.analyses_used || 0;
  const analysesLimit = getLimit('analyses_per_month');
  const limitReached = isLimitReached('analyses_per_month', analysesUsed);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!asin || !buyCost) {
      showToast('Please enter ASIN and buy cost', 'error');
      return;
    }

    if (limitReached) {
      promptUpgrade('analyses_per_month');
      return;
    }

    try {
      const analysisResult = await analyzeSingle(asin, parseFloat(buyCost), moq, supplierId || null);
      setResult(analysisResult);
      showToast('Analysis complete!', 'success');
    } catch (error) {
      showToast(error.message || 'Failed to analyze ASIN', 'error');
    }
  };

  const handleAnalyzeAnother = () => {
    setAsin('');
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
    setAsin('');
    setBuyCost('');
    setMoq(1);
    setSupplierId('');
    setResult(null);
    onClose();
  };

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="sm"
      fullWidth
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
                <UsageDisplay
                  label="Analyses This Month"
                  used={analysesUsed}
                  limit={analysesLimit}
                />
              </Box>

              {limitReached && (
                <Alert severity="error">
                  You've reached your analysis limit. Upgrade for more!
                </Alert>
              )}
              <TextField
                label="ASIN"
                placeholder="B08XYZ1234"
                value={asin}
                onChange={(e) => setAsin(e.target.value.toUpperCase())}
                required
                fullWidth
                sx={{ fontFamily: 'monospace' }}
                disabled={loading}
              />

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
                />
                <TextField
                  label="MOQ"
                  type="number"
                  value={moq}
                  onChange={(e) => setMoq(parseInt(e.target.value) || 1)}
                  fullWidth
                  disabled={loading}
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
                disabled={loading || !asin || !buyCost || limitReached}
                startIcon={loading ? <CircularProgress size={16} /> : <Zap size={16} />}
                sx={{
                  backgroundColor: habexa.purple.main,
                  '&:hover': { backgroundColor: habexa.purple.dark },
                  py: 1.5,
                }}
              >
                {loading ? 'Analyzing...' : limitReached ? 'Limit Reached' : 'Analyze ASIN'}
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

