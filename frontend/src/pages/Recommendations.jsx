import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Typography,
  Paper,
  Button,
  RadioGroup,
  FormControlLabel,
  Radio,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Card,
  CardContent,
  Chip,
  Alert,
  CircularProgress,
  Divider,
  Stack,
  Grid
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export default function Recommendations() {
  const navigate = useNavigate();
  
  const [suppliers, setSuppliers] = useState([]);
  const [selectedSupplier, setSelectedSupplier] = useState('');
  const [goalType, setGoalType] = useState('meet_minimum');
  const [budget, setBudget] = useState(2000);
  const [profitTarget, setProfitTarget] = useState(10000);
  const [maxBudget, setMaxBudget] = useState(15000);
  const [constraints, setConstraints] = useState({
    min_roi: 30,
    max_fba_sellers: 30,
    max_days_to_sell: 60,
    avoid_hazmat: true,
    pricing_mode: '365d_avg'
  });
  
  const [loading, setLoading] = useState(false);
  const [recommendation, setRecommendation] = useState(null);
  const [error, setError] = useState(null);
  
  useEffect(() => {
    fetchSuppliers();
  }, []);
  
  const fetchSuppliers = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_URL}/api/v1/suppliers`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setSuppliers(response.data.suppliers || []);
    } catch (err) {
      console.error('Error fetching suppliers:', err);
    }
  };
  
  const handleGenerate = async () => {
    if (!selectedSupplier) {
      setError('Please select a supplier');
      return;
    }
    
    setLoading(true);
    setError(null);
    setRecommendation(null);
    
    try {
      const token = localStorage.getItem('token');
      
      const goalParams = {};
      if (goalType === 'meet_minimum') {
        goalParams.budget = budget;
      } else if (goalType === 'target_profit') {
        goalParams.profit_target = profitTarget;
        goalParams.max_budget = maxBudget;
      }
      
      const response = await axios.post(
        `${API_URL}/api/v1/recommendations/generate`,
        {
          supplier_id: selectedSupplier,
          goal_type: goalType,
          goal_params: goalParams,
          constraints
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      if (response.data.success) {
        setRecommendation(response.data);
      } else {
        setError(response.data.error || 'Failed to generate recommendations');
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to generate recommendations');
    } finally {
      setLoading(false);
    }
  };
  
  const handleAddToBuyList = async () => {
    if (!recommendation?.run_id) return;
    
    try {
      const token = localStorage.getItem('token');
      await axios.post(
        `${API_URL}/api/v1/recommendations/runs/${recommendation.run_id}/add-to-buy-list`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      alert('Products added to buy list successfully!');
      navigate('/buy-lists');
    } catch (err) {
      alert('Failed to add to buy list: ' + (err.response?.data?.detail || err.message));
    }
  };
  
  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Typography variant="h4" gutterBottom>
        🎯 Order Recommendations
      </Typography>
      
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          What's Your Goal?
        </Typography>
        
        <FormControl fullWidth sx={{ mb: 3 }}>
          <InputLabel>Select Supplier</InputLabel>
          <Select
            value={selectedSupplier}
            onChange={(e) => setSelectedSupplier(e.target.value)}
            label="Select Supplier"
          >
            {suppliers.map((supplier) => (
              <MenuItem key={supplier.id} value={supplier.id}>
                {supplier.name}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        
        <RadioGroup value={goalType} onChange={(e) => setGoalType(e.target.value)}>
          <FormControlLabel
            value="meet_minimum"
            control={<Radio />}
            label={
              <Box>
                <Typography>Meet Minimum Order</Typography>
                {goalType === 'meet_minimum' && (
                  <TextField
                    type="number"
                    label="Budget"
                    value={budget}
                    onChange={(e) => setBudget(parseFloat(e.target.value) || 0)}
                    sx={{ mt: 1, width: 200 }}
                    InputProps={{ startAdornment: '$' }}
                  />
                )}
              </Box>
            }
          />
          <FormControlLabel
            value="target_profit"
            control={<Radio />}
            label={
              <Box>
                <Typography>Target Profit</Typography>
                {goalType === 'target_profit' && (
                  <Box sx={{ mt: 1 }}>
                    <TextField
                      type="number"
                      label="Profit Target"
                      value={profitTarget}
                      onChange={(e) => setProfitTarget(parseFloat(e.target.value) || 0)}
                      sx={{ mr: 2, width: 200 }}
                      InputProps={{ startAdornment: '$' }}
                    />
                    <TextField
                      type="number"
                      label="Max Budget"
                      value={maxBudget}
                      onChange={(e) => setMaxBudget(parseFloat(e.target.value) || 0)}
                      sx={{ width: 200 }}
                      InputProps={{ startAdornment: '$' }}
                    />
                  </Box>
                )}
              </Box>
            }
          />
        </RadioGroup>
        
        <Divider sx={{ my: 3 }} />
        
        <Typography variant="h6" gutterBottom>
          Constraints & Preferences
        </Typography>
        
        <Grid container spacing={2} sx={{ mb: 3 }}>
          <Grid item xs={12} sm={6}>
            <TextField
              type="number"
              label="Min ROI %"
              value={constraints.min_roi}
              onChange={(e) => setConstraints({...constraints, min_roi: parseFloat(e.target.value) || 0})}
              fullWidth
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField
              type="number"
              label="Max FBA Sellers"
              value={constraints.max_fba_sellers}
              onChange={(e) => setConstraints({...constraints, max_fba_sellers: parseInt(e.target.value) || 0})}
              fullWidth
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <TextField
              type="number"
              label="Max Days to Sell"
              value={constraints.max_days_to_sell}
              onChange={(e) => setConstraints({...constraints, max_days_to_sell: parseInt(e.target.value) || 0})}
              fullWidth
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <FormControl fullWidth>
              <InputLabel>Pricing Mode</InputLabel>
              <Select
                value={constraints.pricing_mode}
                onChange={(e) => setConstraints({...constraints, pricing_mode: e.target.value})}
                label="Pricing Mode"
              >
                <MenuItem value="current">Current</MenuItem>
                <MenuItem value="30d_avg">30-Day Average</MenuItem>
                <MenuItem value="90d_avg">90-Day Average</MenuItem>
                <MenuItem value="365d_avg">365-Day Average (Recommended)</MenuItem>
              </Select>
            </FormControl>
          </Grid>
        </Grid>
        
        <Button
          variant="contained"
          color="primary"
          size="large"
          onClick={handleGenerate}
          disabled={loading || !selectedSupplier}
          fullWidth
        >
          {loading ? <CircularProgress size={24} /> : 'Generate Recommendations'}
        </Button>
      </Paper>
      
      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}
      
      {recommendation && recommendation.results && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h5" gutterBottom>
            ✅ Recommended Order
          </Typography>
          
          <Grid container spacing={2} sx={{ mb: 3 }}>
            <Grid item xs={12} sm={3}>
              <Card>
                <CardContent>
                  <Typography color="textSecondary">Total Investment</Typography>
                  <Typography variant="h6">${recommendation.results.total_cost?.toLocaleString()}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={3}>
              <Card>
                <CardContent>
                  <Typography color="textSecondary">Expected Profit</Typography>
                  <Typography variant="h6" color="success.main">
                    ${recommendation.results.total_profit?.toLocaleString()}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={3}>
              <Card>
                <CardContent>
                  <Typography color="textSecondary">ROI</Typography>
                  <Typography variant="h6">{recommendation.results.roi?.toFixed(1)}%</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={3}>
              <Card>
                <CardContent>
                  <Typography color="textSecondary">Products</Typography>
                  <Typography variant="h6">{recommendation.results.product_count}</Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
          
          <Divider sx={{ my: 3 }} />
          
          <Typography variant="h6" gutterBottom>
            Products to Buy
          </Typography>
          
          <Stack spacing={2}>
            {recommendation.results.products?.map((product, idx) => (
              <Card key={idx}>
                <CardContent>
                  <Box display="flex" justifyContent="space-between" alignItems="start">
                    <Box flex={1}>
                      <Typography variant="h6">{product.title || product.asin}</Typography>
                      <Typography variant="body2" color="textSecondary">
                        ASIN: {product.asin}
                      </Typography>
                      
                      <Box mt={2}>
                        <Chip
                          label={`Score: ${product.score?.toFixed(0)}/100`}
                          color={product.score >= 80 ? 'success' : product.score >= 60 ? 'warning' : 'default'}
                          size="small"
                          sx={{ mr: 1 }}
                        />
                        <Typography variant="body2" sx={{ mt: 1 }}>
                          Qty: {product.recommended_quantity} | Cost: ${product.recommended_cost?.toFixed(2)} | 
                          Profit: ${product.expected_profit?.toFixed(2)} | 
                          ROI: {product.roi?.toFixed(1)}%
                        </Typography>
                      </Box>
                      
                      {product.why_recommended && product.why_recommended.length > 0 && (
                        <Box mt={1}>
                          <Typography variant="body2" fontWeight="bold">
                            ✅ Why Recommended:
                          </Typography>
                          <ul style={{ margin: 0, paddingLeft: 20 }}>
                            {product.why_recommended.map((reason, i) => (
                              <li key={i}><Typography variant="body2">{reason}</Typography></li>
                            ))}
                          </ul>
                        </Box>
                      )}
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            ))}
          </Stack>
          
          <Box mt={3}>
            <Button
              variant="contained"
              color="success"
              onClick={handleAddToBuyList}
              sx={{ mr: 2 }}
            >
              Add to Buy List
            </Button>
            <Button variant="outlined" onClick={() => setRecommendation(null)}>
              Clear
            </Button>
          </Box>
        </Paper>
      )}
    </Container>
  );
}

