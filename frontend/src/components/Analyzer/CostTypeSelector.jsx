import React, { useState, useEffect } from 'react';
import {
  RadioGroup,
  FormControlLabel,
  Radio,
  TextField,
  Box,
  Typography,
  Paper,
  Divider
} from '@mui/material';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export default function CostTypeSelector({
  productSourceId,
  costType: initialCostType,
  packSize: initialPackSize,
  caseSize: initialCaseSize,
  wholesaleCost: initialWholesaleCost,
  onUpdate
}) {
  const [costType, setCostType] = useState(initialCostType || 'unit');
  const [packSize, setPackSize] = useState(initialPackSize || 1);
  const [caseSize, setCaseSize] = useState(initialCaseSize || 1);
  const [wholesaleCost, setWholesaleCost] = useState(initialWholesaleCost || 0);
  const [breakdown, setBreakdown] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (productSourceId && wholesaleCost > 0) {
      calculateBreakdown();
    }
  }, [costType, packSize, caseSize, wholesaleCost, productSourceId]);

  const calculateBreakdown = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      
      // Get product data to find Amazon pack size
      const productResponse = await axios.get(
        `${API_URL}/api/v1/products/source/${productSourceId}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );

      const product = productResponse.data;
      const amazonPackSize = product?.package_quantity || 1;

      // Call cost intelligence API
      const breakdownResponse = await axios.post(
        `${API_URL}/api/v1/cost-intelligence/breakdown`,
        {
          wholesale_cost: wholesaleCost,
          cost_type: costType,
          supplier_pack_size: packSize,
          case_size: caseSize,
          amazon_item_package_quantity: amazonPackSize
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      setBreakdown(breakdownResponse.data);

      // Notify parent of update
      if (onUpdate) {
        onUpdate({
          cost_type: costType,
          pack_size: packSize,
          case_size: caseSize,
          true_unit_cost: breakdownResponse.data.true_unit_cost,
          cost_per_amazon_pack: breakdownResponse.data.cost_per_amazon_pack
        });
      }
    } catch (err) {
      console.error('Error calculating cost breakdown:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (value) => {
    if (!value) return '$0.00';
    return `$${parseFloat(value).toFixed(2)}`;
  };

  return (
    <Paper sx={{ p: 2 }}>
      <Typography variant="h6" gutterBottom>
        Cost Type Configuration
      </Typography>

      <RadioGroup
        value={costType}
        onChange={(e) => setCostType(e.target.value)}
        row
      >
        <FormControlLabel value="unit" control={<Radio />} label="Unit" />
        <FormControlLabel value="pack" control={<Radio />} label="Pack" />
        <FormControlLabel value="case" control={<Radio />} label="Case" />
      </RadioGroup>

      <Box mt={2}>
        <TextField
          label="Wholesale Cost"
          type="number"
          value={wholesaleCost}
          onChange={(e) => setWholesaleCost(parseFloat(e.target.value) || 0)}
          InputProps={{ startAdornment: '$' }}
          fullWidth
          size="small"
        />
      </Box>

      {costType === 'pack' && (
        <Box mt={2}>
          <TextField
            label="Pack Size (units per pack)"
            type="number"
            value={packSize}
            onChange={(e) => setPackSize(parseInt(e.target.value) || 1)}
            fullWidth
            size="small"
            helperText="How many individual units are in one pack?"
          />
        </Box>
      )}

      {costType === 'case' && (
        <Box mt={2}>
          <TextField
            label="Case Size (units per case)"
            type="number"
            value={caseSize}
            onChange={(e) => setCaseSize(parseInt(e.target.value) || 1)}
            fullWidth
            size="small"
            helperText="How many individual units are in one case?"
          />
        </Box>
      )}

      {breakdown && (
        <>
          <Divider sx={{ my: 2 }} />
          <Typography variant="subtitle2" gutterBottom>
            Cost Breakdown
          </Typography>
          <Box sx={{ pl: 2 }}>
            <Typography variant="body2">
              <strong>Supplier Wholesale Cost:</strong>{' '}
              {formatCurrency(breakdown.supplier_wholesale_cost)}
            </Typography>
            <Typography variant="body2">
              <strong>Supplier Cost Type:</strong> {breakdown.supplier_cost_type}
            </Typography>
            {breakdown.supplier_pack_size > 1 && (
              <Typography variant="body2">
                <strong>Supplier Pack Size:</strong> {breakdown.supplier_pack_size} units
              </Typography>
            )}
            {breakdown.supplier_case_size > 1 && (
              <Typography variant="body2">
                <strong>Supplier Case Size:</strong> {breakdown.supplier_case_size} units
              </Typography>
            )}
            <Typography variant="body2" color="primary.main" sx={{ mt: 1 }}>
              <strong>True Unit Cost:</strong>{' '}
              {formatCurrency(breakdown.true_unit_cost)}
            </Typography>
            <Typography variant="body2">
              <strong>Amazon Pack Size:</strong> {breakdown.amazon_item_package_quantity}-pack
            </Typography>
            <Typography variant="body2" color="success.main" sx={{ mt: 1 }}>
              <strong>Cost Per Amazon Pack:</strong>{' '}
              {formatCurrency(breakdown.cost_per_amazon_pack)}
            </Typography>
          </Box>
        </>
      )}

      {loading && (
        <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
          Calculating...
        </Typography>
      )}
    </Paper>
  );
}

