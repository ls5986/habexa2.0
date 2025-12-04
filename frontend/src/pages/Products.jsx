import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box, Typography, Card, Button, Chip, IconButton, Tabs, Tab,
  TextField, InputAdornment, Menu, MenuItem, Checkbox, Select,
  FormControl, InputLabel, CircularProgress, Dialog, DialogTitle,
  DialogContent, DialogActions, LinearProgress, Tooltip
} from '@mui/material';
import {
  Search, Upload, Plus, Download, RefreshCw, MoreVertical,
  Package, TrendingUp, ShoppingCart, Archive, Clock, Zap,
  ChevronDown, ExternalLink, Filter, X
} from 'lucide-react';
import api from '../services/api';
import FileUploadModal from '../components/features/products/FileUploadModal';
import BatchAnalyzeButton from '../components/features/products/BatchAnalyzeButton';
import { useFeatureGate } from '../hooks/useFeatureGate';
import { useToast } from '../context/ToastContext';
import { handleApiError } from '../utils/errorHandler';
import { habexa } from '../theme';

const STAGES = [
  { id: 'new', label: 'New', icon: Package, color: habexa.purple.main },
  { id: 'analyzing', label: 'Analyzing', icon: Clock, color: habexa.warning.main },
  { id: 'reviewed', label: 'Reviewed', icon: TrendingUp, color: habexa.info.main },
  { id: 'buy_list', label: 'Buy List', icon: ShoppingCart, color: habexa.success.main },
  { id: 'ordered', label: 'Ordered', icon: Archive, color: habexa.gray[400] },
];

// Debounce hook
function useDebounce(value, delay) {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

// Memoized Deal Row Component
const DealRow = React.memo(({ deal, selected, onSelect, onClick, onUpdateMoq }) => {
  const roi = deal.roi || 0;
  const profit = deal.profit || 0;
  const moq = deal.moq || 1;
  const buyCost = deal.buy_cost || 0;
  const totalInvestment = deal.total_investment || (moq * buyCost);
  const totalProfit = moq * profit;

  const [editingMoq, setEditingMoq] = useState(false);
  const [tempMoq, setTempMoq] = useState(moq);

  const handleMoqSave = () => {
    onUpdateMoq(deal.deal_id, tempMoq);
    setEditingMoq(false);
  };

  return (
    <Box
      sx={{
        display: 'grid',
        gridTemplateColumns: '40px 110px 1fr 120px 80px 80px 80px 90px 80px 80px 60px',
        p: 1.5,
        borderBottom: '1px solid',
        borderColor: 'divider',
        alignItems: 'center',
        '&:hover': { bgcolor: 'action.hover' },
        cursor: 'pointer'
      }}
      onClick={onClick}
    >
      <Checkbox
        size="small"
        checked={selected}
        onClick={(e) => e.stopPropagation()}
        onChange={onSelect}
      />
      <Typography variant="body2" fontFamily="monospace" fontSize={12}>
        {deal.asin}
      </Typography>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: 0 }}>
        {deal.image_url ? (
          <Box
            component="img"
            src={deal.image_url}
            sx={{ width: 32, height: 32, borderRadius: 1, objectFit: 'cover', flexShrink: 0 }}
          />
        ) : (
          <Box sx={{ width: 32, height: 32, bgcolor: habexa.navy.light, borderRadius: 1 }} />
        )}
        <Typography variant="body2" noWrap sx={{ minWidth: 0 }}>
          {deal.title || 'Pending analysis...'}
        </Typography>
      </Box>
      
      {/* Supplier Name */}
      <Typography variant="body2" color="text.secondary" noWrap>
        {deal.supplier_name || 'Unknown'}
      </Typography>
      
      {/* MOQ - Editable */}
      <Box sx={{ textAlign: 'right' }} onClick={(e) => e.stopPropagation()}>
        {editingMoq ? (
          <TextField
            size="small"
            type="number"
            value={tempMoq}
            onChange={(e) => setTempMoq(parseInt(e.target.value) || 1)}
            onBlur={handleMoqSave}
            onKeyDown={(e) => e.key === 'Enter' && handleMoqSave()}
            autoFocus
            sx={{ width: 50 }}
            inputProps={{ min: 1, style: { textAlign: 'right', padding: '4px' } }}
          />
        ) : (
          <Chip
            label={moq}
            size="small"
            onClick={() => setEditingMoq(true)}
            sx={{ 
              minWidth: 40,
              cursor: 'pointer',
              bgcolor: habexa.gray[300],
              '&:hover': { bgcolor: habexa.navy.light }
            }}
          />
        )}
      </Box>
      
      {/* Unit Cost */}
      <Typography variant="body2" align="right" color="text.secondary">
        ${buyCost.toFixed(2)}
      </Typography>
      
      {/* Total Investment */}
      <Typography 
        variant="body2" 
        align="right" 
        fontWeight="600"
        color={totalInvestment > 500 ? 'warning.main' : 'text.primary'}
      >
        ${totalInvestment.toFixed(2)}
      </Typography>
      
      {/* ROI - Pre-calculated from view */}
      <Typography
        variant="body2"
        align="right"
        fontWeight="600"
        color={roi >= 30 ? 'success.main' : roi > 0 ? 'warning.main' : 'error.main'}
      >
        {roi ? `${roi.toFixed(0)}%` : '-'}
      </Typography>
      
      {/* Profit per unit - Pre-calculated from view */}
      <Tooltip title={`Total: $${totalProfit.toFixed(2)}`}>
        <Typography
          variant="body2"
          align="right"
          color={profit > 0 ? 'success.main' : 'error.main'}
        >
          ${profit ? profit.toFixed(2) : '-'}
        </Typography>
      </Tooltip>
      
      {/* Stage */}
      <Chip
        label={deal.stage || 'new'}
        size="small"
        sx={{ height: 22, fontSize: 11 }}
      />
      
      {/* Actions */}
      <IconButton
        size="small"
        component="a"
        href={`https://amazon.com/dp/${deal.asin}`}
        target="_blank"
        onClick={(e) => e.stopPropagation()}
      >
        <ExternalLink size={14} />
      </IconButton>
    </Box>
  );
});

DealRow.displayName = 'DealRow';

export default function Products() {
  const navigate = useNavigate();
  const fetchInProgress = useRef(false);
  
  const [deals, setDeals] = useState([]);
  const [stats, setStats] = useState({ stages: {}, total: 0 });
  const [loading, setLoading] = useState(true);
  const [activeStage, setActiveStage] = useState(null); // null = all
  const [selected, setSelected] = useState([]);
  const [filters, setFilters] = useState({ minRoi: '', minProfit: '', search: '', supplier: '' });
  const [suppliers, setSuppliers] = useState([]);
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const { hasFeature, promptUpgrade } = useFeatureGate();
  const { showToast } = useToast();

  // Debounce search to reduce API calls
  const debouncedSearch = useDebounce(filters.search, 500);

  // Fetch data with parallel API calls and caching
  const fetchData = useCallback(async () => {
    // Prevent duplicate calls
    if (fetchInProgress.current) return;
    fetchInProgress.current = true;

    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (activeStage) params.append('stage', activeStage);
      if (filters.minRoi) params.append('min_roi', filters.minRoi);
      if (filters.minProfit) params.append('min_profit', filters.minProfit);
      if (debouncedSearch) params.append('search', debouncedSearch);
      if (filters.supplier) params.append('supplier_id', filters.supplier);
      params.append('limit', '100');

      // Parallel API calls for better performance
      const [dealsRes, statsRes] = await Promise.all([
        api.get(`/products?${params}`),
        api.get('/products/stats')
      ]);

      // Handle different response formats safely
      let dealsData = [];
      if (Array.isArray(dealsRes.data)) {
        dealsData = dealsRes.data;
      } else if (Array.isArray(dealsRes.data?.deals)) {
        dealsData = dealsRes.data.deals;
      } else if (Array.isArray(dealsRes.data?.data)) {
        dealsData = dealsRes.data.data;
      }
      setDeals(dealsData);
      setStats(statsRes.data || { stages: {}, total: 0 });
    } catch (err) {
      console.error('Failed to fetch:', err);
    } finally {
      setLoading(false);
      fetchInProgress.current = false;
    }
  }, [activeStage, filters.minRoi, filters.minProfit, debouncedSearch, filters.supplier]);

  // Fetch suppliers once
  const fetchSuppliers = useCallback(async () => {
    try {
      const res = await api.get('/suppliers');
      // Handle different response formats safely
      let suppliersData = [];
      if (Array.isArray(res.data)) {
        suppliersData = res.data;
      } else if (Array.isArray(res.data?.suppliers)) {
        suppliersData = res.data.suppliers;
      } else if (Array.isArray(res.data?.data)) {
        suppliersData = res.data.data;
      }
      setSuppliers(suppliersData);
    } catch (err) {
      console.error('Failed to fetch suppliers:', err);
    }
  }, []);

  // Initial load - only once
  useEffect(() => {
    fetchData();
    fetchSuppliers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Only run on mount

  // Refetch when stage changes (debounced)
  const debouncedStage = useDebounce(activeStage, 300);
  useEffect(() => {
    if (debouncedStage !== undefined) {
      fetchData();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedStage]);

  const handleSelectAll = (e) => {
    if (e.target.checked) {
      const dealsArray = Array.isArray(deals) ? deals : [];
      setSelected(dealsArray.map(d => d.deal_id));
    } else {
      setSelected([]);
    }
  };

  const handleSelect = (id) => {
    setSelected(prev => 
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    );
  };

  const handleBulkAnalyze = async () => {
    if (!selected.length) return;
    setAnalyzing(true);
    try {
      const res = await api.post('/products/bulk-analyze', { deal_ids: selected });
      showToast(`Queued ${res.data.queued} products for analysis`, 'success');
      setSelected([]);
      fetchData();
    } catch (err) {
      handleApiError(err, showToast);
    } finally {
      setAnalyzing(false);
    }
  };

  const handleBulkMove = async (stage) => {
    if (!selected.length) return;
    try {
      await api.post('/products/bulk-stage', { deal_ids: selected, stage });
      setSelected([]);
      fetchData();
    } catch (err) {
      handleApiError(err, showToast);
    }
  };

  const handleUploadComplete = (result) => {
    // Refresh products list after a short delay to let backend process
    setTimeout(() => {
      fetchData();
    }, 2000);
    // Could show toast notification here
    console.log('Upload complete:', result);
  };

  const handleExport = async () => {
    // Check if user has export feature
    if (!hasFeature('export_data')) {
      promptUpgrade('export_data');
      return;
    }
    
    try {
      const params = activeStage ? `?stage=${activeStage}` : '';
      const res = await api.get(`/products/export${params}`);
      
      // Convert to CSV
      const rows = res.data.rows || [];
      if (!rows.length) return;
      
      const headers = Object.keys(rows[0]);
      const csv = [
        headers.join(','),
        ...rows.map(r => headers.map(h => `"${r[h] || ''}"`).join(','))
      ].join('\n');
      
      const blob = new Blob([csv], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `deals-${activeStage || 'all'}-${Date.now()}.csv`;
      a.click();
    } catch (err) {
      console.error('Export failed:', err);
      showToast('Export failed: ' + (err.response?.data?.detail || err.message), 'error');
    }
  };

  const handleUpdateMoq = async (dealId, newMoq) => {
    try {
      await api.patch(`/products/deal/${dealId}`, { moq: newMoq });
      // Update local state
      setDeals(prev => prev.map(d => 
        d.deal_id === dealId ? { ...d, moq: newMoq, total_investment: (d.buy_cost || 0) * newMoq } : d
      ));
    } catch (err) {
      console.error('Failed to update MOQ:', err);
      showToast('Failed to update MOQ: ' + (err.response?.data?.detail || err.message), 'error');
    }
  };

  // Memoized filtered deals for client-side filtering (if needed)
  const filteredDeals = useMemo(() => {
    return deals; // Server-side filtering, but can add client-side here if needed
  }, [deals]);

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" fontWeight="700">Products</Typography>
        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
          <BatchAnalyzeButton
            analyzeAllPending={true}
            buttonText="Analyze All Pending"
            onComplete={() => setTimeout(() => fetchData(), 1000)}
          />
          {selected.length > 0 && (
            <BatchAnalyzeButton
              productIds={selected}
              buttonText={`Analyze ${selected.length} Selected`}
              onComplete={() => {
                setSelected([]);
                setTimeout(() => fetchData(), 1000);
              }}
            />
          )}
          <Button
            variant="outlined"
            startIcon={<Upload size={16} />}
            onClick={() => setShowUploadModal(true)}
          >
            Upload File
          </Button>
          <Button
            variant="contained"
            startIcon={<Plus size={16} />}
            onClick={() => setShowAddDialog(true)}
          >
            Add ASIN
          </Button>
        </Box>
      </Box>

      {/* Stage Tabs */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
        <Tabs value={activeStage || 'all'} onChange={(e, v) => setActiveStage(v === 'all' ? null : v)}>
          <Tab value="all" label={`All (${stats.total || 0})`} />
          {STAGES.map(s => (
            <Tab
              key={s.id}
              value={s.id}
              label={`${s.label} (${stats.stages?.[s.id] || 0})`}
              icon={<s.icon size={14} />}
              iconPosition="start"
            />
          ))}
        </Tabs>
      </Box>

      {/* Filters & Bulk Actions */}
      <Box sx={{ display: 'flex', gap: 2, mb: 2, flexWrap: 'wrap', alignItems: 'center' }}>
        <TextField
          size="small"
          placeholder="Search ASIN..."
          value={filters.search}
          onChange={(e) => setFilters({ ...filters, search: e.target.value })}
          InputProps={{
            startAdornment: <InputAdornment position="start"><Search size={16} /></InputAdornment>
          }}
          sx={{ width: 200 }}
        />
        <TextField
          size="small"
          placeholder="Min ROI %"
          type="number"
          value={filters.minRoi}
          onChange={(e) => setFilters({ ...filters, minRoi: e.target.value })}
          onBlur={() => setTimeout(() => fetchData(), 500)}
          sx={{ width: 100 }}
        />
        <TextField
          size="small"
          placeholder="Min Profit $"
          type="number"
          value={filters.minProfit}
          onChange={(e) => setFilters({ ...filters, minProfit: e.target.value })}
          onBlur={() => setTimeout(() => fetchData(), 500)}
          sx={{ width: 100 }}
        />
        <FormControl size="small" sx={{ width: 150 }}>
          <InputLabel>Supplier</InputLabel>
          <Select
            value={filters.supplier}
            label="Supplier"
            onChange={(e) => { 
              setFilters({ ...filters, supplier: e.target.value }); 
              // Debounce the fetch
              setTimeout(() => fetchData(), 500);
            }}
          >
            <MenuItem value="">All</MenuItem>
            {suppliers.map(s => (
              <MenuItem key={s.id} value={s.id}>{s.name}</MenuItem>
            ))}
          </Select>
        </FormControl>
        
        <Box sx={{ flex: 1 }} />
        
        {selected.length > 0 && (
          <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
            <Typography variant="body2" color="text.secondary">
              {selected.length} selected
            </Typography>
            <Button
              size="small"
              variant="contained"
              startIcon={analyzing ? <CircularProgress size={14} /> : <Zap size={14} />}
              onClick={handleBulkAnalyze}
              disabled={analyzing}
            >
              Analyze
            </Button>
            <Button
              size="small"
              variant="outlined"
              onClick={() => handleBulkMove('buy_list')}
            >
              Move to Buy List
            </Button>
            <Button
              size="small"
              variant="outlined"
              color="error"
              onClick={() => setSelected([])}
            >
              <X size={14} />
            </Button>
          </Box>
        )}
        
        <IconButton onClick={fetchData}><RefreshCw size={18} /></IconButton>
        <IconButton 
          onClick={handleExport} 
          disabled={!hasFeature('export_data')}
          title={!hasFeature('export_data') ? 'Export requires Starter or higher' : 'Export data'}
        >
          <Download size={18} />
        </IconButton>
      </Box>

      {/* Deals Table */}
      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress />
        </Box>
      ) : filteredDeals.length === 0 ? (
        <Card sx={{ p: 4, textAlign: 'center' }}>
          <Package size={48} color={habexa.gray[400]} />
          <Typography variant="h6" sx={{ mt: 2 }}>No deals found</Typography>
          <Typography color="text.secondary" sx={{ mb: 2 }}>
            Upload a CSV or Excel file or add ASINs manually to get started
          </Typography>
          <Button variant="contained" startIcon={<Plus size={16} />} onClick={() => setShowAddDialog(true)}>
            Add Your First ASIN
          </Button>
        </Card>
      ) : (
        <Card>
          {/* Table Header */}
          <Box sx={{ 
            display: { xs: 'none', md: 'grid' },
            gridTemplateColumns: '40px 110px 1fr 120px 80px 80px 80px 90px 80px 80px 60px',
            p: 1.5, 
            borderBottom: '1px solid',
            borderColor: 'divider',
            bgcolor: 'background.paper'
          }}>
            <Checkbox
              size="small"
              checked={selected.length === filteredDeals.length && filteredDeals.length > 0}
              indeterminate={selected.length > 0 && selected.length < filteredDeals.length}
              onChange={handleSelectAll}
            />
            <Typography variant="caption" color="text.secondary">ASIN</Typography>
            <Typography variant="caption" color="text.secondary">Product</Typography>
            <Typography variant="caption" color="text.secondary">Supplier</Typography>
            <Typography variant="caption" color="text.secondary" align="right">MOQ</Typography>
            <Typography variant="caption" color="text.secondary" align="right">Unit $</Typography>
            <Typography variant="caption" color="text.secondary" align="right">Total $</Typography>
            <Typography variant="caption" color="text.secondary" align="right">ROI</Typography>
            <Typography variant="caption" color="text.secondary" align="right">Profit</Typography>
            <Typography variant="caption" color="text.secondary">Stage</Typography>
            <Typography variant="caption" color="text.secondary">Actions</Typography>
          </Box>

          {/* Table Rows - Desktop */}
          <Box sx={{ display: { xs: 'none', md: 'block' } }}>
            {filteredDeals.map(deal => (
              <DealRow
                key={deal.deal_id}
                deal={deal}
                selected={selected.includes(deal.deal_id)}
                onSelect={() => handleSelect(deal.deal_id)}
                onClick={() => navigate(`/deals/${deal.deal_id}`)}
                onUpdateMoq={handleUpdateMoq}
              />
            ))}
          </Box>

          {/* Mobile Cards */}
          <Box sx={{ display: { xs: 'flex', md: 'none' }, flexDirection: 'column', gap: 2, p: 2 }}>
            {filteredDeals.map(deal => (
              <Card
                key={deal.deal_id}
                sx={{
                  p: 2,
                  border: selected.includes(deal.deal_id) ? `2px solid ${habexa.purple.main}` : '1px solid',
                  borderColor: selected.includes(deal.deal_id) ? habexa.purple.main : 'divider',
                  cursor: 'pointer',
                }}
                onClick={() => navigate(`/deals/${deal.deal_id}`)}
              >
                <Box display="flex" justifyContent="space-between" alignItems="start" mb={2}>
                  <Box display="flex" gap={2} flex={1}>
                    {deal.image_url && (
                      <Box
                        component="img"
                        src={deal.image_url}
                        sx={{ width: 64, height: 64, borderRadius: 1, objectFit: 'cover' }}
                      />
                    )}
                    <Box flex={1}>
                      <Typography variant="body2" fontWeight={600} mb={0.5}>
                        {deal.title || 'Pending analysis...'}
                      </Typography>
                      <Typography variant="caption" fontFamily="monospace" color="text.secondary">
                        {deal.asin}
                      </Typography>
                    </Box>
                  </Box>
                  <Checkbox
                    size="small"
                    checked={selected.includes(deal.deal_id)}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleSelect(deal.deal_id);
                    }}
                  />
                </Box>
                <Box display="flex" justifyContent="space-between" gap={2} flexWrap="wrap">
                  <Box>
                    <Typography variant="caption" color="text.secondary">ROI</Typography>
                    <Typography variant="body2" fontWeight={600} color={deal.roi >= 30 ? 'success.main' : 'text.primary'}>
                      {deal.roi ? `${deal.roi.toFixed(0)}%` : '-'}
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="caption" color="text.secondary">Profit</Typography>
                    <Typography variant="body2" fontWeight={600} color={deal.profit > 0 ? 'success.main' : 'error.main'}>
                      ${deal.profit ? deal.profit.toFixed(2) : '-'}
                    </Typography>
                  </Box>
                  <Box>
                    <Typography variant="caption" color="text.secondary">Cost</Typography>
                    <Typography variant="body2">
                      ${(deal.buy_cost || 0).toFixed(2)}
                    </Typography>
                  </Box>
                  <Chip label={deal.stage || 'new'} size="small" sx={{ height: 22, fontSize: 11 }} />
                </Box>
              </Card>
            ))}
          </Box>
        </Card>
      )}

      {/* Add Product Dialog */}
      <AddProductDialog
        open={showAddDialog}
        onClose={() => setShowAddDialog(false)}
        onAdded={() => { setShowAddDialog(false); fetchData(); }}
        suppliers={suppliers}
      />

      {/* File Upload Modal */}
      <FileUploadModal
        open={showUploadModal}
        onClose={() => setShowUploadModal(false)}
        onComplete={handleUploadComplete}
      />
    </Box>
  );
}

// Add Product Dialog
function AddProductDialog({ open, onClose, onAdded, suppliers }) {
  const [form, setForm] = useState({ asin: '', buy_cost: '', supplier_id: '', supplier_name: '', moq: '1', notes: '' });
  const [loading, setLoading] = useState(false);
  const { showToast } = useToast();

  const handleSubmit = async () => {
    if (!form.asin) return;
    setLoading(true);
    try {
      await api.post('/products', {
        asin: form.asin,
        buy_cost: form.buy_cost ? parseFloat(form.buy_cost) : null,
        supplier_id: form.supplier_id || null,
        supplier_name: form.supplier_name || null,
        moq: parseInt(form.moq) || 1,
        notes: form.notes
      });
      setForm({ asin: '', buy_cost: '', supplier_id: '', supplier_name: '', moq: '1', notes: '' });
      onAdded();
    } catch (err) {
      showToast(err.response?.data?.detail || 'Failed to add product', 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Add Product</DialogTitle>
      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
          <TextField
            label="ASIN"
            value={form.asin}
            onChange={(e) => setForm({ ...form, asin: e.target.value.toUpperCase() })}
            placeholder="B08VBVBS7N"
            required
          />
          <TextField
            label="Buy Cost"
            type="number"
            value={form.buy_cost}
            onChange={(e) => setForm({ ...form, buy_cost: e.target.value })}
            InputProps={{ startAdornment: <InputAdornment position="start">$</InputAdornment> }}
          />
          <FormControl>
            <InputLabel>Supplier</InputLabel>
            <Select
              value={form.supplier_id}
              label="Supplier"
              onChange={(e) => setForm({ ...form, supplier_id: e.target.value, supplier_name: '' })}
            >
              <MenuItem value="">Select existing...</MenuItem>
              {suppliers.map(s => (
                <MenuItem key={s.id} value={s.id}>{s.name}</MenuItem>
              ))}
            </Select>
          </FormControl>
          <TextField
            label="Or New Supplier Name"
            value={form.supplier_name}
            onChange={(e) => setForm({ ...form, supplier_name: e.target.value, supplier_id: '' })}
            placeholder="Enter new supplier name"
          />
          <TextField
            label="MOQ"
            type="number"
            value={form.moq}
            onChange={(e) => setForm({ ...form, moq: e.target.value })}
          />
          <TextField
            label="Notes"
            multiline
            rows={2}
            value={form.notes}
            onChange={(e) => setForm({ ...form, notes: e.target.value })}
          />
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button variant="contained" onClick={handleSubmit} disabled={loading || !form.asin}>
          {loading ? <CircularProgress size={20} /> : 'Add Product'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
