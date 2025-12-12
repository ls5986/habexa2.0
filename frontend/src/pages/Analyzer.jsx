import React, { useState, useEffect, useCallback } from 'react';
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
  CircularProgress,
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
  ShoppingCart,
} from '@mui/icons-material';
import { analyzerColumns, defaultVisibleColumns, columnGroups, getColorForValue } from '../config/analyzerColumns';
import api from '../services/api';
import { useToast } from '../context/ToastContext';

export default function Analyzer() {
  // Use the new Enhanced Analyzer component
  return <EnhancedAnalyzer />;
}

// Legacy Analyzer component (kept for reference)
export function LegacyAnalyzer() {
  // State management
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    total_products: 0,
    profitable_count: 0,
    avg_roi: 0,
    total_profit_potential: 0,
  });
  
  // Table state
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  const [orderBy, setOrderBy] = useState('roi_percentage');
  const [order, setOrder] = useState('desc');
  const [visibleColumns, setVisibleColumns] = useState(defaultVisibleColumns);
  const [selected, setSelected] = useState([]);
  const [total, setTotal] = useState(0);
  
  // Filter state
  const [filters, setFilters] = useState({
    search: '',
    min_roi: '',
    max_roi: '',
    profit_tier: '',
    category: '',
    supplier_id: '',
    is_profitable: '',
    amazon_sells: '',
    is_hazmat: '',
  });
  
  // UI state
  const [columnMenuAnchor, setColumnMenuAnchor] = useState(null);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'info' });
  const [categories, setCategories] = useState([]);
  const [suppliers, setSuppliers] = useState([]);
  const [bulkAnalyzing, setBulkAnalyzing] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [createBuyListDialogOpen, setCreateBuyListDialogOpen] = useState(false);
  const [buyListName, setBuyListName] = useState('');
  const [creatingBuyList, setCreatingBuyList] = useState(false);

  const { showToast } = useToast();

  // Fetch data on mount and filter changes
  useEffect(() => {
    fetchProducts();
    fetchStats();
    fetchCategories();
    fetchSuppliers();
  }, [page, rowsPerPage, orderBy, order]);

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
      if (filterObj.is_profitable !== '') filterObj.is_profitable = filterObj.is_profitable === 'true';
      if (filterObj.amazon_sells !== '') filterObj.amazon_sells = filterObj.amazon_sells === 'true';
      if (filterObj.is_hazmat !== '') filterObj.is_hazmat = filterObj.is_hazmat === 'true';
      
      const response = await api.post(
        `/analyzer/products?page=${page + 1}&page_size=${rowsPerPage}&sort_by=${orderBy}&sort_order=${order}`,
        filterObj
      );
      
      setProducts(response.data.products || []);
      setTotal(response.data.total || 0);
    } catch (error) {
      console.error('Error fetching products:', error);
      showToast('Error loading products', 'error');
    } finally {
      setLoading(false);
    }
  }, [filters, page, rowsPerPage, orderBy, order, showToast]);

  const fetchStats = useCallback(async () => {
    try {
      const response = await api.get('/analyzer/stats');
      setStats(response.data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  }, []);

  const fetchCategories = useCallback(async () => {
    try {
      const response = await api.get('/analyzer/categories');
      setCategories(response.data.categories || []);
    } catch (error) {
      console.error('Error fetching categories:', error);
    }
  }, []);

  const fetchSuppliers = useCallback(async () => {
    try {
      const response = await api.get('/analyzer/suppliers');
      setSuppliers(response.data.suppliers || []);
    } catch (error) {
      console.error('Error fetching suppliers:', error);
    }
  }, []);

  const handleApplyFilters = () => {
    setPage(0);
    fetchProducts();
    fetchStats();
  };

  const handleClearFilters = () => {
    setFilters({
      search: '',
      min_roi: '',
      max_roi: '',
      profit_tier: '',
      category: '',
      supplier_id: '',
      is_profitable: '',
      amazon_sells: '',
      is_hazmat: '',
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
      showToast('Please select products first', 'warning');
      return;
    }

    setBulkAnalyzing(true);
    try {
      const response = await api.post('/analyzer/bulk-analyze', selected);
      showToast(`Re-analyzed ${response.data.analyzed} products`, 'success');
      setSelected([]);
      fetchProducts();
      fetchStats();
    } catch (error) {
      console.error('Error bulk analyzing:', error);
      showToast('Error re-analyzing products', 'error');
    } finally {
      setBulkAnalyzing(false);
    }
  };

  const handleCreateBuyList = async () => {
    if (selected.length === 0) {
      showToast('Please select products first', 'warning');
      return;
    }

    if (!buyListName.trim()) {
      showToast('Please enter a buy list name', 'warning');
      return;
    }

    setCreatingBuyList(true);
    try {
      const response = await api.post('/buy-lists/create-from-products', {
        product_ids: selected,
        name: buyListName.trim()
      });
      
      showToast(`Created buy list "${buyListName}" with ${response.data.added_items} products`, 'success');
      setCreateBuyListDialogOpen(false);
      setBuyListName('');
      setSelected([]);
      
      // Navigate to buy list detail page
      if (response.data.buy_list?.id) {
        window.location.href = `/buy-lists/${response.data.buy_list.id}`;
      }
    } catch (error) {
      console.error('Error creating buy list:', error);
      showToast('Error creating buy list', 'error');
    } finally {
      setCreatingBuyList(false);
    }
  };

  const handleExportCSV = async () => {
    setExporting(true);
    try {
      const filterObj = Object.fromEntries(
        Object.entries(filters).filter(([_, v]) => v !== '' && v !== null)
      );
      
      const productIds = selected.length > 0 ? selected : null;
      
      const response = await api.post(
        '/analyzer/export?format=csv',
        { ...filterObj, product_ids: productIds },
        { responseType: 'blob' }
      );

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `habexa_products_${new Date().toISOString().split('T')[0]}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      showToast('CSV exported successfully', 'success');
    } catch (error) {
      console.error('Error exporting CSV:', error);
      showToast('Error exporting data', 'error');
    } finally {
      setExporting(false);
    }
  };

  const handleCopyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    showToast('Copied to clipboard', 'success');
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
          size="small"
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
          onError={(e) => {
            e.target.src = '/placeholder-product.png';
          }}
        />
      );
    }

    // Link column (Amazon)
    if (column.type === 'link' && column.id === 'amazon_link') {
      return (
        <IconButton
          size="small"
          color="primary"
          href={product.amazon_link || `https://www.amazon.com/dp/${product.asin}`}
          target="_blank"
          rel="noopener noreferrer"
        >
          <OpenInNew fontSize="small" />
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
          ${typeof value === 'number' ? value.toFixed(2) : value}
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
          {typeof value === 'number' ? value.toFixed(decimals) : value}%
        </Typography>
      );
    }

    // Number with comma formatting
    if (column.type === 'number' && column.format === 'comma') {
      return (
        <Typography variant="body2">
          {typeof value === 'number' ? value.toLocaleString() : value}
        </Typography>
      );
    }

    // Number with decimals
    if (column.type === 'number' && column.decimals) {
      return (
        <Typography variant="body2">
          {typeof value === 'number' ? value.toFixed(column.decimals) : value}
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
          <Typography variant="body2">{typeof value === 'number' ? value.toFixed(1) : value}</Typography>
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
    const roi = product.roi_percentage || product.roi;
    if (!roi && roi !== 0) return 'transparent';
    const colorConfig = getColorForValue('roi', roi);
    return colorConfig?.bgColor || 'transparent';
  };

  return (
    <Box sx={{ p: 3, bgcolor: '#f5f5f5', minHeight: '100vh' }}>
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
            disabled={exporting}
          >
            {exporting ? 'Exporting...' : 'Export CSV'}
          </Button>
          <Button
            variant="contained"
            startIcon={<Refresh />}
            onClick={() => {
              fetchProducts();
              fetchStats();
            }}
            disabled={loading}
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
                {stats.total_products || 0}
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
                {stats.profitable_count || 0}
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
              <Typography variant="h4" fontWeight={600} color="primary.main">
                {stats.avg_roi ? `${stats.avg_roi.toFixed(1)}%` : '0%'}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Monthly Profit Potential
              </Typography>
              <Typography variant="h4" fontWeight={600} color="success.main">
                ${stats.total_profit_potential ? stats.total_profit_potential.toLocaleString() : '0'}
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
              label="Search ASIN/Title"
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
              value={filters.min_roi}
              onChange={(e) => setFilters({ ...filters, min_roi: e.target.value })}
            />
          </Grid>
          <Grid item xs={12} md={2}>
            <FormControl fullWidth size="small">
              <InputLabel>Profit Tier</InputLabel>
              <Select
                value={filters.profit_tier}
                onChange={(e) => setFilters({ ...filters, profit_tier: e.target.value })}
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
            <Box display="flex" gap={1}>
              <Button
                variant="contained"
                size="small"
                startIcon={<ShoppingCart />}
                onClick={() => setCreateBuyListDialogOpen(true)}
                color="primary"
              >
                Create Buy List
              </Button>
              <Button
                variant="outlined"
                size="small"
                startIcon={<Refresh />}
                onClick={handleBulkAnalyze}
                disabled={bulkAnalyzing}
              >
                {bulkAnalyzing ? 'Analyzing...' : 'Re-Analyze'}
              </Button>
            </Box>
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
                          size="small"
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
                  <TableCell colSpan={visibleColumns.length} align="center" sx={{ py: 4 }}>
                    <CircularProgress />
                  </TableCell>
                </TableRow>
              ) : products.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={visibleColumns.length} align="center" sx={{ py: 4 }}>
                    <Typography color="text.secondary">No products found</Typography>
                  </TableCell>
                </TableRow>
              ) : (
                products.map((product) => (
                  <TableRow
                    key={product.id}
                    sx={{
                      bgcolor: getRowColor(product),
                      '&:hover': { opacity: 0.8 },
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
          count={total || stats.total_products}
          page={page}
          onPageChange={(e, newPage) => setPage(newPage)}
          rowsPerPage={rowsPerPage}
          onRowsPerPageChange={(e) => {
            setRowsPerPage(parseInt(e.target.value, 10));
            setPage(0);
          }}
          rowsPerPageOptions={[25, 50, 100, 200]}
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

      {/* Create Buy List Dialog */}
      <Dialog
        open={createBuyListDialogOpen}
        onClose={() => {
          setCreateBuyListDialogOpen(false);
          setBuyListName('');
        }}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Create Buy List</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Create a new buy list with {selected.length} selected product{selected.length > 1 ? 's' : ''}.
          </Typography>
          <TextField
            autoFocus
            fullWidth
            label="Buy List Name"
            value={buyListName}
            onChange={(e) => setBuyListName(e.target.value)}
            placeholder="e.g., KEHE Order #47 - Dec 2025"
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => {
              setCreateBuyListDialogOpen(false);
              setBuyListName('');
            }}
            disabled={creatingBuyList}
          >
            Cancel
          </Button>
          <Button
            onClick={handleCreateBuyList}
            variant="contained"
            disabled={creatingBuyList || !buyListName.trim()}
            startIcon={<ShoppingCart />}
          >
            {creatingBuyList ? 'Creating...' : 'Create Buy List'}
          </Button>
        </DialogActions>
      </Dialog>

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
