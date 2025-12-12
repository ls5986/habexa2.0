import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  IconButton,
  Checkbox,
  Chip,
  Avatar,
  Tooltip,
  Menu,
  MenuItem as MenuItemMUI,
  ListItemText,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TableSortLabel,
  TablePagination,
  Card,
  CardContent,
  Grid,
  Alert,
  Snackbar,
} from '@mui/material';
import {
  FilterList,
  Clear,
  Download,
  Refresh,
  ViewColumn,
  ContentCopy,
  OpenInNew,
  CheckCircle,
  Cancel,
  TrendingUp,
  TrendingDown,
  Star,
} from '@mui/icons-material';
import { analyzerColumns, defaultVisibleColumns, columnGroups, getColorForValue } from '../config/analyzerColumns';
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export default function Analyzer() {
  // State management
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    total_products: 0,
    profitable_count: 0,
    avg_roi: 0,
    total_monthly_profit: 0,
  });
  
  // Table state
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  const [orderBy, setOrderBy] = useState('roi_percentage');
  const [order, setOrder] = useState('desc');
  const [visibleColumns, setVisibleColumns] = useState(defaultVisibleColumns);
  const [selected, setSelected] = useState([]);
  
  // Filter state
  const [filters, setFilters] = useState({
    search: '',
    minRoi: '',
    maxRoi: '',
    profitTier: '',
    category: '',
    supplier: '',
    isProfitable: '',
    amazonSells: '',
    isHazmat: '',
  });
  
  // UI state
  const [columnMenuAnchor, setColumnMenuAnchor] = useState(null);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'info' });
  const [categories, setCategories] = useState([]);
  const [suppliers, setSuppliers] = useState([]);

  // Fetch data on mount and filter changes
  useEffect(() => {
    fetchProducts();
    fetchStats();
    fetchCategories();
    fetchSuppliers();
  }, [page, rowsPerPage, orderBy, order]);

  const fetchProducts = async () => {
    setLoading(true);
    try {
      const params = {
        skip: page * rowsPerPage,
        limit: rowsPerPage,
        order_by: orderBy,
        order_direction: order,
        ...buildFilterParams(),
      };

      const response = await axios.get(`${API_BASE_URL}/api/analyzer/products`, {
        params,
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      });

      setProducts(response.data.products || []);
    } catch (error) {
      console.error('Error fetching products:', error);
      showSnackbar('Error loading products', 'error');
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const params = buildFilterParams();
      const response = await axios.get(`${API_BASE_URL}/api/analyzer/stats`, {
        params,
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      });
      setStats(response.data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  const fetchCategories = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/analyzer/categories`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      });
      setCategories(response.data.categories || []);
    } catch (error) {
      console.error('Error fetching categories:', error);
    }
  };

  const fetchSuppliers = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/analyzer/suppliers`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      });
      setSuppliers(response.data.suppliers || []);
    } catch (error) {
      console.error('Error fetching suppliers:', error);
    }
  };

  const buildFilterParams = () => {
    const params = {};
    if (filters.search) params.search = filters.search;
    if (filters.minRoi) params.min_roi = parseFloat(filters.minRoi);
    if (filters.maxRoi) params.max_roi = parseFloat(filters.maxRoi);
    if (filters.profitTier) params.profit_tier = filters.profitTier;
    if (filters.category) params.category = filters.category;
    if (filters.supplier) params.supplier = filters.supplier;
    if (filters.isProfitable !== '') params.is_profitable = filters.isProfitable === 'true';
    if (filters.amazonSells !== '') params.amazon_sells = filters.amazonSells === 'true';
    if (filters.isHazmat !== '') params.is_hazmat = filters.isHazmat === 'true';
    return params;
  };

  const handleApplyFilters = () => {
    setPage(0);
    fetchProducts();
    fetchStats();
  };

  const handleClearFilters = () => {
    setFilters({
      search: '',
      minRoi: '',
      maxRoi: '',
      profitTier: '',
      category: '',
      supplier: '',
      isProfitable: '',
      amazonSells: '',
      isHazmat: '',
    });
    setPage(0);
    setTimeout(() => {
      fetchProducts();
      fetchStats();
    }, 100);
  };

  const handleSort = (columnId) => {
    const isAsc = orderBy === columnId && order === 'asc';
    setOrder(isAsc ? 'desc' : 'asc');
    setOrderBy(columnId);
  };

  const handleSelectAll = (event) => {
    if (event.target.checked) {
      setSelected(products.map(p => p.id));
    } else {
      setSelected([]);
    }
  };

  const handleSelectOne = (productId) => {
    const selectedIndex = selected.indexOf(productId);
    let newSelected = [];

    if (selectedIndex === -1) {
      newSelected = [...selected, productId];
    } else {
      newSelected = selected.filter(id => id !== productId);
    }

    setSelected(newSelected);
  };

  const handleBulkAnalyze = async () => {
    if (selected.length === 0) {
      showSnackbar('Please select products first', 'warning');
      return;
    }

    try {
      await axios.post(
        `${API_BASE_URL}/api/analyzer/bulk-analyze`,
        { product_ids: selected },
        { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } }
      );
      
      showSnackbar(`Re-analyzed ${selected.length} products`, 'success');
      setSelected([]);
      fetchProducts();
      fetchStats();
    } catch (error) {
      console.error('Error bulk analyzing:', error);
      showSnackbar('Error re-analyzing products', 'error');
    }
  };

  const handleExportCSV = async () => {
    try {
      const params = buildFilterParams();
      const response = await axios.get(`${API_BASE_URL}/api/analyzer/export`, {
        params,
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
        responseType: 'blob',
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `analyzer_export_${new Date().toISOString().split('T')[0]}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      showSnackbar('CSV exported successfully', 'success');
    } catch (error) {
      console.error('Error exporting CSV:', error);
      showSnackbar('Error exporting data', 'error');
    }
  };

  const handleCopyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    showSnackbar('Copied to clipboard', 'success');
  };

  const showSnackbar = (message, severity = 'info') => {
    setSnackbar({ open: true, message, severity });
  };

  const renderCellValue = (column, product) => {
    const value = product[column.id];

    // Handle null/undefined
    if (value === null || value === undefined) {
      return <Typography variant="body2" color="text.disabled">-</Typography>;
    }

    // Checkbox column
    if (column.type === 'checkbox') {
      return (
        <Checkbox
          checked={selected.indexOf(product.id) !== -1}
          onChange={() => handleSelectOne(product.id)}
        />
      );
    }

    // Image column
    if (column.type === 'image') {
      return (
        <Avatar
          src={product.image_url}
          alt={product.title}
          variant="rounded"
          sx={{ width: 60, height: 60 }}
        />
      );
    }

    // Link column (Amazon)
    if (column.type === 'link' && column.id === 'amazon_link') {
      return (
        <IconButton
          size="small"
          color="primary"
          href={`https://www.amazon.com/dp/${product.asin}`}
          target="_blank"
        >
          <OpenInNew />
        </IconButton>
      );
    }

    // Currency
    if (column.type === 'currency') {
      const colorConfig = column.colorCoded ? getColorForValue('profit', value) : null;
      return (
        <Typography
          variant="body2"
          fontWeight={column.colorCoded ? 600 : 400}
          sx={{ color: colorConfig?.color }}
        >
          ${value.toFixed(2)}
        </Typography>
      );
    }

    // Percentage
    if (column.type === 'percentage') {
      const decimals = column.decimals || 1;
      const colorConfig = column.colorCoded ? getColorForValue(column.id.replace('_percentage', ''), value) : null;
      return (
        <Typography
          variant="body2"
          fontWeight={column.colorCoded ? 600 : 400}
          sx={{ color: colorConfig?.color }}
        >
          {value.toFixed(decimals)}%
        </Typography>
      );
    }

    // Number with comma formatting
    if (column.type === 'number' && column.format === 'comma') {
      return (
        <Typography variant="body2">
          {value.toLocaleString()}
        </Typography>
      );
    }

    // Number with decimals
    if (column.type === 'number' && column.decimals) {
      return (
        <Typography variant="body2">
          {value.toFixed(column.decimals)}
        </Typography>
      );
    }

    // Number
    if (column.type === 'number') {
      return <Typography variant="body2">{value}</Typography>;
    }

    // Boolean
    if (column.type === 'boolean') {
      return value ? (
        <CheckCircle color="success" fontSize="small" />
      ) : (
        <Cancel color="error" fontSize="small" />
      );
    }

    // Badge (profit tier)
    if (column.type === 'badge') {
      const tierColors = {
        excellent: 'success',
        good: 'warning',
        marginal: 'info',
        unprofitable: 'error',
      };
      return (
        <Chip
          label={value}
          color={tierColors[value] || 'default'}
          size="small"
        />
      );
    }

    // Rating
    if (column.type === 'rating') {
      return (
        <Box display="flex" alignItems="center" gap={0.5}>
          <Star fontSize="small" color="warning" />
          <Typography variant="body2">{value.toFixed(1)}</Typography>
        </Box>
      );
    }

    // DateTime
    if (column.type === 'datetime') {
      return (
        <Typography variant="body2" fontSize="0.75rem">
          {new Date(value).toLocaleDateString()}
        </Typography>
      );
    }

    // Text (with copyable option)
    if (column.copyable) {
      return (
        <Box display="flex" alignItems="center" gap={0.5}>
          <Typography variant="body2" fontFamily={column.id === 'asin' ? 'monospace' : 'inherit'}>
            {value}
          </Typography>
          <IconButton size="small" onClick={() => handleCopyToClipboard(value)}>
            <ContentCopy fontSize="small" />
          </IconButton>
        </Box>
      );
    }

    // Default text
    return (
      <Typography
        variant="body2"
        sx={{
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
          maxWidth: column.width - 32,
        }}
      >
        {value}
      </Typography>
    );
  };

  const getRowColor = (product) => {
    if (!product.roi_percentage) return 'transparent';
    const colorConfig = getColorForValue('roi', product.roi_percentage);
    return colorConfig?.bgColor || 'transparent';
  };

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" fontWeight={600}>
          Product Analyzer
        </Typography>
        <Box display="flex" gap={2}>
          <Button
            variant="outlined"
            startIcon={<ViewColumn />}
            onClick={(e) => setColumnMenuAnchor(e.currentTarget)}
          >
            Columns
          </Button>
          <Button
            variant="outlined"
            startIcon={<Download />}
            onClick={handleExportCSV}
          >
            Export CSV
          </Button>
          <Button
            variant="contained"
            startIcon={<Refresh />}
            onClick={() => {
              fetchProducts();
              fetchStats();
            }}
          >
            Refresh
          </Button>
        </Box>
      </Box>

      {/* Stats Cards */}
      <Grid container spacing={3} mb={3}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Total Products
              </Typography>
              <Typography variant="h4" fontWeight={600}>
                {stats.total_products}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Profitable Deals
              </Typography>
              <Typography variant="h4" fontWeight={600} color="success.main">
                {stats.profitable_count}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Average ROI
              </Typography>
              <Typography variant="h4" fontWeight={600} color="primary">
                {stats.avg_roi?.toFixed(1)}%
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Monthly Profit
              </Typography>
              <Typography variant="h4" fontWeight={600} color="success.main">
                ${stats.total_monthly_profit?.toLocaleString()}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Filters */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} md={3}>
            <TextField
              fullWidth
              size="small"
              label="Search ASIN"
              value={filters.search}
              onChange={(e) => setFilters({ ...filters, search: e.target.value })}
            />
          </Grid>
          <Grid item xs={12} md={2}>
            <TextField
              fullWidth
              size="small"
              label="Min ROI %"
              type="number"
              value={filters.minRoi}
              onChange={(e) => setFilters({ ...filters, minRoi: e.target.value })}
            />
          </Grid>
          <Grid item xs={12} md={2}>
            <FormControl fullWidth size="small">
              <InputLabel>Profit Tier</InputLabel>
              <Select
                value={filters.profitTier}
                onChange={(e) => setFilters({ ...filters, profitTier: e.target.value })}
                label="Profit Tier"
              >
                <MenuItem value="">All</MenuItem>
                <MenuItem value="excellent">Excellent (50%+)</MenuItem>
                <MenuItem value="good">Good (30-50%)</MenuItem>
                <MenuItem value="marginal">Marginal (15-30%)</MenuItem>
                <MenuItem value="unprofitable">Unprofitable (&lt;15%)</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} md={2}>
            <FormControl fullWidth size="small">
              <InputLabel>Category</InputLabel>
              <Select
                value={filters.category}
                onChange={(e) => setFilters({ ...filters, category: e.target.value })}
                label="Category"
              >
                <MenuItem value="">All</MenuItem>
                {categories.map((cat) => (
                  <MenuItem key={cat} value={cat}>
                    {cat}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} md={3}>
            <Box display="flex" gap={1}>
              <Button
                fullWidth
                variant="contained"
                startIcon={<FilterList />}
                onClick={handleApplyFilters}
              >
                Apply Filters
              </Button>
              <Button
                variant="outlined"
                startIcon={<Clear />}
                onClick={handleClearFilters}
              >
                Clear
              </Button>
            </Box>
          </Grid>
        </Grid>
      </Paper>

      {/* Selection Actions */}
      {selected.length > 0 && (
        <Alert severity="info" sx={{ mb: 2 }}>
          <Box display="flex" justifyContent="space-between" alignItems="center">
            <Typography>
              {selected.length} product{selected.length > 1 ? 's' : ''} selected
            </Typography>
            <Button
              variant="contained"
              size="small"
              startIcon={<Refresh />}
              onClick={handleBulkAnalyze}
            >
              Re-Analyze Selected
            </Button>
          </Box>
        </Alert>
      )}

      {/* Scrollable Table */}
      <Paper sx={{ width: '100%', overflow: 'hidden' }}>
        <TableContainer sx={{ maxHeight: 'calc(100vh - 500px)', overflowX: 'auto' }}>
          <Table stickyHeader size="small">
            <TableHead>
              <TableRow>
                {analyzerColumns
                  .filter((col) => visibleColumns.includes(col.id))
                  .map((column) => (
                    <TableCell
                      key={column.id}
                      align={column.type === 'number' || column.type === 'currency' || column.type === 'percentage' ? 'right' : 'left'}
                      sx={{
                        minWidth: column.width,
                        maxWidth: column.width,
                        fontWeight: 600,
                        bgcolor: 'background.default',
                        position: column.sticky ? 'sticky' : 'relative',
                        left: column.sticky ? 0 : 'auto',
                        zIndex: column.sticky ? 3 : 1,
                      }}
                    >
                      {column.sortable ? (
                        <TableSortLabel
                          active={orderBy === column.id}
                          direction={orderBy === column.id ? order : 'asc'}
                          onClick={() => handleSort(column.id)}
                        >
                          {column.label}
                        </TableSortLabel>
                      ) : column.type === 'checkbox' ? (
                        <Checkbox
                          indeterminate={selected.length > 0 && selected.length < products.length}
                          checked={products.length > 0 && selected.length === products.length}
                          onChange={handleSelectAll}
                        />
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
                  <TableCell colSpan={visibleColumns.length} align="center">
                    <Typography>Loading...</Typography>
                  </TableCell>
                </TableRow>
              ) : products.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={visibleColumns.length} align="center">
                    <Typography>No products found</Typography>
                  </TableCell>
                </TableRow>
              ) : (
                products.map((product) => (
                  <TableRow
                    key={product.id}
                    sx={{
                      bgcolor: getRowColor(product),
                      '&:hover': { bgcolor: 'action.hover' },
                    }}
                  >
                    {analyzerColumns
                      .filter((col) => visibleColumns.includes(col.id))
                      .map((column) => (
                        <TableCell
                          key={column.id}
                          align={column.type === 'number' || column.type === 'currency' || column.type === 'percentage' ? 'right' : 'left'}
                          sx={{
                            minWidth: column.width,
                            maxWidth: column.width,
                            position: column.sticky ? 'sticky' : 'relative',
                            left: column.sticky ? 0 : 'auto',
                            bgcolor: column.sticky ? 'inherit' : 'transparent',
                            zIndex: column.sticky ? 2 : 1,
                          }}
                        >
                          {renderCellValue(column, product)}
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
          count={stats.total_products}
          page={page}
          onPageChange={(e, newPage) => setPage(newPage)}
          rowsPerPage={rowsPerPage}
          onRowsPerPageChange={(e) => {
            setRowsPerPage(parseInt(e.target.value, 10));
            setPage(0);
          }}
          rowsPerPageOptions={[25, 50, 100]}
        />
      </Paper>

      {/* Column Visibility Menu */}
      <Menu
        anchorEl={columnMenuAnchor}
        open={Boolean(columnMenuAnchor)}
        onClose={() => setColumnMenuAnchor(null)}
        PaperProps={{ sx: { maxHeight: 500, width: 300 } }}
      >
        {Object.entries(columnGroups).map(([groupKey, group]) => (
          <Box key={groupKey}>
            <Typography variant="caption" sx={{ px: 2, py: 1, fontWeight: 600, color: 'text.secondary' }}>
              {group.label}
            </Typography>
            {group.columns.map((colId) => {
              const column = analyzerColumns.find(c => c.id === colId);
              if (!column || column.id === 'select') return null;
              
              return (
                <MenuItemMUI
                  key={colId}
                  onClick={() => {
                    if (visibleColumns.includes(colId)) {
                      setVisibleColumns(visibleColumns.filter(id => id !== colId));
                    } else {
                      setVisibleColumns([...visibleColumns, colId]);
                    }
                  }}
                >
                  <Checkbox checked={visibleColumns.includes(colId)} />
                  <ListItemText primary={column.label} />
                </MenuItemMUI>
              );
            })}
          </Box>
        ))}
      </Menu>

      {/* Snackbar */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert severity={snackbar.severity} onClose={() => setSnackbar({ ...snackbar, open: false })}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}
