import React, { useState, useMemo, useEffect } from 'react';
import {
  Box, Typography, Card, CardContent, TextField, Slider,
  Divider, Grid, InputAdornment, Tooltip, IconButton
} from '@mui/material';
import { Calculator, Info, TrendingUp, Package, DollarSign, Percent } from 'lucide-react';
import { habexa } from '../../../theme';

export default function ProfitCalculator({ 
  initialBuyCost = 0,
  sellPrice = 0,
  referralFee = 0,
  fbaFee = 0,
  initialQuantity = 1
}) {
  // Editable state - doesn't save to DB
  const [buyCost, setBuyCost] = useState(initialBuyCost);
  const [quantity, setQuantity] = useState(initialQuantity);
  const [customSellPrice, setCustomSellPrice] = useState(sellPrice);
  const [prepCost, setPrepCost] = useState(0);
  const [shippingCost, setShippingCost] = useState(0);
  const [miscCost, setMiscCost] = useState(0);

  // Update quantity when initialQuantity prop changes
  useEffect(() => {
    if (initialQuantity > 0) {
      setQuantity(initialQuantity);
    }
  }, [initialQuantity]);

  // Update buy cost and sell price when props change
  useEffect(() => {
    if (initialBuyCost > 0) {
      setBuyCost(initialBuyCost);
    }
  }, [initialBuyCost]);

  useEffect(() => {
    if (sellPrice > 0) {
      setCustomSellPrice(sellPrice);
    }
  }, [sellPrice]);

  // Calculations
  const calculations = useMemo(() => {
    const totalCostPerUnit = buyCost + prepCost + shippingCost + miscCost;
    const totalFees = referralFee + fbaFee;
    const profitPerUnit = customSellPrice - totalCostPerUnit - totalFees;
    const roi = totalCostPerUnit > 0 ? (profitPerUnit / totalCostPerUnit) * 100 : 0;
    const margin = customSellPrice > 0 ? (profitPerUnit / customSellPrice) * 100 : 0;
    
    const totalInvestment = totalCostPerUnit * quantity;
    const totalRevenue = customSellPrice * quantity;
    const totalProfit = profitPerUnit * quantity;
    const totalFeesCost = totalFees * quantity;
    
    const breakEvenPrice = totalCostPerUnit + totalFees;
    const breakEvenQuantity = profitPerUnit > 0 ? Math.ceil(totalInvestment / profitPerUnit) : 0;
    
    return {
      totalCostPerUnit: totalCostPerUnit.toFixed(2),
      profitPerUnit: profitPerUnit.toFixed(2),
      roi: roi.toFixed(1),
      margin: margin.toFixed(1),
      totalInvestment: totalInvestment.toFixed(2),
      totalRevenue: totalRevenue.toFixed(2),
      totalProfit: totalProfit.toFixed(2),
      totalFeesCost: totalFeesCost.toFixed(2),
      breakEvenPrice: breakEvenPrice.toFixed(2),
      breakEvenQuantity: Math.max(0, breakEvenQuantity),
      isProfitable: profitPerUnit > 0,
    };
  }, [buyCost, quantity, customSellPrice, prepCost, shippingCost, miscCost, referralFee, fbaFee]);

  const StatBox = ({ label, value, prefix = '', suffix = '', color, tooltip }) => (
    <Box sx={{ 
      textAlign: 'center', 
      p: 2, 
      bgcolor: '#ffffff',
      border: '2px solid #7c3aed',
      borderRadius: 1
    }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 0.5 }}>
        <Typography variant="caption" sx={{ color: '#666666', fontSize: '0.75rem' }}>{label}</Typography>
        {tooltip && (
          <Tooltip title={tooltip}>
            <Info size={12} color="#666666" />
          </Tooltip>
        )}
      </Box>
      <Typography variant="h5" fontWeight="700" color={color || '#1a1a2e'} sx={{ fontSize: '1.25rem' }}>
        {prefix}{value}{suffix}
      </Typography>
    </Box>
  );

  return (
    <Card sx={{ mt: 3, bgcolor: '#ffffff' }}>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
          <Calculator size={20} />
          <Typography variant="h6" fontWeight="600">Profit Calculator</Typography>
          <Typography variant="caption" color="text.secondary" sx={{ ml: 'auto' }}>
            (Changes don't save)
          </Typography>
        </Box>

        <Grid container spacing={3}>
          {/* Left: Inputs */}
          <Grid item xs={12} md={5}>
            <Typography variant="subtitle2" color="text.secondary" gutterBottom>
              COSTS PER UNIT
            </Typography>
            
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mb: 3 }}>
              <TextField
                label="Buy Cost"
                type="number"
                size="small"
                value={buyCost}
                onChange={(e) => setBuyCost(parseFloat(e.target.value) || 0)}
                InputProps={{
                  startAdornment: <InputAdornment position="start">$</InputAdornment>
                }}
                sx={{
                  '& .MuiOutlinedInput-root': {
                    bgcolor: '#ffffff',
                    '& fieldset': { borderColor: '#e0e0e0' },
                    '&:hover fieldset': { borderColor: '#7c3aed' },
                    '&.Mui-focused fieldset': { borderColor: '#7c3aed' },
                  },
                  '& .MuiInputBase-input': { 
                    color: '#1a1a2e',
                  },
                  '& .MuiInputLabel-root': { 
                    color: '#666666',
                  },
                }}
              />
              <TextField
                label="Prep Cost"
                type="number"
                size="small"
                value={prepCost}
                onChange={(e) => setPrepCost(parseFloat(e.target.value) || 0)}
                InputProps={{
                  startAdornment: <InputAdornment position="start">$</InputAdornment>
                }}
                sx={{
                  '& .MuiOutlinedInput-root': {
                    bgcolor: '#ffffff',
                    '& fieldset': { borderColor: '#e0e0e0' },
                    '&:hover fieldset': { borderColor: '#7c3aed' },
                    '&.Mui-focused fieldset': { borderColor: '#7c3aed' },
                  },
                  '& .MuiInputBase-input': { 
                    color: '#1a1a2e',
                  },
                  '& .MuiInputLabel-root': { 
                    color: '#666666',
                  },
                }}
              />
              <TextField
                label="Shipping/Unit"
                type="number"
                size="small"
                value={shippingCost}
                onChange={(e) => setShippingCost(parseFloat(e.target.value) || 0)}
                InputProps={{
                  startAdornment: <InputAdornment position="start">$</InputAdornment>
                }}
                sx={{
                  '& .MuiOutlinedInput-root': {
                    bgcolor: '#ffffff',
                    '& fieldset': { borderColor: '#e0e0e0' },
                    '&:hover fieldset': { borderColor: '#7c3aed' },
                    '&.Mui-focused fieldset': { borderColor: '#7c3aed' },
                  },
                  '& .MuiInputBase-input': { 
                    color: '#1a1a2e',
                  },
                  '& .MuiInputLabel-root': { 
                    color: '#666666',
                  },
                }}
              />
              <TextField
                label="Misc Cost"
                type="number"
                size="small"
                value={miscCost}
                onChange={(e) => setMiscCost(parseFloat(e.target.value) || 0)}
                InputProps={{
                  startAdornment: <InputAdornment position="start">$</InputAdornment>
                }}
                sx={{
                  '& .MuiOutlinedInput-root': {
                    bgcolor: '#ffffff',
                    '& fieldset': { borderColor: '#e0e0e0' },
                    '&:hover fieldset': { borderColor: '#7c3aed' },
                    '&.Mui-focused fieldset': { borderColor: '#7c3aed' },
                  },
                  '& .MuiInputBase-input': { 
                    color: '#1a1a2e',
                  },
                  '& .MuiInputLabel-root': { 
                    color: '#666666',
                  },
                }}
              />
            </Box>

            <Typography variant="subtitle2" color="text.secondary" gutterBottom>
              SELL PRICE
            </Typography>
            <TextField
              label="Sell Price"
              type="number"
              size="small"
              fullWidth
              value={customSellPrice}
              onChange={(e) => setCustomSellPrice(parseFloat(e.target.value) || 0)}
              InputProps={{
                startAdornment: <InputAdornment position="start">$</InputAdornment>
              }}
              sx={{ mb: 3,
                '& .MuiOutlinedInput-root': {
                  bgcolor: '#ffffff',
                  '& fieldset': { borderColor: '#e0e0e0' },
                  '&:hover fieldset': { borderColor: '#7c3aed' },
                  '&.Mui-focused fieldset': { borderColor: '#7c3aed' },
                },
                '& .MuiInputBase-input': { 
                  color: '#1a1a2e',
                },
                '& .MuiInputLabel-root': { 
                  color: '#666666',
                },
              }}
            />

            <Typography variant="subtitle2" color="text.secondary" gutterBottom>
              QUANTITY (MOQ)
            </Typography>
            <Box sx={{ 
              px: 1, 
              py: 2, 
              bgcolor: '#ffffff', 
              border: '1px solid #e0e0e0', 
              borderRadius: 1 
            }}>
              <Slider
                value={quantity}
                onChange={(e, v) => setQuantity(v)}
                min={1}
                max={500}
                valueLabelDisplay="on"
                sx={{ mt: 2, color: '#7c3aed' }}
              />
            </Box>
            <TextField
              type="number"
              size="small"
              fullWidth
              value={quantity}
              onChange={(e) => setQuantity(parseInt(e.target.value) || 1)}
              InputProps={{
                startAdornment: <InputAdornment position="start"><Package size={16} /></InputAdornment>
              }}
              sx={{
                '& .MuiOutlinedInput-root': {
                  bgcolor: '#ffffff',
                  '& fieldset': { borderColor: '#e0e0e0' },
                  '&:hover fieldset': { borderColor: '#7c3aed' },
                  '&.Mui-focused fieldset': { borderColor: '#7c3aed' },
                },
                '& .MuiInputBase-input': { 
                  color: '#1a1a2e',
                },
              }}
            />
          </Grid>

          {/* Right: Results */}
          <Grid item xs={12} md={7}>
            <Typography variant="subtitle2" color="text.secondary" gutterBottom>
              PER UNIT
            </Typography>
            <Grid container spacing={1} sx={{ mb: 3 }}>
              <Grid item xs={6} sm={3}>
                <StatBox label="Total Cost" value={calculations.totalCostPerUnit} prefix="$" />
              </Grid>
              <Grid item xs={6} sm={3}>
                <StatBox 
                  label="Profit" 
                  value={calculations.profitPerUnit} 
                  prefix="$"
                  color={calculations.isProfitable ? habexa.success.main : habexa.error.main}
                />
              </Grid>
              <Grid item xs={6} sm={3}>
                <StatBox 
                  label="ROI" 
                  value={calculations.roi} 
                  suffix="%"
                  color={parseFloat(calculations.roi) >= 30 ? habexa.success.main : habexa.warning.main}
                />
              </Grid>
              <Grid item xs={6} sm={3}>
                <StatBox label="Margin" value={calculations.margin} suffix="%" />
              </Grid>
            </Grid>

            <Typography variant="subtitle2" color="text.secondary" gutterBottom>
              TOTAL ({quantity} units)
            </Typography>
            <Grid container spacing={1} sx={{ mb: 3 }}>
              <Grid item xs={6} sm={3}>
                <StatBox 
                  label="Investment" 
                  value={calculations.totalInvestment} 
                  prefix="$"
                  tooltip="Total cash needed to purchase inventory"
                />
              </Grid>
              <Grid item xs={6} sm={3}>
                <StatBox label="Revenue" value={calculations.totalRevenue} prefix="$" />
              </Grid>
              <Grid item xs={6} sm={3}>
                <StatBox label="Fees" value={calculations.totalFeesCost} prefix="$" />
              </Grid>
              <Grid item xs={6} sm={3}>
                <StatBox 
                  label="Net Profit" 
                  value={calculations.totalProfit} 
                  prefix="$"
                  color={calculations.isProfitable ? habexa.success.main : habexa.error.main}
                />
              </Grid>
            </Grid>

            <Divider sx={{ my: 2 }} />

            <Typography variant="subtitle2" color="text.secondary" gutterBottom>
              BREAK-EVEN ANALYSIS
            </Typography>
            <Grid container spacing={1}>
              <Grid item xs={6}>
                <StatBox 
                  label="Min Sell Price" 
                  value={calculations.breakEvenPrice} 
                  prefix="$"
                  tooltip="Minimum price to break even"
                />
              </Grid>
              <Grid item xs={6}>
                <StatBox 
                  label="Units to Profit" 
                  value={calculations.breakEvenQuantity}
                  tooltip="Units needed to recover investment"
                />
              </Grid>
            </Grid>
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );
}

