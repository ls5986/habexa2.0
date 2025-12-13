import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  TextField,
  Button,
  Alert,
  Divider,
  Grid,
  Card,
  CardContent
} from '@mui/material';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export default function ShippingCostCalculator({ supplierId, orderValue, totalWeight, unitCount, onCostCalculated }) {
  const [profiles, setProfiles] = useState([]);
  const [selectedProfileId, setSelectedProfileId] = useState('');
  const [calculatedCost, setCalculatedCost] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (supplierId) {
      fetchShippingProfiles();
    }
  }, [supplierId]);

  useEffect(() => {
    if (selectedProfileId && orderValue && totalWeight && unitCount) {
      calculateShippingCost();
    }
  }, [selectedProfileId, orderValue, totalWeight, unitCount]);

  const fetchShippingProfiles = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(
        `${API_URL}/api/v1/shipping-profiles?supplier_id=${supplierId}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setProfiles(response.data.profiles || []);
      
      // Auto-select default profile
      const defaultProfile = response.data.profiles?.find(p => p.is_default);
      if (defaultProfile) {
        setSelectedProfileId(defaultProfile.id);
      }
    } catch (err) {
      console.error('Error fetching shipping profiles:', err);
    }
  };

  const calculateShippingCost = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      
      // Call shipping cost calculation API
      const response = await axios.post(
        `${API_URL}/api/v1/shipping-profiles/${selectedProfileId}/calculate`,
        {
          order_value: orderValue,
          total_weight: totalWeight,
          unit_count: unitCount
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      const cost = response.data.shipping_cost || 0;
      setCalculatedCost(cost);

      if (onCostCalculated) {
        onCostCalculated(cost);
      }
    } catch (err) {
      console.error('Error calculating shipping cost:', err);
      setCalculatedCost(0);
    } finally {
      setLoading(false);
    }
  };

  const selectedProfile = profiles.find(p => p.id === selectedProfileId);

  const formatCurrency = (value) => {
    if (!value) return '$0.00';
    return `$${parseFloat(value).toFixed(2)}`;
  };

  return (
    <Paper sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom>
        Shipping Cost Calculator
      </Typography>

      <FormControl fullWidth sx={{ mb: 2 }}>
        <InputLabel>Shipping Profile</InputLabel>
        <Select
          value={selectedProfileId}
          onChange={(e) => setSelectedProfileId(e.target.value)}
          label="Shipping Profile"
        >
          {profiles.map((profile) => (
            <MenuItem key={profile.id} value={profile.id}>
              {profile.name}
              {profile.is_default && (
                <Typography component="span" variant="caption" sx={{ ml: 1, color: 'text.secondary' }}>
                  (Default)
                </Typography>
              )}
            </MenuItem>
          ))}
        </Select>
      </FormControl>

      {selectedProfile && (
        <Box sx={{ mb: 2 }}>
          <Typography variant="body2" color="text.secondary">
            Cost Type: <strong>{selectedProfile.cost_type}</strong>
          </Typography>
          {selectedProfile.free_shipping_threshold && (
            <Typography variant="body2" color="text.secondary">
              Free shipping over: {formatCurrency(selectedProfile.free_shipping_threshold)}
            </Typography>
          )}
        </Box>
      )}

      <Divider sx={{ my: 2 }} />

      <Grid container spacing={2} sx={{ mb: 2 }}>
        <Grid item xs={12} sm={4}>
          <TextField
            label="Order Value"
            value={orderValue}
            InputProps={{ startAdornment: '$' }}
            disabled
            fullWidth
            size="small"
          />
        </Grid>
        <Grid item xs={12} sm={4}>
          <TextField
            label="Total Weight (lbs)"
            value={totalWeight}
            disabled
            fullWidth
            size="small"
          />
        </Grid>
        <Grid item xs={12} sm={4}>
          <TextField
            label="Unit Count"
            value={unitCount}
            disabled
            fullWidth
            size="small"
          />
        </Grid>
      </Grid>

      {calculatedCost !== null && (
        <Card sx={{ backgroundColor: 'primary.light', mb: 2 }}>
          <CardContent>
            <Typography variant="h5" color="primary.contrastText">
              Shipping Cost: {formatCurrency(calculatedCost)}
            </Typography>
            {selectedProfile?.free_shipping_threshold && orderValue >= selectedProfile.free_shipping_threshold && (
              <Alert severity="success" sx={{ mt: 1 }}>
                Free shipping threshold met!
              </Alert>
            )}
          </CardContent>
        </Card>
      )}

      {loading && (
        <Typography variant="body2" color="text.secondary">
          Calculating...
        </Typography>
      )}
    </Paper>
  );
}

