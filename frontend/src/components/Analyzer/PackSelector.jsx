import React, { useState, useEffect } from 'react';
import {
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
  Box,
  Typography,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper
} from '@mui/material';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export default function PackSelector({ productId, currentPackSize, onPackSizeChange }) {
  const [variants, setVariants] = useState([]);
  const [selectedPackSize, setSelectedPackSize] = useState(currentPackSize || 1);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (productId) {
      fetchPackVariants();
    }
  }, [productId]);

  const fetchPackVariants = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      const response = await axios.get(
        `${API_URL}/api/v1/pack-variants/${productId}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setVariants(response.data.variants || []);
    } catch (err) {
      console.error('Error fetching pack variants:', err);
    } finally {
      setLoading(false);
    }
  };

  const handlePackSizeChange = (newPackSize) => {
    setSelectedPackSize(newPackSize);
    if (onPackSizeChange) {
      onPackSizeChange(newPackSize);
    }
  };

  const recommendedVariant = variants.find(v => v.is_recommended);
  const selectedVariant = variants.find(v => v.pack_size === selectedPackSize) || variants[0];

  const formatCurrency = (value) => {
    if (!value) return '$0.00';
    return `$${parseFloat(value).toFixed(2)}`;
  };

  if (loading) {
    return <Typography variant="body2">Loading pack variants...</Typography>;
  }

  if (variants.length === 0) {
    return (
      <FormControl fullWidth size="small">
        <InputLabel>Pack Size</InputLabel>
        <Select value={selectedPackSize} label="Pack Size" disabled>
          <MenuItem value={selectedPackSize}>{selectedPackSize}-pack</MenuItem>
        </Select>
      </FormControl>
    );
  }

  return (
    <Box>
      <FormControl fullWidth size="small">
        <InputLabel>Pack Size</InputLabel>
        <Select
          value={selectedPackSize}
          onChange={(e) => handlePackSizeChange(e.target.value)}
          label="Pack Size"
        >
          {variants.map((variant) => (
            <MenuItem key={variant.pack_size} value={variant.pack_size}>
              <Box display="flex" alignItems="center" justifyContent="space-between" width="100%">
                <Typography>
                  {variant.pack_size}-pack
                  {variant.is_recommended && (
                    <Chip
                      label="⭐ Best"
                      size="small"
                      color="success"
                      sx={{ ml: 1, height: 18, fontSize: '0.7rem' }}
                    />
                  )}
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ ml: 2 }}>
                  PPU: {formatCurrency(variant.profit_per_unit)}
                </Typography>
              </Box>
            </MenuItem>
          ))}
        </Select>
      </FormControl>

      {selectedVariant && (
        <Box mt={1}>
          <Typography variant="caption" color="text.secondary">
            PPU: {formatCurrency(selectedVariant.profit_per_unit)} | 
            ROI: {selectedVariant.roi?.toFixed(1)}%
          </Typography>
        </Box>
      )}

      <Button
        size="small"
        onClick={() => setDialogOpen(true)}
        sx={{ mt: 1 }}
      >
        View Pack Economics
      </Button>

      <PackEconomicsDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        variants={variants}
        selectedPackSize={selectedPackSize}
        onSelectPackSize={handlePackSizeChange}
      />
    </Box>
  );
}

function PackEconomicsDialog({ open, onClose, variants, selectedPackSize, onSelectPackSize }) {
  const formatCurrency = (value) => {
    if (!value) return '$0.00';
    return `$${parseFloat(value).toFixed(2)}`;
  };

  const formatPercent = (value) => {
    if (!value) return '0%';
    return `${parseFloat(value).toFixed(1)}%`;
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        Pack Economics Comparison
      </DialogTitle>
      <DialogContent>
        <TableContainer component={Paper} variant="outlined">
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Pack Size</TableCell>
                <TableCell align="right">Amazon Price</TableCell>
                <TableCell align="right">Cost</TableCell>
                <TableCell align="right">Fees</TableCell>
                <TableCell align="right">Profit/Pack</TableCell>
                <TableCell align="right">
                  <strong>PPU</strong>
                </TableCell>
                <TableCell align="right">ROI</TableCell>
                <TableCell align="right">Margin</TableCell>
                <TableCell></TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {variants
                .sort((a, b) => b.profit_per_unit - a.profit_per_unit)
                .map((variant) => (
                  <TableRow
                    key={variant.pack_size}
                    sx={{
                      backgroundColor: variant.is_recommended ? 'success.light' : 'transparent',
                      '&:hover': { backgroundColor: 'action.hover' }
                    }}
                  >
                    <TableCell>
                      <Box display="flex" alignItems="center" gap={1}>
                        <Typography fontWeight="bold">
                          {variant.pack_size}-pack
                        </Typography>
                        {variant.is_recommended && (
                          <Chip label="⭐ Recommended" size="small" color="success" />
                        )}
                      </Box>
                    </TableCell>
                    <TableCell align="right">
                      {formatCurrency(variant.buy_box_price_365d_avg || variant.amazon_price_current)}
                    </TableCell>
                    <TableCell align="right">
                      {/* Cost would come from product_source */}
                      —
                    </TableCell>
                    <TableCell align="right">
                      {formatCurrency((variant.fba_fees || 0) + (variant.referral_fee || 0))}
                    </TableCell>
                    <TableCell align="right">
                      {formatCurrency(variant.total_profit)}
                    </TableCell>
                    <TableCell align="right">
                      <Typography fontWeight="bold" color="success.main">
                        {formatCurrency(variant.profit_per_unit)}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      {formatPercent(variant.roi)}
                    </TableCell>
                    <TableCell align="right">
                      {formatPercent(variant.margin)}
                    </TableCell>
                    <TableCell>
                      {variant.pack_size === selectedPackSize ? (
                        <Chip label="Selected" size="small" color="primary" />
                      ) : (
                        <Button
                          size="small"
                          onClick={() => {
                            onSelectPackSize(variant.pack_size);
                            onClose();
                          }}
                        >
                          Use This
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
            </TableBody>
          </Table>
        </TableContainer>

        {variants.find(v => v.is_recommended) && (
          <Box mt={2}>
            <Typography variant="body2" color="text.secondary">
              💡 Recommended pack size selected based on highest Profit Per Unit (PPU)
            </Typography>
          </Box>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
}

