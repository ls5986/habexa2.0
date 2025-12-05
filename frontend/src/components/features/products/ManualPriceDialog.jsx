import React, { useState, useMemo } from 'react';
import {
  Dialog, DialogTitle, DialogContent, DialogActions,
  Button, TextField, InputAdornment, Typography, Box,
  Alert, AlertTitle, Chip, CircularProgress
} from '@mui/material';
import api from '../../../services/api';
import { useToast } from '../../../context/ToastContext';

const ManualPriceDialog = ({ open, onClose, deal, analysis, onSave }) => {
  const [sellPrice, setSellPrice] = useState('');
  const [saving, setSaving] = useState(false);
  const { showToast } = useToast();

  // Calculate estimated profit as user types
  const estimated = useMemo(() => {
    if (!sellPrice || !deal) return null;

    const price = parseFloat(sellPrice);
    if (isNaN(price) || price <= 0) return null;

    const buyC = deal.buy_cost || deal.product_sources?.[0]?.buy_cost || 0;
    const fees = price * 0.15 + 4.50; // Rough estimate: 15% referral + $4.50 FBA
    const inbound = 0.35 * 0.5; // Estimate 0.5 lb at $0.35/lb
    const prep = 0.10;
    const landed = buyC + inbound + prep;
    const profit = price - fees - landed;
    const roi = landed > 0 ? (profit / landed) * 100 : 0;

    return { fees, profit, roi, landed };
  }, [sellPrice, deal]);

  const handleSave = async () => {
    if (!sellPrice || !analysis?.id) return;

    setSaving(true);
    try {
      await api.patch(`/analysis/${analysis.id}/manual-price`, {
        sell_price: parseFloat(sellPrice)
      });
      showToast('Manual price saved successfully', 'success');
      onSave();
      onClose();
      setSellPrice('');
    } catch (err) {
      showToast(err.response?.data?.detail || 'Failed to save manual price', 'error');
    } finally {
      setSaving(false);
    }
  };

  const formatPricingReason = (reason) => {
    const reasons = {
      'no_active_offers': 'No active sellers on Amazon',
      'no_response': 'No response from Amazon API',
      'gated': 'Product is gated/restricted',
      'invalid_asin': 'ASIN may be invalid',
      'unknown': 'Unknown reason',
    };
    return reasons[reason] || reason || 'Unknown';
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Enter Manual Sell Price</DialogTitle>
      <DialogContent>
        <Alert severity="warning" sx={{ mb: 2 }}>
          No pricing data available from Amazon. You can enter a manual sell price based on your research.
        </Alert>

        <Typography variant="subtitle2" gutterBottom>
          {deal?.title || 'Unknown Product'}
        </Typography>
        <Typography variant="body2" color="text.secondary" gutterBottom>
          ASIN: {deal?.asin} | Buy Cost: ${deal?.buy_cost || deal?.product_sources?.[0]?.buy_cost || '0.00'}
        </Typography>

        {analysis?.pricing_status_reason && (
          <Chip
            label={`Reason: ${formatPricingReason(analysis.pricing_status_reason)}`}
            size="small"
            color="warning"
            sx={{ mb: 2 }}
          />
        )}

        {/* Show Keepa data if available */}
        {analysis?.fba_lowest_365d && (
          <Alert severity="info" sx={{ mb: 2 }}>
            Keepa shows historical FBA low of ${analysis.fba_lowest_365d?.toFixed(2)}
            {analysis.amazon_was_seller && ' (Amazon was a seller)'}
          </Alert>
        )}

        <TextField
          label="Sell Price"
          type="number"
          step="0.01"
          value={sellPrice}
          onChange={(e) => setSellPrice(e.target.value)}
          fullWidth
          InputProps={{
            startAdornment: <InputAdornment position="start">$</InputAdornment>
          }}
          sx={{ mt: 2 }}
          autoFocus
        />

        {estimated && (
          <Box sx={{ mt: 2, p: 2, bgcolor: 'grey.100', borderRadius: 1 }}>
            <Typography variant="subtitle2" gutterBottom>Estimated (fees are approximate):</Typography>
            <Typography variant="body2">Fees: ~${estimated.fees.toFixed(2)}</Typography>
            <Typography variant="body2">Landed Cost: ${estimated.landed.toFixed(2)}</Typography>
            <Typography variant="body2">Profit: ${estimated.profit.toFixed(2)}</Typography>
            <Typography
              variant="body1"
              fontWeight="bold"
              color={estimated.roi >= 30 ? 'success.main' : estimated.roi > 0 ? 'warning.main' : 'error.main'}
              sx={{ mt: 1 }}
            >
              ROI: {estimated.roi.toFixed(1)}%
            </Typography>
          </Box>
        )}

        <Typography variant="caption" color="text.secondary" sx={{ mt: 2, display: 'block' }}>
          Note: Fees are estimated at ~15% referral + $4.50 FBA.
          Re-analyze when product has active offers for accurate fees.
        </Typography>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button
          onClick={handleSave}
          variant="contained"
          disabled={!sellPrice || saving || isNaN(parseFloat(sellPrice)) || parseFloat(sellPrice) <= 0}
        >
          {saving ? <CircularProgress size={20} /> : 'Save Manual Price'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default ManualPriceDialog;

