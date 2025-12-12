import React, { useState, useEffect, useMemo } from 'react';
import {
  Box,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Checkbox,
  Typography,
  Stack,
  Chip,
  LinearProgress,
  Alert,
  IconButton,
  Tooltip,
  alpha
} from '@mui/material';
import FilterListIcon from '@mui/icons-material/FilterList';
import ViewColumnIcon from '@mui/icons-material/ViewColumn';
import FileDownloadIcon from '@mui/icons-material/FileDownload';
import RefreshIcon from '@mui/icons-material/Refresh';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import LocalOfferIcon from '@mui/icons-material/LocalOffer';
import InventoryIcon from '@mui/icons-material/Inventory';
import WarningIcon from '@mui/icons-material/Warning';
import ClearIcon from '@mui/icons-material/Clear';

import AnalyzerTableRow from './AnalyzerTableRow';
import AnalyzerBulkActions from './AnalyzerBulkActions';
import AnalyzerFilters from './AnalyzerFilters';
import AnalyzerSupplierSwitcher from './AnalyzerSupplierSwitcher';
import AnalyzerColumnMenu from './AnalyzerColumnMenu';
import { analyzerColumns, defaultVisibleColumns, getColorForValue } from '../../config/analyzerColumns';
import api from '../../services/api';
import './analyzer.css';

export default function EnhancedAnalyzer() {
  // ============================================
  // STATE MANAGEMENT
  // ============================================
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Selection
  const [selectedProducts, setSelectedProducts] = useState(new Set());
  const [selectAll, setSelectAll] = useState(false);
  
  // Filtering
  const [currentSupplier, setCurrentSupplier] = useState('all');
  const [filters, setFilters] = useState({
    search: '',
    roi: { min: null, max: null },
    profit: { min: null, max: null },
    pack_size: { min: null, max: null },
    profit_tier: [],
    has_promo: null,
    in_stock: null
  });
  const [showFilters, setShowFilters] = useState(false);
  
  // Column visibility
  const [visibleColumns, setVisibleColumns] = useState(defaultVisibleColumns);
  const [showColumnMenu, setShowColumnMenu] = useState(false);
  
  // Sorting
  const [sortBy, setSortBy] = useState('roi');
  const [sortDirection, setSortDirection] = useState('desc');

  // ============================================
  // DATA FETCHING
  // ============================================
  useEffect(() => {
    fetchProducts();
  }, [currentSupplier]);

  const fetchProducts = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const queryParams = new URLSearchParams();
      if (currentSupplier !== 'all') {
        queryParams.append('supplier_id', currentSupplier);
      }
      
      const response = await api.get(`/products?${queryParams}`);
      setProducts(response.data?.products || response.data || []);
      
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to fetch products');
    } finally {
      setLoading(false);
    }
  };

  // ============================================
  // FILTERING & SORTING
  // ============================================
  const filteredProducts = useMemo(() => {
    let filtered = [...products];

    // Text search
    if (filters.search) {
      const searchLower = filters.search.toLowerCase();
      filtered = filtered.filter(p => 
        p.title?.toLowerCase().includes(searchLower) ||
        p.asin?.toLowerCase().includes(searchLower) ||
        p.supplier_sku?.toLowerCase().includes(searchLower)
      );
    }

    // ROI filter
    if (filters.roi.min !== null) {
      filtered = filtered.filter(p => (p.roi || p.roi_percentage || 0) >= filters.roi.min);
    }
    if (filters.roi.max !== null) {
      filtered = filtered.filter(p => (p.roi || p.roi_percentage || 0) <= filters.roi.max);
    }

    // Profit filter
    if (filters.profit.min !== null) {
      filtered = filtered.filter(p => (p.profit || p.profit_amount || 0) >= filters.profit.min);
    }
    if (filters.profit.max !== null) {
      filtered = filtered.filter(p => (p.profit || p.profit_amount || 0) <= filters.profit.max);
    }

    // Pack size filter
    if (filters.pack_size.min) {
      filtered = filtered.filter(p => (p.pack_size || 1) >= filters.pack_size.min);
    }
    if (filters.pack_size.max) {
      filtered = filtered.filter(p => (p.pack_size || 1) <= filters.pack_size.max);
    }

    // Profit tier filter
    if (filters.profit_tier.length > 0) {
      filtered = filtered.filter(p => {
        const tier = getProfitTier(p.roi || p.roi_percentage || 0);
        return filters.profit_tier.includes(tier.toLowerCase());
      });
    }

    // Boolean filters
    if (filters.has_promo !== null) {
      filtered = filtered.filter(p => p.has_promo === filters.has_promo);
    }
    if (filters.in_stock !== null) {
      filtered = filtered.filter(p => (p.in_stock || p.amazon_in_stock) === filters.in_stock);
    }

    // Sort
    filtered.sort((a, b) => {
      let aVal = a[sortBy];
      let bVal = b[sortBy];
      
      // Handle nested values
      if (sortBy === 'wholesale_cost' || sortBy === 'buy_cost' || sortBy === 'pack_size') {
        aVal = a.product_sources?.[0]?.[sortBy] || aVal;
        bVal = b.product_sources?.[0]?.[sortBy] || bVal;
      }
      
      if (typeof aVal === 'string') {
        aVal = aVal?.toLowerCase() || '';
        bVal = bVal?.toLowerCase() || '';
      }
      
      if (sortDirection === 'asc') {
        return aVal > bVal ? 1 : -1;
      } else {
        return aVal < bVal ? 1 : -1;
      }
    });

    return filtered;
  }, [products, filters, sortBy, sortDirection]);

  // ============================================
  // SELECTION HANDLERS
  // ============================================
  const handleSelectAll = (checked) => {
    if (checked) {
      setSelectedProducts(new Set(filteredProducts.map(p => p.id)));
      setSelectAll(true);
    } else {
      setSelectedProducts(new Set());
      setSelectAll(false);
    }
  };

  const handleSelectProduct = (productId, checked) => {
    const newSelected = new Set(selectedProducts);
    if (checked) {
      newSelected.add(productId);
    } else {
      newSelected.delete(productId);
    }
    setSelectedProducts(newSelected);
    setSelectAll(newSelected.size === filteredProducts.length && filteredProducts.length > 0);
  };

  // ============================================
  // INLINE EDIT HANDLERS
  // ============================================
  const handleFieldUpdate = async (productId, field, value) => {
    try {
      // Update backend - check if it's a product_sources field
      if (['wholesale_cost', 'buy_cost', 'pack_size'].includes(field)) {
        // Update product_sources table
        const product = products.find(p => p.id === productId);
        const productSource = product?.product_sources?.[0];
        
        if (productSource?.id) {
          await api.patch(`/product-sources/${productSource.id}`, { [field]: value });
        } else {
          // Create product_source if it doesn't exist
          await api.post('/product-sources', {
            product_id: productId,
            [field]: value
          });
        }
      } else {
        // Update products table
        await api.patch(`/products/${productId}`, { [field]: value });
      }

      // Update local state
      setProducts(prev => prev.map(p => {
        if (p.id === productId) {
          if (['wholesale_cost', 'buy_cost', 'pack_size'].includes(field)) {
            return {
              ...p,
              product_sources: [{
                ...(p.product_sources?.[0] || {}),
                [field]: value
              }]
            };
          }
          return { ...p, [field]: value };
        }
        return p;
      }));

    } catch (err) {
      console.error('Field update failed:', err);
      alert('Failed to update field');
    }
  };

  // ============================================
  // BULK ACTIONS
  // ============================================
  const handleBulkAddToOrder = async (productIds) => {
    try {
      // Create buy list from selected products
      const response = await api.post('/buy-lists/create-from-products', {
        product_ids: productIds,
        name: `Buy List - ${new Date().toLocaleDateString()}`
      });
      
      if (response.data?.buy_list_id) {
        // Navigate to buy list or show success
        window.location.href = `/buy-lists/${response.data.buy_list_id}`;
      }
    } catch (err) {
      console.error('Bulk add to order failed:', err);
      alert('Failed to create buy list');
    }
  };
  
  const handleBulkUpdateCosts = async (productIds, updates) => {
    try {
      // Get product sources for these products
      const productSourceUpdates = [];
      
      for (const productId of productIds) {
        const product = products.find(p => p.id === productId);
        const productSource = product?.product_sources?.[0];
        
        if (productSource?.id) {
          const updateData = { id: productSource.id };
          if (updates.wholesale_cost !== '') updateData.wholesale_cost = parseFloat(updates.wholesale_cost);
          if (updates.pack_size !== '') updateData.pack_size = parseInt(updates.pack_size);
          if (updates.moq !== '') updateData.moq = parseInt(updates.moq);
          
          if (Object.keys(updateData).length > 1) {
            productSourceUpdates.push(updateData);
          }
        }
      }
      
      if (productSourceUpdates.length > 0) {
        await api.post('/products/bulk-update-costs', {
          product_source_updates: productSourceUpdates
        });
        
        fetchProducts();
        setSelectedProducts(new Set());
        setSelectAll(false);
      }
    } catch (err) {
      console.error('Bulk update costs failed:', err);
      alert('Failed to update costs');
    }
  };
  
  const handleBulkRefreshData = async (productIds) => {
    try {
      await api.post('/products/bulk-refetch', {
        product_ids: productIds
      });
      
      alert('API data refresh started. This may take a few minutes.');
      // Optionally refresh products after a delay
      setTimeout(() => fetchProducts(), 5000);
    } catch (err) {
      console.error('Bulk refresh failed:', err);
      alert('Failed to refresh data');
    }
  };

  const handleBulkHide = async (productIds) => {
    try {
      await api.post('/products/bulk-hide', { product_ids: productIds });
      fetchProducts();
      setSelectedProducts(new Set());
    } catch (err) {
      console.error('Bulk hide failed:', err);
    }
  };

  const handleBulkDelete = async (productIds) => {
    if (!window.confirm(`Delete ${productIds.length} products?`)) return;
    
    try {
      await api.post('/products/bulk-delete', { product_ids: productIds });
      fetchProducts();
      setSelectedProducts(new Set());
    } catch (err) {
      console.error('Bulk delete failed:', err);
    }
  };

  const handleBulkFavorite = async (productIds) => {
    try {
      await api.post('/products/bulk-favorite', { product_ids: productIds, favorite: true });
      fetchProducts();
      setSelectedProducts(new Set());
    } catch (err) {
      console.error('Bulk favorite failed:', err);
    }
  };

  const handleExport = (productIds = []) => {
    // Export to CSV
    const productsToExport = productIds.length > 0
      ? filteredProducts.filter(p => productIds.includes(p.id))
      : filteredProducts;
    
    // Convert to CSV
    const csv = convertToCSV(productsToExport);
    
    // Download
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `habexa-products-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // ============================================
  // UTILITY FUNCTIONS
  // ============================================
  const getProfitTier = (roi) => {
    if (roi >= 50) return 'Excellent';
    if (roi >= 30) return 'Good';
    if (roi >= 15) return 'Acceptable';
    if (roi >= 5) return 'Marginal';
    return 'Unprofitable';
  };

  const getProfitColor = (roi) => {
    if (roi >= 50) return '#4caf50';
    if (roi >= 30) return '#8bc34a';
    if (roi >= 15) return '#ffeb3b';
    if (roi >= 5) return '#ff9800';
    return '#f44336';
  };

  const convertToCSV = (data) => {
    if (!data || data.length === 0) return '';
    
    // Get visible columns (excluding select, image, asin which are always first)
    const cols = analyzerColumns.filter(col => 
      visibleColumns.includes(col.id) && 
      !['select', 'image', 'asin'].includes(col.id)
    );
    
    // Headers
    const headers = ['ASIN', 'Title', ...cols.map(col => col.label)].join(',');
    
    // Rows
    const rows = data.map(product => {
      const row = [
        product.asin || '',
        product.title || '',
        ...cols.map(col => {
          const value = product[col.id] || product.product_sources?.[0]?.[col.id] || '';
          return `"${String(value).replace(/"/g, '""')}"`;
        })
      ];
      return row.join(',');
    }).join('\n');
    
    return `${headers}\n${rows}`;
  };

  // Get active filter count
  const activeFilterCount = useMemo(() => {
    let count = 0;
    if (filters.search) count++;
    if (filters.roi.min !== null || filters.roi.max !== null) count++;
    if (filters.profit.min !== null || filters.profit.max !== null) count++;
    if (filters.pack_size.min || filters.pack_size.max) count++;
    if (filters.profit_tier.length > 0) count++;
    if (filters.has_promo !== null) count++;
    if (filters.in_stock !== null) count++;
    return count;
  }, [filters]);

  // ============================================
  // RENDER
  // ============================================
  return (
    <Box sx={{ p: 3 }}>
      {/* HEADER */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" fontWeight="bold">
          Product Analyzer
        </Typography>

        <Stack direction="row" spacing={2} alignItems="center">
          {/* Supplier Switcher */}
          <AnalyzerSupplierSwitcher
            currentSupplier={currentSupplier}
            onSupplierChange={setCurrentSupplier}
          />

          {/* Actions */}
          <Tooltip title="Refresh">
            <IconButton onClick={fetchProducts} disabled={loading}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>

          <Tooltip title="Filters">
            <IconButton 
              onClick={() => setShowFilters(!showFilters)}
              color={activeFilterCount > 0 ? 'primary' : 'default'}
            >
              {activeFilterCount > 0 ? (
                <Box position="relative">
                  <FilterListIcon />
                  <Box
                    sx={{
                      position: 'absolute',
                      top: -4,
                      right: -4,
                      bgcolor: 'primary.main',
                      color: 'white',
                      borderRadius: '50%',
                      width: 16,
                      height: 16,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: 10,
                      fontWeight: 'bold'
                    }}
                  >
                    {activeFilterCount}
                  </Box>
                </Box>
              ) : (
                <FilterListIcon />
              )}
            </IconButton>
          </Tooltip>

          <Tooltip title="Columns">
            <IconButton onClick={() => setShowColumnMenu(!showColumnMenu)}>
              <ViewColumnIcon />
            </IconButton>
          </Tooltip>

          <Tooltip title="Export">
            <IconButton onClick={handleExport}>
              <FileDownloadIcon />
            </IconButton>
          </Tooltip>
        </Stack>
      </Box>

      {/* QUICK FILTER CHIPS */}
      <Stack direction="row" spacing={1} mb={2} flexWrap="wrap" gap={1}>
        <Chip
          icon={<TrendingUpIcon />}
          label="High ROI (50%+)"
          onClick={() => setFilters({...filters, roi: { min: 50, max: null }})}
          color={filters.roi.min === 50 ? 'primary' : 'default'}
          variant={filters.roi.min === 50 ? 'filled' : 'outlined'}
          sx={{ fontWeight: filters.roi.min === 50 ? 600 : 400 }}
        />
        
        <Chip
          icon={<LocalOfferIcon />}
          label="Promo Deals"
          onClick={() => setFilters({...filters, has_promo: true})}
          color={filters.has_promo === true ? 'primary' : 'default'}
          variant={filters.has_promo === true ? 'filled' : 'outlined'}
          sx={{ fontWeight: filters.has_promo === true ? 600 : 400 }}
        />
        
        <Chip
          icon={<InventoryIcon />}
          label="Multi-Packs (>1)"
          onClick={() => setFilters({...filters, pack_size: { min: 2, max: null }})}
          color={filters.pack_size.min === 2 ? 'primary' : 'default'}
          variant={filters.pack_size.min === 2 ? 'filled' : 'outlined'}
          sx={{ fontWeight: filters.pack_size.min === 2 ? 600 : 400 }}
        />
        
        <Chip
          icon={<WarningIcon />}
          label="Unprofitable"
          onClick={() => setFilters({...filters, roi: { min: null, max: 5 }})}
          color={filters.roi.max === 5 ? 'error' : 'default'}
          variant={filters.roi.max === 5 ? 'filled' : 'outlined'}
          sx={{ fontWeight: filters.roi.max === 5 ? 600 : 400 }}
        />
        
        {activeFilterCount > 0 && (
          <Chip
            icon={<ClearIcon />}
            label="Clear All Filters"
            onClick={() => setFilters({
              search: '',
              roi: { min: null, max: null },
              profit: { min: null, max: null },
              pack_size: { min: null, max: null },
              profit_tier: [],
              has_promo: null,
              in_stock: null
            })}
            variant="outlined"
            onDelete={() => {}}
          />
        )}
      </Stack>

      {/* ADVANCED FILTERS */}
      {showFilters && (
        <AnalyzerFilters
          filters={filters}
          onFiltersChange={setFilters}
          onClose={() => setShowFilters(false)}
        />
      )}

      {/* COLUMN MENU */}
      {showColumnMenu && (
        <Box position="relative">
          <AnalyzerColumnMenu
            columns={analyzerColumns}
            visibleColumns={visibleColumns}
            onVisibleColumnsChange={setVisibleColumns}
            onClose={() => setShowColumnMenu(false)}
          />
        </Box>
      )}

      {/* BULK ACTIONS TOOLBAR */}
      {selectedProducts.size > 0 && (
        <AnalyzerBulkActions
          selectedCount={selectedProducts.size}
          selectedProducts={Array.from(selectedProducts)}
          onAddToOrder={handleBulkAddToOrder}
          onHide={handleBulkHide}
          onDelete={handleBulkDelete}
          onFavorite={handleBulkFavorite}
          onUpdateCosts={handleBulkUpdateCosts}
          onRefreshData={handleBulkRefreshData}
          onExport={handleExport}
          onClearSelection={() => {
            setSelectedProducts(new Set());
            setSelectAll(false);
          }}
        />
      )}

      {/* RESULTS COUNT */}
      <Box mb={2}>
        <Typography variant="body2" color="text.secondary">
          Showing {filteredProducts.length} of {products.length} products
          {selectedProducts.size > 0 && ` • ${selectedProducts.size} selected`}
        </Typography>
      </Box>

      {/* ERROR */}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {/* LOADING */}
      {loading && <LinearProgress sx={{ mb: 2 }} />}

      {/* TABLE */}
      <TableContainer component={Paper} sx={{ maxHeight: 'calc(100vh - 400px)' }}>
        <Table stickyHeader>
          <TableHead>
            <TableRow>
              {/* Checkbox Column - MUST BE FIRST, STICKY */}
              <TableCell 
                padding="checkbox" 
                sx={{ 
                  bgcolor: 'grey.100', 
                  position: 'sticky', 
                  left: 0, 
                  zIndex: 3,
                  minWidth: 48
                }}
              >
                <Checkbox
                  checked={selectAll}
                  indeterminate={selectedProducts.size > 0 && selectedProducts.size < filteredProducts.length}
                  onChange={(e) => handleSelectAll(e.target.checked)}
                  sx={{ color: 'primary.main' }}
                />
              </TableCell>

              {/* Image Column (Always visible) */}
              <TableCell sx={{ bgcolor: 'grey.100', position: 'sticky', left: 48, zIndex: 2 }}>
                <Typography variant="body2" fontWeight="bold">
                  Image
                </Typography>
              </TableCell>

              {/* ASIN Column (Always visible) */}
              <TableCell sx={{ bgcolor: 'grey.100', position: 'sticky', left: 148, zIndex: 2 }}>
                <Typography variant="body2" fontWeight="bold">
                  ASIN
                </Typography>
              </TableCell>

              {/* Dynamic Columns */}
              {analyzerColumns
                .filter(col => visibleColumns.includes(col.id) && !['select', 'image', 'asin'].includes(col.id))
                .map(column => (
                  <TableCell 
                    key={column.id}
                    sx={{ bgcolor: 'grey.100', minWidth: column.width || 120 }}
                  >
                    <Box display="flex" alignItems="center" gap={1}>
                      <Typography variant="body2" fontWeight="bold">
                        {column.label}
                      </Typography>
                      
                      {column.sortable !== false && (
                        <IconButton
                          size="small"
                          onClick={() => {
                            if (sortBy === column.id) {
                              setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
                            } else {
                              setSortBy(column.id);
                              setSortDirection('desc');
                            }
                          }}
                          sx={{ p: 0.5, ml: 0.5 }}
                        >
                          <Typography variant="caption" color="primary">
                            {sortBy === column.id ? (
                              sortDirection === 'asc' ? '↑' : '↓'
                            ) : (
                              '⇅'
                            )}
                          </Typography>
                        </IconButton>
                      )}
                    </Box>
                  </TableCell>
                ))}
            </TableRow>
          </TableHead>

          <TableBody>
            {filteredProducts.map(product => (
                <AnalyzerTableRow
                  key={product.id}
                  product={product}
                  selected={selectedProducts.has(product.id)}
                  visibleColumns={visibleColumns}
                  profitColor={getProfitColor(product.roi || product.roi_percentage || 0)}
                  onSelect={(checked) => handleSelectProduct(product.id, checked)}
                  onFieldUpdate={handleFieldUpdate}
                  columns={analyzerColumns}
                  roiValue={product.roi || product.roi_percentage || 0}
                />
            ))}

            {filteredProducts.length === 0 && !loading && (
              <TableRow>
                <TableCell colSpan={visibleColumns.length + 3} align="center" sx={{ py: 8 }}>
                  <Typography variant="h6" color="text.secondary">
                    No products found
                  </Typography>
                  {activeFilterCount > 0 && (
                    <Typography variant="body2" color="text.secondary" mt={1}>
                      Try adjusting your filters
                    </Typography>
                  )}
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* PAGINATION */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mt={2}>
        <Typography variant="body2" color="text.secondary">
          Page 1 of {Math.ceil(filteredProducts.length / 50)}
        </Typography>
        
        <Stack direction="row" spacing={1}>
          {/* Add pagination controls here */}
        </Stack>
      </Box>
    </Box>
  );
}

