import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  InputAdornment,
  Grid,
  Divider,
  Chip,
  ToggleButton,
  ToggleButtonGroup,
  Tooltip,
  IconButton,
  Card,
  CardContent
} from '@mui/material';
import InfoIcon from '@mui/icons-material/Info';
import { Calculator } from 'lucide-react';
import { habexa } from '../../../theme';

export default function ProfitCalculator({ 
  initialBuyCost = 0,
  sellPrice = 0,
  referralFee = 0,
  fbaFee = 0,
  initialQuantity = 1,
  onCalculate
}) {
  // Inputs
  const [costPrice, setCostPrice] = useState(initialBuyCost);
  const [salePrice, setSalePrice] = useState(sellPrice);
  const [fulfillmentType, setFulfillmentType] = useState('FBA');
  const [storageMonths, setStorageMonths] = useState(0);
  const [quantity, setQuantity] = useState(initialQuantity);
  
  // Additional costs
  const [prepFee, setPrepFee] = useState(0);
  const [inboundShipping, setInboundShipping] = useState(0);
  const [miscFee, setMiscFee] = useState(0);
  const [miscFeePercent, setMiscFeePercent] = useState(0);
  const [discount, setDiscount] = useState(0);
  
  // Use provided fees or calculate
  const [calculatedReferralFee, setCalculatedReferralFee] = useState(referralFee);
  const [calculatedFbaFee, setCalculatedFbaFee] = useState(fbaFee);
  
  // Calculated values
  const [calculations, setCalculations] = useState({
    referralFee: 0,
    fbaFee: 0,
    closingFee: 0,
    storageFee: 0,
    inboundPlacementFee: 0,
    totalFees: 0,
    profit: 0,
    roi: 0,
    margin: 0,
    maxCost: 0,
    breakevenPrice: 0,
    amazonPayout: 0,
    totalCost: 0,
    totalRevenue: 0,
    totalProfit: 0
  });
  
  // Update when props change
  useEffect(() => {
    if (initialBuyCost > 0) {
      setCostPrice(initialBuyCost);
    }
  }, [initialBuyCost]);
  
  useEffect(() => {
    if (sellPrice > 0) {
      setSalePrice(sellPrice);
    }
  }, [sellPrice]);
  
  useEffect(() => {
    if (initialQuantity > 0) {
      setQuantity(initialQuantity);
    }
  }, [initialQuantity]);
  
  // Calculate everything when inputs change
  useEffect(() => {
    calculateProfitability();
  }, [costPrice, salePrice, fulfillmentType, storageMonths, quantity, prepFee, inboundShipping, miscFee, miscFeePercent, discount, referralFee, fbaFee]);
  
  const calculateProfitability = () => {
    const cost = parseFloat(costPrice) || 0;
    const sale = parseFloat(salePrice) || 0;
    const qty = parseInt(quantity) || 1;
    
    // Use provided fees or calculate
    let refFee = referralFee;
    let fba = fbaFee;
    
    // If fees not provided, calculate them
    if (!refFee && sale > 0) {
      refFee = sale * 0.15; // 15% referral fee (typical)
    }
    if (!fba && sale > 0 && fulfillmentType === 'FBA') {
      fba = calculateFBAFee(sale);
    } else if (fulfillmentType === 'FBM') {
      fba = 0; // FBM has no FBA fee
    }
    
    // Amazon fees calculation
    const closingFee = sale < 10 ? 0 : 0; // Closing fee (deprecated for most categories)
    const storageFeePerUnit = calculateStorageFee(storageMonths);
    const inboundPlacementFee = 0; // Varies by location
    
    // Additional costs
    const prepFeeTotal = parseFloat(prepFee) || 0;
    const inboundShippingTotal = parseFloat(inboundShipping) || 0;
    const miscFeeTotal = parseFloat(miscFee) || 0;
    const miscFeePercentTotal = (cost * (parseFloat(miscFeePercent) || 0)) / 100;
    const discountTotal = parseFloat(discount) || 0;
    
    // Total fees per unit
    const totalFees = refFee + fba + closingFee + storageFeePerUnit + 
                      inboundPlacementFee + prepFeeTotal + inboundShippingTotal + 
                      miscFeeTotal + miscFeePercentTotal;
    
    // Profit calculations
    const netSale = sale - discountTotal;
    const profit = netSale - cost - totalFees;
    const roi = cost > 0 ? ((profit / cost) * 100) : 0;
    const margin = sale > 0 ? ((profit / sale) * 100) : 0;
    
    // Maximum cost (what you can pay and still profit)
    const maxCost = netSale - totalFees - 0.01; // Leave $0.01 profit
    
    // Breakeven price (minimum sale price to break even)
    const breakevenPrice = cost + totalFees;
    
    // Amazon payout (what Amazon deposits)
    const amazonPayout = sale - totalFees;
    
    // Totals
    const totalCost = cost * qty;
    const totalRevenue = netSale * qty;
    const totalProfit = profit * qty;
    
    const calcResults = {
      referralFee: refFee,
      fbaFee: fba,
      closingFee,
      storageFee: storageFeePerUnit,
      inboundPlacementFee,
      totalFees,
      profit,
      roi,
      margin,
      maxCost,
      breakevenPrice,
      amazonPayout,
      totalCost,
      totalRevenue,
      totalProfit
    };
    
    setCalculations(calcResults);
    
    // Callback
    if (onCalculate) {
      onCalculate({
        ...calcResults,
        costPrice: cost,
        salePrice: sale,
        quantity: qty
      });
    }
  };
  
  const calculateFBAFee = (salePrice) => {
    // Simplified FBA fee calculation (based on price tiers)
    // Real calculation depends on size tier and weight
    if (salePrice < 10) return 2.50;
    if (salePrice < 15) return 3.00;
    if (salePrice < 20) return 3.50;
    if (salePrice < 30) return 4.00;
    if (salePrice < 40) return 4.50;
    if (salePrice < 50) return 5.00;
    return 5.50;
  };
  
  const calculateStorageFee = (months) => {
    // Monthly storage fee (simplified)
    const monthlyRate = 0.87; // $0.87 per cubic foot per month (Jan-Sep)
    const estimatedVolume = 0.5; // Assume 0.5 cubic feet
    return monthlyRate * estimatedVolume * months;
  };
  
  return (
    <Card sx={{ mt: 3, bgcolor: '#ffffff' }}>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
          <Calculator size={20} />
          <Typography variant="h6" fontWeight="600">Profit Calculator</Typography>
          <Chip label="Changes don't save" size="small" color="warning" sx={{ ml: 'auto' }} />
        </Box>
        
        <Grid container spacing={3}>
          {/* LEFT SIDE - INPUTS */}
          <Grid item xs={12} md={5}>
            {/* Cost Price */}
            <TextField
              fullWidth
              label="Cost Price"
              type="number"
              value={costPrice}
              onChange={(e) => setCostPrice(e.target.value)}
              InputProps={{
                startAdornment: <InputAdornment position="start">$</InputAdornment>
              }}
              sx={{ mb: 2 }}
            />
            
            {/* Sale Price */}
            <TextField
              fullWidth
              label="Sale Price"
              type="number"
              value={salePrice}
              onChange={(e) => setSalePrice(e.target.value)}
              InputProps={{
                startAdornment: <InputAdornment position="start">$</InputAdornment>
              }}
              sx={{ mb: 2 }}
            />
            
            {/* Fulfillment Type */}
            <Box sx={{ mb: 2 }}>
              <Typography variant="caption" color="text.secondary">Fulfillment Type</Typography>
              <ToggleButtonGroup
                value={fulfillmentType}
                exclusive
                onChange={(e, val) => val && setFulfillmentType(val)}
                fullWidth
                sx={{ mt: 0.5 }}
              >
                <ToggleButton value="FBA">FBA</ToggleButton>
                <ToggleButton value="FBM">FBM</ToggleButton>
              </ToggleButtonGroup>
            </Box>
            
            {/* Storage Months */}
            <TextField
              fullWidth
              label="Storage (Months)"
              type="number"
              value={storageMonths}
              onChange={(e) => setStorageMonths(e.target.value)}
              sx={{ mb: 2 }}
            />
            
            {/* Quantity */}
            <TextField
              fullWidth
              label="Quantity"
              type="number"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              sx={{ mb: 2 }}
            />
            
            <Divider sx={{ my: 2 }} />
            
            {/* Additional Costs (Collapsible) */}
            <Typography variant="body2" fontWeight="bold" gutterBottom>
              Additional Costs (Optional)
            </Typography>
            
            <TextField
              fullWidth
              label="Prep Fee"
              type="number"
              size="small"
              value={prepFee}
              onChange={(e) => setPrepFee(e.target.value)}
              InputProps={{
                startAdornment: <InputAdornment position="start">$</InputAdornment>
              }}
              sx={{ mb: 1 }}
            />
            
            <TextField
              fullWidth
              label="Inbound Shipping"
              type="number"
              size="small"
              value={inboundShipping}
              onChange={(e) => setInboundShipping(e.target.value)}
              InputProps={{
                startAdornment: <InputAdornment position="start">$</InputAdornment>
              }}
              sx={{ mb: 1 }}
            />
            
            <TextField
              fullWidth
              label="Misc Fee"
              type="number"
              size="small"
              value={miscFee}
              onChange={(e) => setMiscFee(e.target.value)}
              InputProps={{
                startAdornment: <InputAdornment position="start">$</InputAdornment>
              }}
              sx={{ mb: 1 }}
            />
            
            <TextField
              fullWidth
              label="Misc Fee (%)"
              type="number"
              size="small"
              value={miscFeePercent}
              onChange={(e) => setMiscFeePercent(e.target.value)}
              InputProps={{
                endAdornment: <InputAdornment position="end">%</InputAdornment>
              }}
              sx={{ mb: 1 }}
            />
            
            <TextField
              fullWidth
              label="Discount"
              type="number"
              size="small"
              value={discount}
              onChange={(e) => setDiscount(e.target.value)}
              InputProps={{
                startAdornment: <InputAdornment position="start">$</InputAdornment>
              }}
            />
          </Grid>
          
          {/* RIGHT SIDE - RESULTS */}
          <Grid item xs={12} md={7}>
            {/* Key Metrics */}
            <Box sx={{ mb: 3 }}>
              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <Paper variant="outlined" sx={{ p: 2, textAlign: 'center' }}>
                    <Typography variant="caption" color="text.secondary">Profit</Typography>
                    <Typography variant="h5" color={calculations.profit > 0 ? 'success.main' : 'error.main'}>
                      ${calculations.profit.toFixed(2)}
                    </Typography>
                  </Paper>
                </Grid>
                
                <Grid item xs={6}>
                  <Paper variant="outlined" sx={{ p: 2, textAlign: 'center' }}>
                    <Typography variant="caption" color="text.secondary">ROI</Typography>
                    <Typography variant="h5" color={calculations.roi > 0 ? 'success.main' : 'error.main'}>
                      {calculations.roi.toFixed(1)}%
                    </Typography>
                  </Paper>
                </Grid>
                
                <Grid item xs={6}>
                  <Paper variant="outlined" sx={{ p: 2, textAlign: 'center' }}>
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 0.5 }}>
                      Maximum Cost
                      <Tooltip title="Maximum price you can pay and still make a profit">
                        <IconButton size="small" sx={{ p: 0 }}><InfoIcon fontSize="small" /></IconButton>
                      </Tooltip>
                    </Typography>
                    <Typography variant="h6">
                      ${calculations.maxCost.toFixed(2)}
                    </Typography>
                  </Paper>
                </Grid>
                
                <Grid item xs={6}>
                  <Paper variant="outlined" sx={{ p: 2, textAlign: 'center' }}>
                    <Typography variant="caption" color="text.secondary">Profit Margin</Typography>
                    <Typography variant="h6">
                      {calculations.margin.toFixed(1)}%
                    </Typography>
                  </Paper>
                </Grid>
              </Grid>
            </Box>
            
            {/* Fee Breakdown */}
            <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
                <Typography variant="body2" fontWeight="bold" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  Total Fees
                </Typography>
                <Typography variant="h6" color="error.main">
                  ${calculations.totalFees.toFixed(2)}
                </Typography>
              </Box>
              
              <Divider sx={{ my: 1 }} />
              
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography variant="body2" color="text.secondary" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                    Referral Fee
                    <Tooltip title="15% of sale price (typical for most categories)">
                      <IconButton size="small" sx={{ p: 0 }}><InfoIcon fontSize="small" /></IconButton>
                    </Tooltip>
                  </Typography>
                  <Typography variant="body2">${calculations.referralFee.toFixed(2)}</Typography>
                </Box>
                
                {fulfillmentType === 'FBA' && (
                  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="body2" color="text.secondary">Fulfillment (FBA)</Typography>
                    <Typography variant="body2">${calculations.fbaFee.toFixed(2)}</Typography>
                  </Box>
                )}
                
                {calculations.closingFee > 0 && (
                  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="body2" color="text.secondary">Closing Fee</Typography>
                    <Typography variant="body2">${calculations.closingFee.toFixed(2)}</Typography>
                  </Box>
                )}
                
                {storageMonths > 0 && (
                  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="body2" color="text.secondary">Storage Fee</Typography>
                    <Typography variant="body2">${calculations.storageFee.toFixed(2)}</Typography>
                  </Box>
                )}
                
                {prepFee > 0 && (
                  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="body2" color="text.secondary">Prep Fee</Typography>
                    <Typography variant="body2">${parseFloat(prepFee).toFixed(2)}</Typography>
                  </Box>
                )}
                
                {inboundShipping > 0 && (
                  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="body2" color="text.secondary">Inbound Shipping</Typography>
                    <Typography variant="body2">${parseFloat(inboundShipping).toFixed(2)}</Typography>
                  </Box>
                )}
                
                {calculations.inboundPlacementFee > 0 && (
                  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="body2" color="text.secondary">Inbound Placement (Q)</Typography>
                    <Typography variant="body2">${calculations.inboundPlacementFee.toFixed(2)}</Typography>
                  </Box>
                )}
                
                {miscFee > 0 && (
                  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="body2" color="text.secondary">Misc Fee</Typography>
                    <Typography variant="body2">${parseFloat(miscFee).toFixed(2)}</Typography>
                  </Box>
                )}
                
                {miscFeePercent > 0 && (
                  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="body2" color="text.secondary">Misc Fee (% of cost)</Typography>
                    <Typography variant="body2">${((costPrice * miscFeePercent) / 100).toFixed(2)}</Typography>
                  </Box>
                )}
              </Box>
            </Paper>
            
            {/* Additional Metrics */}
            <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                {discount > 0 && (
                  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="body2" fontWeight="bold">Discount</Typography>
                    <Typography variant="body2">${parseFloat(discount).toFixed(2)}</Typography>
                  </Box>
                )}
                
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography variant="body2" fontWeight="bold">Breakeven Sale Price</Typography>
                  <Typography variant="body2">${calculations.breakevenPrice.toFixed(2)}</Typography>
                </Box>
                
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography variant="body2" fontWeight="bold" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                    Estimated Amz. Payout
                    <Tooltip title="Amount Amazon will deposit after fees">
                      <IconButton size="small" sx={{ p: 0 }}><InfoIcon fontSize="small" /></IconButton>
                    </Tooltip>
                  </Typography>
                  <Typography variant="body2" color="success.main">
                    ${calculations.amazonPayout.toFixed(2)}
                  </Typography>
                </Box>
              </Box>
            </Paper>
            
            {/* Totals (Quantity) */}
            {quantity > 1 && (
              <Paper variant="outlined" sx={{ p: 2, bgcolor: 'action.hover' }}>
                <Typography variant="body2" fontWeight="bold" gutterBottom>
                  Quantity: {quantity}
                </Typography>
                
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="body2">Cost</Typography>
                    <Typography variant="body2">${calculations.totalCost.toFixed(2)}</Typography>
                  </Box>
                  
                  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="body2">Sale</Typography>
                    <Typography variant="body2">${calculations.totalRevenue.toFixed(2)}</Typography>
                  </Box>
                  
                  <Divider />
                  
                  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="body2" fontWeight="bold">Total Profit</Typography>
                    <Typography variant="h6" color={calculations.totalProfit > 0 ? 'success.main' : 'error.main'}>
                      ${calculations.totalProfit.toFixed(2)}
                    </Typography>
                  </Box>
                </Box>
              </Paper>
            )}
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );
}
