import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  CircularProgress,
  Alert,
  Chip,
  TableSortLabel,
  TablePagination,
  Button,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
} from '@mui/material';
import {
  DollarSign,
  TrendingUp,
  TrendingDown,
  Package,
  RefreshCw,
} from 'lucide-react';
import api from '../services/api';
import { useToast } from '../context/ToastContext';

// Format currency helper
const formatCurrency = (value) => {
  if (value === null || value === undefined) return '$0.00';
  return `$${parseFloat(value).toFixed(2)}`;
};

// Format percentage helper
const formatPercentage = (value) => {
  if (value === null || value === undefined) return '0%';
  return `${parseFloat(value).toFixed(1)}%`;
};

export default function FinancialDashboard() {
  const { showToast } = useToast();
  
  const [summary, setSummary] = useState(null);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [recalculating, setRecalculating] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [sortBy, setSortBy] = useState('roi_percentage');
  const [sortOrder, setSortOrder] = useState('desc');
  const [period, setPeriod] = useState('all');

  useEffect(() => {
    fetchSummary();
    fetchProducts();
  }, [period]);

  useEffect(() => {
    fetchProducts();
  }, [page, pageSize, sortBy, sortOrder]);

  const fetchSummary = async () => {
    try {
      const response = await api.get(`/financial/dashboard/summary?period=${period}`);
      setSummary(response.data);
    } catch (error) {
      console.error('Error fetching financial summary:', error);
      showToast('Failed to load financial summary', 'error');
    }
  };

  const fetchProducts = async () => {
    setLoading(true);
    try {
      const response = await api.get(`/financial/dashboard/products`, {
        params: {
          page,
          page_size: pageSize,
          sort_by: sortBy,
          sort_order: sortOrder,
        }
      });
      setProducts(response.data.products || []);
    } catch (error) {
      console.error('Error fetching financial products:', error);
      showToast('Failed to load products', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleRecalculateAll = async () => {
    setRecalculating(true);
    try {
      // Recalculate financials for all products
      const productIds = products.map(p => p.id);
      let successCount = 0;
      
      for (const productId of productIds) {
        try {
          await api.post(`/financial/product/${productId}/recalculate`);
          successCount++;
        } catch (error) {
          console.error(`Error recalculating product ${productId}:`, error);
        }
      }
      
      showToast(`Recalculated financials for ${successCount} products`, 'success');
      fetchSummary();
      fetchProducts();
    } catch (error) {
      console.error('Error recalculating financials:', error);
      showToast('Failed to recalculate financials', 'error');
    } finally {
      setRecalculating(false);
    }
  };

  const handleSort = (field) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortOrder('desc');
    }
  };

  const getROIColor = (roi) => {
    if (roi >= 50) return 'success';
    if (roi >= 30) return 'warning';
    if (roi >= 15) return 'info';
    return 'error';
  };

  if (loading && !summary) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3, bgcolor: '#f5f5f5', minHeight: '100vh' }}>
      {/* Header */}
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h4" fontWeight={600}>
          Financial Dashboard
        </Typography>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>Period</InputLabel>
            <Select
              value={period}
              onChange={(e) => setPeriod(e.target.value)}
              label="Period"
            >
              <MenuItem value="all">All Time</MenuItem>
              <MenuItem value="month">This Month</MenuItem>
              <MenuItem value="quarter">This Quarter</MenuItem>
              <MenuItem value="year">This Year</MenuItem>
            </Select>
          </FormControl>
          <Button
            variant="outlined"
            startIcon={<RefreshCw size={16} />}
            onClick={handleRecalculateAll}
            disabled={recalculating}
          >
            {recalculating ? 'Recalculating...' : 'Recalculate All'}
          </Button>
        </Box>
      </Box>

      {/* Summary Cards */}
      {summary && (
        <Grid container spacing={2} sx={{ mb: 3 }}>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography variant="overline" color="text.secondary">Total Cost</Typography>
                <Typography variant="h4" fontWeight={600} color="error.main">
                  {formatCurrency(summary.total_cost)}
                </Typography>
                <Box sx={{ mt: 1 }}>
                  <Typography variant="caption" color="text.secondary">
                    Supplier: {formatCurrency(summary.total_supplier_cost)}
                  </Typography>
                  <Typography variant="caption" color="text.secondary" display="block">
                    3PL: {formatCurrency(summary.total_tpl_cost)}
                  </Typography>
                  <Typography variant="caption" color="text.secondary" display="block">
                    Shipping: {formatCurrency(summary.total_shipping_cost)}
                  </Typography>
                  <Typography variant="caption" color="text.secondary" display="block">
                    Fees: {formatCurrency(summary.total_fba_fees + summary.total_referral_fees)}
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography variant="overline" color="text.secondary">Total Revenue</Typography>
                <Typography variant="h4" fontWeight={600} color="primary.main">
                  {formatCurrency(summary.total_revenue)}
                </Typography>
                <Box sx={{ mt: 1, display: 'flex', alignItems: 'center', gap: 0.5 }}>
                  {summary.total_revenue > summary.total_cost ? (
                    <TrendingUp size={16} color="green" />
                  ) : (
                    <TrendingDown size={16} color="red" />
                  )}
                  <Typography variant="caption" color="text.secondary">
                    {summary.total_revenue > summary.total_cost ? 'Profitable' : 'Unprofitable'}
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography variant="overline" color="text.secondary">Total Profit</Typography>
                <Typography 
                  variant="h4" 
                  fontWeight={600}
                  color={summary.total_profit > 0 ? 'success.main' : 'error.main'}
                >
                  {formatCurrency(summary.total_profit)}
                </Typography>
                <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                  Margin: {formatPercentage((summary.total_profit / summary.total_revenue * 100) || 0)}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography variant="overline" color="text.secondary">Average ROI</Typography>
                <Typography variant="h4" fontWeight={600} color={getROIColor(summary.average_roi)}>
                  {formatPercentage(summary.average_roi)}
                </Typography>
                <Box sx={{ mt: 1 }}>
                  <Typography variant="caption" color="text.secondary">
                    Products: {summary.product_count}
                  </Typography>
                  <Typography variant="caption" color="text.secondary" display="block">
                    Units: {summary.unit_count.toLocaleString()}
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Cost Breakdown Chart */}
      {summary && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" fontWeight={600} sx={{ mb: 2 }}>
              Cost Breakdown
            </Typography>
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6} md={3}>
                <Box sx={{ p: 2, bgcolor: 'error.light', borderRadius: 1 }}>
                  <Typography variant="overline" color="text.secondary">Supplier Costs</Typography>
                  <Typography variant="h5" fontWeight={600}>
                    {formatCurrency(summary.total_supplier_cost)}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {formatPercentage((summary.total_supplier_cost / summary.total_cost * 100) || 0)} of total
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <Box sx={{ p: 2, bgcolor: 'warning.light', borderRadius: 1 }}>
                  <Typography variant="overline" color="text.secondary">3PL Costs</Typography>
                  <Typography variant="h5" fontWeight={600}>
                    {formatCurrency(summary.total_tpl_cost)}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {formatPercentage((summary.total_tpl_cost / summary.total_cost * 100) || 0)} of total
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <Box sx={{ p: 2, bgcolor: 'info.light', borderRadius: 1 }}>
                  <Typography variant="overline" color="text.secondary">Shipping Costs</Typography>
                  <Typography variant="h5" fontWeight={600}>
                    {formatCurrency(summary.total_shipping_cost)}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {formatPercentage((summary.total_shipping_cost / summary.total_cost * 100) || 0)} of total
                  </Typography>
                </Box>
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <Box sx={{ p: 2, bgcolor: 'secondary.light', borderRadius: 1 }}>
                  <Typography variant="overline" color="text.secondary">Amazon Fees</Typography>
                  <Typography variant="h5" fontWeight={600}>
                    {formatCurrency(summary.total_fba_fees + summary.total_referral_fees)}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {formatPercentage(((summary.total_fba_fees + summary.total_referral_fees) / summary.total_cost * 100) || 0)} of total
                  </Typography>
                </Box>
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      )}

      {/* Products Table */}
      <Card>
        <CardContent>
          <Typography variant="h6" fontWeight={600} sx={{ mb: 2 }}>
            Product Financials
          </Typography>
          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
              <CircularProgress />
            </Box>
          ) : products.length === 0 ? (
            <Alert severity="info">No products with financial data</Alert>
          ) : (
            <>
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Product</TableCell>
                      <TableCell align="right">Supplier Cost</TableCell>
                      <TableCell align="right">3PL Cost</TableCell>
                      <TableCell align="right">Shipping</TableCell>
                      <TableCell align="right">FBA Fees</TableCell>
                      <TableCell align="right">Total Cost</TableCell>
                      <TableCell align="right">Revenue</TableCell>
                      <TableCell align="right">Profit</TableCell>
                      <TableCell align="right">
                        <TableSortLabel
                          active={sortBy === 'roi_percentage'}
                          direction={sortBy === 'roi_percentage' ? sortOrder : 'asc'}
                          onClick={() => handleSort('roi_percentage')}
                        >
                          ROI %
                        </TableSortLabel>
                      </TableCell>
                      <TableCell align="right">Margin %</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {products.map((product) => (
                      <TableRow key={product.id}>
                        <TableCell>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            {product.image_url && (
                              <Box
                                component="img"
                                src={product.image_url}
                                alt={product.title}
                                sx={{ width: 40, height: 40, objectFit: 'contain', borderRadius: 1 }}
                              />
                            )}
                            <Box>
                              <Typography variant="body2" fontWeight={600}>
                                {product.title || 'Unknown Product'}
                              </Typography>
                              <Typography variant="caption" color="text.secondary">
                                ASIN: {product.asin}
                              </Typography>
                            </Box>
                          </Box>
                        </TableCell>
                        <TableCell align="right">
                          <Typography variant="body2">
                            {formatCurrency(product.supplier_cost)}
                          </Typography>
                        </TableCell>
                        <TableCell align="right">
                          <Typography variant="body2">
                            {formatCurrency(product.tpl_cost)}
                          </Typography>
                        </TableCell>
                        <TableCell align="right">
                          <Typography variant="body2">
                            {formatCurrency(product.shipping_cost)}
                          </Typography>
                        </TableCell>
                        <TableCell align="right">
                          <Typography variant="body2">
                            {formatCurrency(product.fba_fees + product.referral_fee)}
                          </Typography>
                        </TableCell>
                        <TableCell align="right">
                          <Typography variant="body2" fontWeight={600}>
                            {formatCurrency(product.total_cost)}
                          </Typography>
                        </TableCell>
                        <TableCell align="right">
                          <Typography variant="body2" color="primary.main">
                            {formatCurrency(product.revenue)}
                          </Typography>
                        </TableCell>
                        <TableCell align="right">
                          <Typography
                            variant="body2"
                            fontWeight={600}
                            color={product.profit > 0 ? 'success.main' : 'error.main'}
                          >
                            {formatCurrency(product.profit)}
                          </Typography>
                        </TableCell>
                        <TableCell align="right">
                          <Chip
                            label={formatPercentage(product.roi_percentage)}
                            size="small"
                            color={getROIColor(product.roi_percentage)}
                          />
                        </TableCell>
                        <TableCell align="right">
                          <Typography variant="body2">
                            {formatPercentage(product.margin_percentage)}
                          </Typography>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
              <TablePagination
                component="div"
                count={products.length}
                page={page - 1}
                onPageChange={(e, newPage) => setPage(newPage + 1)}
                rowsPerPage={pageSize}
                onRowsPerPageChange={(e) => {
                  setPageSize(parseInt(e.target.value, 10));
                  setPage(1);
                }}
                rowsPerPageOptions={[25, 50, 100]}
              />
            </>
          )}
        </CardContent>
      </Card>
    </Box>
  );
}

