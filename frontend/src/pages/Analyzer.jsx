import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  Box, Typography, Card, CardContent, Button, TextField, InputAdornment,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TablePagination,
  Checkbox, Chip, IconButton, Menu, MenuItem, FormControl, InputLabel, Select,
  Tooltip, CircularProgress, Alert, Dialog, DialogTitle, DialogContent,
  DialogActions, LinearProgress, Paper, Grid, Stack
} from '@mui/material';
import {
  Search, Download, RefreshCw, Settings, Filter, X, CheckCircle,
  ExternalLink, ArrowUpDown, ArrowUp, ArrowDown, Eye, EyeOff
} from 'lucide-react';
import api from '../services/api';
import { useToast } from '../context/ToastContext';
import { ANALYZER_COLUMNS, getDefaultVisibleColumns, getROIColor, getProfitTierColor, getRowColor } from '../config/analyzerColumns';

export default function Analyzer() {
  const [products, setProducts] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(new Set());
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(50);
  const [total, setTotal] = useState(0);
  const [sortBy, setSortBy] = useState('roi_percentage');
  const [sortOrder, setSortOrder] = useState('desc');
  
  // Filters
  const [filters, setFilters] = useState({
    search: '',
    category: '',
    supplier_id: '',
    min_roi: '',
    max_roi: '',
    min_margin: '',
    min_profit: '',
    profit_tier: '',
    min_est_sales: '',
    max_bsr: '',
    max_fba_sellers: '',
    is_profitable: '',
    amazon_sells: '',
    is_hazmat: ''
  });
  
  // Column visibility
  const [visibleColumns, setVisibleColumns] = useState(getDefaultVisibleColumns());
  const [columnMenuAnchor, setColumnMenuAnchor] = useState(null);
  
  // Dropdowns
  const [categories, setCategories] = useState([]);
  const [suppliers, setSuppliers] = useState([]);
  
  // Bulk operations
  const [bulkAnalyzing, setBulkAnalyzing] = useState(false);
  const [exporting, setExporting] = useState(false);
  
  const { showToast } = useToast();
  
  // Fetch data
  const fetchProducts = useCallback(async () => {
    setLoading(true);
    try {
      // Build filter object (remove empty strings)
      const filterObj = Object.fromEntries(
        Object.entries(filters).filter(([_, v]) => v !== '' && v !== null)
      );
      
      // Convert string numbers to actual numbers
      if (filterObj.min_roi) filterObj.min_roi = parseFloat(filterObj.min_roi);
      if (filterObj.max_roi) filterObj.max_roi = parseFloat(filterObj.max_roi);
      if (filterObj.min_margin) filterObj.min_margin = parseFloat(filterObj.min_margin);
      if (filterObj.min_profit) filterObj.min_profit = parseFloat(filterObj.min_profit);
      if (filterObj.min_est_sales) filterObj.min_est_sales = parseInt(filterObj.min_est_sales);
      if (filterObj.max_bsr) filterObj.max_bsr = parseInt(filterObj.max_bsr);
      if (filterObj.max_fba_sellers) filterObj.max_fba_sellers = parseInt(filterObj.max_fba_sellers);
      if (filterObj.is_profitable !== '') filterObj.is_profitable = filterObj.is_profitable === 'true';
      if (filterObj.amazon_sells !== '') filterObj.amazon_sells = filterObj.amazon_sells === 'true';
      if (filterObj.is_hazmat !== '') filterObj.is_hazmat = filterObj.is_hazmat === 'true';
      
      const response = await api.post('/analyzer/products', filterObj, {
        params: {
          page: page + 1,
          page_size: pageSize,
          sort_by: sortBy,
          sort_order: sortOrder
        }
      });
      
      setProducts(response.data.products || []);
      setTotal(response.data.total || 0);
    } catch (err) {
      console.error('Failed to fetch products:', err);
      showToast('Failed to load products', 'error');
    } finally {
      setLoading(false);
    }
  }, [filters, page, pageSize, sortBy, sortOrder, showToast]);
  
  const fetchStats = useCallback(async () => {
    try {
      const response = await api.get('/analyzer/stats');
      setStats(response.data);
    } catch (err) {
      console.error('Failed to fetch stats:', err);
    }
  }, []);
  
  const fetchCategories = useCallback(async () => {
    try {
      const response = await api.get('/analyzer/categories');
      setCategories(response.data.categories || []);
    } catch (err) {
      console.error('Failed to fetch categories:', err);
    }
  }, []);
  
  const fetchSuppliers = useCallback(async () => {
    try {
      const response = await api.get('/analyzer/suppliers');
      setSuppliers(response.data.suppliers || []);
    } catch (err) {
      console.error('Failed to fetch suppliers:', err);
    }
  }, []);
  
  useEffect(() => {
    fetchStats();
    fetchCategories();
    fetchSuppliers();
  }, [fetchStats, fetchCategories, fetchSuppliers]);
  
  useEffect(() => {
    fetchProducts();
  }, [fetchProducts]);
  
  // Handle sorting
  const handleSort = (field) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortOrder('desc');
    }
    setPage(0); // Reset to first page
  };
  
  // Handle selection
  const handleSelectAll = (checked) => {
    if (checked) {
      setSelected(new Set(products.map(p => p.id)));
    } else {
      setSelected(new Set());
    }
  };
  
  const handleSelectOne = (id, checked) => {
    const newSelected = new Set(selected);
    if (checked) {
      newSelected.add(id);
    } else {
      newSelected.delete(id);
    }
    setSelected(newSelected);
  };
  
  // Bulk operations
  const handleBulkAnalyze = async () => {
    if (selected.size === 0) {
      showToast('Please select products to analyze', 'warning');
      return;
    }
    
    setBulkAnalyzing(true);
    try {
      const response = await api.post('/analyzer/bulk-analyze', Array.from(selected));
      showToast(`Re-analyzed ${response.data.analyzed} products`, 'success');
      fetchProducts();
      fetchStats();
      setSelected(new Set());
    } catch (err) {
      console.error('Bulk analyze failed:', err);
      showToast('Failed to re-analyze products', 'error');
    } finally {
      setBulkAnalyzing(false);
    }
  };
  
  const handleExport = async () => {
    setExporting(true);
    try {
      const filterObj = Object.fromEntries(
        Object.entries(filters).filter(([_, v]) => v !== '' && v !== null)
      );
      
      const productIds = selected.size > 0 ? Array.from(selected) : null;
      
      const response = await api.post(
        '/analyzer/export?format=csv',
        { ...filterObj, product_ids: productIds },
        { responseType: 'blob' }
      );
      
      // Download file
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `habexa_products_${new Date().toISOString().split('T')[0]}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      showToast('Export successful', 'success');
    } catch (err) {
      console.error('Export failed:', err);
      showToast('Failed to export products', 'error');
    } finally {
      setExporting(false);
    }
  };
  
  // Clear filters
  const handleClearFilters = () => {
    setFilters({
      search: '',
      category: '',
      supplier_id: '',
      min_roi: '',
      max_roi: '',
      min_margin: '',
      min_profit: '',
      profit_tier: '',
      min_est_sales: '',
      max_bsr: '',
      max_fba_sellers: '',
      is_profitable: '',
      amazon_sells: '',
      is_hazmat: ''
    });
    setPage(0);
  };
  
  // Column visibility
  const toggleColumn = (columnId) => {
    const column = ANALYZER_COLUMNS.find(c => c.id === columnId);
    if (column?.fixed) return; // Can't hide fixed columns
    
    setVisibleColumns(prev => {
      if (prev.includes(columnId)) {
        return prev.filter(id => id !== columnId);
      } else {
        return [...prev, columnId];
      }
    });
  };
  
  // Get visible columns
  const visibleColumnDefs = useMemo(() => {
    return ANALYZER_COLUMNS.filter(col => visibleColumns.includes(col.id));
  }, [visibleColumns]);
  
  // Format currency
  const formatCurrency = (value) => {
    if (value === null || value === undefined) return '—';
    return `$${parseFloat(value).toFixed(2)}`;
  };
  
  // Format percentage
  const formatPercentage = (value) => {
    if (value === null || value === undefined) return '—';
    return `${parseFloat(value).toFixed(1)}%`;
  };
  
  // Format number
  const formatNumber = (value) => {
    if (value === null || value === undefined) return '—';
    return parseInt(value).toLocaleString();
  };
  
  // Render cell content
  const renderCell = (product, column) => {
    const value = product[column.id];
    
    switch (column.type) {
      case 'checkbox':
        return (
          <Checkbox
            checked={selected.has(product.id)}
            onChange={(e) => handleSelectOne(product.id, e.target.checked)}
            size="small"
          />
        );
      
      case 'image':
        return (
          <Box
            component="img"
            src={value || '/placeholder-product.png'}
            alt={product.title}
            sx={{
              width: 50,
              height: 50,
              objectFit: 'contain',
              borderRadius: 1
            }}
            onError={(e) => {
              e.target.src = '/placeholder-product.png';
            }}
          />
        );
      
      case 'link':
        return (
          <IconButton
            size="small"
            href={value}
            target="_blank"
            rel="noopener noreferrer"
          >
            <ExternalLink size={16} />
          </IconButton>
        );
      
      case 'currency':
        return (
          <Typography
            variant="body2"
            color={column.colorCoded && value && value < 0 ? 'error' : 'text.primary'}
          >
            {formatCurrency(value)}
          </Typography>
        );
      
      case 'percentage':
        return (
          <Chip
            label={formatPercentage(value)}
            size="small"
            color={column.colorCoded ? getROIColor(value) : 'default'}
            sx={{ minWidth: 70 }}
          />
        );
      
      case 'boolean':
        return value ? (
          <CheckCircle size={16} color="success" />
        ) : (
          <X size={16} color="disabled" />
        );
      
      case 'badge':
        return (
          <Chip
            label={value || '—'}
            size="small"
            color={getProfitTierColor(value)}
          />
        );
      
      default:
        return (
          <Typography variant="body2">
            {value !== null && value !== undefined ? String(value) : '—'}
          </Typography>
        );
    }
  };
  
  return (
    <Box sx={{ p: 3, bgcolor: '#f5f5f5', minHeight: '100vh' }}>
      {/* Header */}
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h4" fontWeight={600}>
          Product Analyzer
        </Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            variant="outlined"
            startIcon={<Settings size={16} />}
            onClick={(e) => setColumnMenuAnchor(e.currentTarget)}
          >
            Columns
          </Button>
          <Button
            variant="outlined"
            startIcon={<Download size={16} />}
            onClick={handleExport}
            disabled={exporting}
          >
            {exporting ? 'Exporting...' : 'Export'}
          </Button>
          <Button
            variant="contained"
            startIcon={<RefreshCw size={16} />}
            onClick={fetchProducts}
            disabled={loading}
          >
            Refresh
          </Button>
        </Box>
      </Box>
      
      {/* Stats Cards */}
      {stats && (
        <Grid container spacing={2} sx={{ mb: 3 }}>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography variant="overline" color="text.secondary">Total Products</Typography>
                <Typography variant="h4" fontWeight={600}>{stats.total_products || 0}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography variant="overline" color="text.secondary">Profitable</Typography>
                <Typography variant="h4" fontWeight={600} color="success.main">
                  {stats.profitable_count || 0}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography variant="overline" color="text.secondary">Avg ROI</Typography>
                <Typography variant="h4" fontWeight={600} color="primary.main">
                  {formatPercentage(stats.avg_roi || 0)}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography variant="overline" color="text.secondary">Monthly Profit Potential</Typography>
                <Typography variant="h4" fontWeight={600} color="success.main">
                  {formatCurrency(stats.total_profit_potential || 0)}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}
      
      {/* Filters */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, alignItems: 'flex-end' }}>
            <TextField
              size="small"
              label="Search ASIN/Title"
              value={filters.search}
              onChange={(e) => setFilters({...filters, search: e.target.value})}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <Search size={16} />
                  </InputAdornment>
                )
              }}
              sx={{ minWidth: 200 }}
            />
            
            <FormControl size="small" sx={{ minWidth: 150 }}>
              <InputLabel>Category</InputLabel>
              <Select
                value={filters.category}
                label="Category"
                onChange={(e) => setFilters({...filters, category: e.target.value})}
              >
                <MenuItem value="">All</MenuItem>
                {categories.map(cat => (
                  <MenuItem key={cat} value={cat}>{cat}</MenuItem>
                ))}
              </Select>
            </FormControl>
            
            <FormControl size="small" sx={{ minWidth: 150 }}>
              <InputLabel>Profit Tier</InputLabel>
              <Select
                value={filters.profit_tier}
                label="Profit Tier"
                onChange={(e) => setFilters({...filters, profit_tier: e.target.value})}
              >
                <MenuItem value="">All</MenuItem>
                <MenuItem value="excellent">Excellent</MenuItem>
                <MenuItem value="good">Good</MenuItem>
                <MenuItem value="marginal">Marginal</MenuItem>
                <MenuItem value="unprofitable">Unprofitable</MenuItem>
              </Select>
            </FormControl>
            
            <TextField
              size="small"
              label="Min ROI %"
              type="number"
              value={filters.min_roi}
              onChange={(e) => setFilters({...filters, min_roi: e.target.value})}
              sx={{ width: 120 }}
            />
            
            <TextField
              size="small"
              label="Max BSR"
              type="number"
              value={filters.max_bsr}
              onChange={(e) => setFilters({...filters, max_bsr: e.target.value})}
              sx={{ width: 120 }}
            />
            
            <Button
              variant="outlined"
              startIcon={<X size={16} />}
              onClick={handleClearFilters}
            >
              Clear
            </Button>
            
            <Button
              variant="contained"
              startIcon={<Filter size={16} />}
              onClick={() => {
                setPage(0);
                fetchProducts();
              }}
            >
              Apply Filters
            </Button>
          </Box>
        </CardContent>
      </Card>
      
      {/* Bulk Actions */}
      {selected.size > 0 && (
        <Card sx={{ mb: 3, bgcolor: 'primary.light' }}>
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography variant="body1" fontWeight={600}>
                {selected.size} product{selected.size !== 1 ? 's' : ''} selected
              </Typography>
              <Box sx={{ display: 'flex', gap: 1 }}>
                <Button
                  variant="contained"
                  startIcon={<RefreshCw size={16} />}
                  onClick={handleBulkAnalyze}
                  disabled={bulkAnalyzing}
                >
                  {bulkAnalyzing ? 'Analyzing...' : 'Re-Analyze'}
                </Button>
                <Button
                  variant="outlined"
                  onClick={() => setSelected(new Set())}
                >
                  Clear Selection
                </Button>
              </Box>
            </Box>
          </CardContent>
        </Card>
      )}
      
      {/* Table */}
      <Card>
        <TableContainer>
          <Table size="small" stickyHeader>
            <TableHead>
              <TableRow>
                {visibleColumnDefs.map(column => (
                  <TableCell
                    key={column.id}
                    sx={{
                      minWidth: column.width,
                      fontWeight: 600,
                      bgcolor: 'background.paper'
                    }}
                  >
                    {column.sortable ? (
                      <Box
                        sx={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: 0.5,
                          cursor: 'pointer',
                          '&:hover': { opacity: 0.7 }
                        }}
                        onClick={() => handleSort(column.sortField || column.id)}
                      >
                        {column.label}
                        {sortBy === (column.sortField || column.id) ? (
                          sortOrder === 'asc' ? <ArrowUp size={14} /> : <ArrowDown size={14} />
                        ) : (
                          <ArrowUpDown size={14} color="disabled" />
                        )}
                      </Box>
                    ) : (
                      column.label
                    )}
                  </TableCell>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={visibleColumnDefs.length} align="center" sx={{ py: 4 }}>
                    <CircularProgress />
                  </TableCell>
                </TableRow>
              ) : products.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={visibleColumnDefs.length} align="center" sx={{ py: 4 }}>
                    <Typography color="text.secondary">No products found</Typography>
                  </TableCell>
                </TableRow>
              ) : (
                products.map(product => (
                  <TableRow
                    key={product.id}
                    sx={{
                      bgcolor: getRowColor(product.roi, product.profit_tier),
                      '&:hover': { bgcolor: 'action.hover' }
                    }}
                  >
                    {visibleColumnDefs.map(column => (
                      <TableCell key={column.id}>
                        {renderCell(product, column)}
                      </TableCell>
                    ))}
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
        
        <TablePagination
          component="div"
          count={total}
          page={page}
          onPageChange={(e, newPage) => setPage(newPage)}
          rowsPerPage={pageSize}
          onRowsPerPageChange={(e) => {
            setPageSize(parseInt(e.target.value, 10));
            setPage(0);
          }}
          rowsPerPageOptions={[25, 50, 100, 200]}
        />
      </Card>
      
      {/* Column Visibility Menu */}
      <Menu
        anchorEl={columnMenuAnchor}
        open={Boolean(columnMenuAnchor)}
        onClose={() => setColumnMenuAnchor(null)}
      >
        {ANALYZER_COLUMNS.map(column => (
          <MenuItem
            key={column.id}
            onClick={() => {
              if (!column.fixed) {
                toggleColumn(column.id);
              }
            }}
            disabled={column.fixed}
          >
            <Checkbox
              checked={visibleColumns.includes(column.id)}
              size="small"
              sx={{ mr: 1 }}
            />
            {column.label}
          </MenuItem>
        ))}
      </Menu>
    </Box>
  );
}

