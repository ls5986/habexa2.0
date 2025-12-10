import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box, Typography, Card, Button, Chip, IconButton, Tabs, Tab,
  TextField, InputAdornment, Menu, MenuItem, Checkbox, Select,
  FormControl, InputLabel, CircularProgress, Dialog, DialogTitle,
  DialogContent, DialogActions, LinearProgress, Tooltip, Alert,
  Radio, RadioGroup, FormControlLabel
} from '@mui/material';
import {
  Search, Upload, Plus, Download, RefreshCw, MoreVertical,
  Package, TrendingUp, ShoppingCart, Archive, Clock, Zap,
  ChevronDown, ExternalLink, Filter, X, Trash2, AlertTriangle
} from 'lucide-react';
import api from '../services/api';
import FileUploadModal from '../components/features/products/FileUploadModal';
import BatchAnalyzeButton from '../components/features/products/BatchAnalyzeButton';
import ManualPriceDialog from '../components/features/products/ManualPriceDialog';
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
const DealRow = React.memo(({ deal, selected, onSelect, onClick, onUpdateMoq, onDelete, onSetAsin, onOpenManualPrice, onSelectAsin, onEnterAsin, analysis }) => {
  const roi = deal.roi || 0;
  const profit = deal.profit || 0;
  const moq = deal.moq || 1;
  const buyCost = deal.buy_cost || 0;
  const totalInvestment = deal.total_investment || (moq * buyCost);
  const totalProfit = moq * profit;
  const asinStatus = deal.asin_status || 'found';
  const needsAsin = asinStatus === 'not_found' || !deal.asin;
  const needsSelection = asinStatus === 'multiple_found';
  const potentialAsins = deal.potential_asins || [];
  const isVariation = deal.is_variation && deal.variation_count > 1;
  
  // Pricing status from analysis
  const analysisData = analysis || {};
  const pricingStatus = analysisData.pricing_status || 'complete';
  const needsReview = analysisData.needs_review || pricingStatus === 'no_pricing';

  const [editingMoq, setEditingMoq] = useState(false);
  const [tempMoq, setTempMoq] = useState(moq);
  const [editingAsin, setEditingAsin] = useState(false);
  const [tempAsin, setTempAsin] = useState('');

  const handleMoqSave = () => {
    onUpdateMoq(deal.deal_id, tempMoq);
    setEditingMoq(false);
  };

  const handleAsinSave = () => {
    if (tempAsin.length === 10) {
      onSetAsin(deal.product_id, tempAsin);
      setEditingAsin(false);
      setTempAsin('');
    }
  };

  return (
    <Box
      sx={{
        display: 'grid',
        gridTemplateColumns: '40px 50px 140px 1fr 120px 70px 60px 80px 80px 90px 80px 80px 60px',
        p: 1.5,
        borderBottom: '1px solid',
        borderColor: 'divider',
        alignItems: 'center',
        gap: 1,
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
      {/* Product Image - Separate Column */}
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
        {deal.image_url ? (
          <Box
            component="img"
            src={deal.image_url}
            sx={{ 
              width: 40, 
              height: 40, 
              borderRadius: 1, 
              objectFit: 'cover', 
              flexShrink: 0,
              border: '1px solid',
              borderColor: 'divider'
            }}
            onError={(e) => {
              e.target.style.display = 'none';
            }}
          />
        ) : (
          <Box sx={{ 
            width: 40, 
            height: 40, 
            bgcolor: 'grey.100', 
            borderRadius: 1,
            border: '1px solid',
            borderColor: 'divider',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <Package size={20} color="#999" />
          </Box>
        )}
      </Box>
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
        {needsSelection ? (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
            <Chip
              label={`Choose ASIN (${potentialAsins.length})`}
              color="warning"
              size="small"
              onClick={(e) => {
                e.stopPropagation();
                onSelectAsin && onSelectAsin(deal);
              }}
              sx={{
                fontSize: 10,
                height: 20,
                cursor: 'pointer',
                '&:hover': { bgcolor: 'warning.dark' }
              }}
            />
            {deal.upc && (
              <Typography variant="caption" color="text.secondary" fontSize={9}>
                UPC: {deal.upc}
              </Typography>
            )}
          </Box>
        ) : needsAsin ? (
          <>
            {editingAsin ? (
              <Box sx={{ display: 'flex', gap: 0.5, alignItems: 'center' }}>
                <TextField
                  size="small"
                  placeholder="Enter ASIN"
                  value={tempAsin}
                  onChange={(e) => setTempAsin(e.target.value.toUpperCase().slice(0, 10))}
                  onClick={(e) => e.stopPropagation()}
                  sx={{ width: 100, fontSize: 11 }}
                  inputProps={{ style: { fontSize: 11, fontFamily: 'monospace' } }}
                />
                <Button
                  size="small"
                  variant="contained"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleAsinSave();
                  }}
                  disabled={tempAsin.length !== 10}
                  sx={{ minWidth: 40, height: 28, fontSize: 10 }}
                >
                  Save
                </Button>
              </Box>
            ) : (
              <Box sx={{ display: 'flex', gap: 0.5, alignItems: 'center' }}>
                <Chip
                  label="Enter ASIN"
                  color="error"
                  size="small"
                  onClick={(e) => {
                    e.stopPropagation();
                    onEnterAsin && onEnterAsin(deal);
                  }}
                  sx={{
                    fontSize: 10,
                    height: 20,
                    cursor: 'pointer',
                    '&:hover': { bgcolor: 'error.dark' }
                  }}
                />
              </Box>
            )}
            {deal.upc && (
              <Typography variant="caption" color="text.secondary" fontSize={10}>
                UPC: {deal.upc}
              </Typography>
            )}
          </>
        ) : (
          <>
            <Typography variant="body2" fontFamily="monospace" fontSize={12} fontWeight={500}>
              {deal.asin}
            </Typography>
            {isVariation && (
              <Chip
                label={`Variation (${deal.variation_count})`}
                size="small"
                variant="outlined"
                sx={{ fontSize: 9, height: 18, mt: 0.5 }}
              />
            )}
            {deal.upc && (
              <Typography variant="caption" color="text.secondary" fontSize={9}>
                UPC: {deal.upc}
              </Typography>
            )}
          </>
        )}
      </Box>
      {/* Product Title - No image here anymore */}
      <Typography variant="body2" noWrap sx={{ minWidth: 0, fontWeight: 500 }}>
        {deal.title || (deal.roi === undefined && deal.profit === undefined ? 'Pending analysis...' : 'Unknown Product')}
      </Typography>
      
      {/* Supplier Name */}
      <Typography variant="body2" color="text.secondary" noWrap>
        {deal.supplier_name || 'Unknown'}
      </Typography>
      
      {/* MOQ - Editable */}
      <Box sx={{ textAlign: 'center', display: 'flex', justifyContent: 'center' }} onClick={(e) => e.stopPropagation()}>
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
            inputProps={{ min: 1, style: { textAlign: 'center', padding: '4px' } }}
          />
        ) : (
          <Chip
            label={moq}
            size="small"
            variant="outlined"
            onClick={() => setEditingMoq(true)}
            sx={{ 
              minWidth: 40,
              cursor: 'pointer',
              bgcolor: 'background.paper',
              borderColor: 'divider',
              color: 'text.primary',
              fontWeight: 500,
              '&:hover': { 
                bgcolor: 'action.hover',
                borderColor: habexa.purple.main,
                color: habexa.purple.main
              }
            }}
          />
        )}
      </Box>
      
      {/* Pack Size */}
      <Box sx={{ textAlign: 'center' }}>
        <Typography variant="body2" color="text.secondary">
          {deal.case_pack || deal.pack_size || '-'}
        </Typography>
      </Box>
      
      {/* Unit Cost */}
      <Box sx={{ textAlign: 'right' }}>
        <Typography variant="body2" color="text.secondary">
          ${(buyCost || 0).toFixed(2)}
        </Typography>
        {deal.has_promo && deal.promo_percent && (
          <Chip 
            label={`${deal.promo_percent}% OFF`} 
            color="success" 
            size="small"
            sx={{ 
              fontWeight: 'bold',
              fontSize: 9,
              height: 18,
              mt: 0.5
            }}
          />
        )}
      </Box>
      
      {/* Total Investment */}
      <Typography 
        variant="body2" 
        align="right" 
        fontWeight="600"
        color={(totalInvestment || 0) > 500 ? 'warning.main' : 'text.primary'}
      >
        ${(totalInvestment || 0).toFixed(2)}
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
      <Tooltip title={`Total: $${(totalProfit || 0).toFixed(2)}`}>
        <Typography
          variant="body2"
          align="right"
          color={(profit || 0) > 0 ? 'success.main' : 'error.main'}
        >
          ${profit ? profit.toFixed(2) : '-'}
        </Typography>
      </Tooltip>
      
      {/* Pricing Status & Stage */}
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
        {needsReview && (
          <Tooltip title={`Reason: ${analysisData.pricing_status_reason || 'No pricing data'}`}>
            <Chip
              label={pricingStatus === 'manual' ? 'Manual' : 'No Pricing'}
              color={pricingStatus === 'manual' ? 'info' : 'warning'}
              size="small"
              onClick={(e) => {
                e.stopPropagation();
                if (pricingStatus === 'no_pricing' && onOpenManualPrice) {
                  onOpenManualPrice(deal, analysisData);
                }
              }}
              sx={{
                height: 18,
                fontSize: 9,
                cursor: pricingStatus === 'no_pricing' ? 'pointer' : 'default',
                '&:hover': pricingStatus === 'no_pricing' ? { bgcolor: 'warning.dark' } : {}
              }}
            />
          </Tooltip>
        )}
        <Chip
          label={deal.stage || 'new'}
          size="small"
          sx={{ height: 22, fontSize: 11 }}
        />
      </Box>
      
      {/* Actions */}
      <Box sx={{ display: 'flex', gap: 0.5, alignItems: 'center' }} onClick={(e) => e.stopPropagation()}>
        <Tooltip title="View on Amazon">
          <IconButton
            size="small"
            component="a"
            href={`https://amazon.com/dp/${deal.asin}`}
            target="_blank"
          >
            <ExternalLink size={14} />
          </IconButton>
        </Tooltip>
        <Tooltip title="Delete product">
          <IconButton
            size="small"
            onClick={(e) => {
              e.stopPropagation();
              onDelete(deal);
            }}
            sx={{ color: 'error.main' }}
          >
            <Trash2 size={14} />
          </IconButton>
        </Tooltip>
      </Box>
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
  const [filters, setFilters] = useState({ minRoi: '', minProfit: '', search: '', supplier: '', asinStatus: 'all', pricingStatus: 'all' });
  const [showPromoOnly, setShowPromoOnly] = useState(false);
  const [suppliers, setSuppliers] = useState([]);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [deleteDialog, setDeleteDialog] = useState({ open: false, deal: null });
  const [manualPriceDialog, setManualPriceDialog] = useState({ open: false, deal: null, analysis: null });
  const [asinSelectionDialog, setAsinSelectionDialog] = useState({ open: false, product: null });
  const [manualAsinDialog, setManualAsinDialog] = useState({ open: false, product: null, asinInput: '' });
  const [counts, setCounts] = useState({ all: 0, found: 0, not_found: 0, multiple_found: 0, manual: 0 });
  const [asinStatusStats, setAsinStatusStats] = useState({ all: 0, asin_found: 0, needs_selection: 0, needs_asin: 0, manual_entry: 0 });
  const [deleteAllDialog, setDeleteAllDialog] = useState({ open: false, count: 0 });
  const { hasFeature, promptUpgrade } = useFeatureGate();
  const { showToast } = useToast();

  // Debounce search to reduce API calls
  const debouncedSearch = useDebounce(filters.search, 500);

  // Fetch data with parallel API calls and caching
  const fetchData = useCallback(async (forceRefresh = false) => {
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
      if (filters.asinStatus && filters.asinStatus !== 'all') {
        params.append('asin_status', filters.asinStatus);
        console.log('✅ Adding asin_status to params:', filters.asinStatus);
      }
      params.append('limit', '100');
      
      const url = `/products?${params.toString()}`;
      console.log('🌐 API URL:', url);
      
      // Add timestamp to bypass cache if force refresh
      if (forceRefresh) {
        params.append('_t', Date.now().toString());
      }

      // Parallel API calls for better performance
      const [dealsRes, statsRes] = await Promise.all([
        api.get(url),
        api.get(`/products/stats${forceRefresh ? `?_t=${Date.now()}` : ''}`)
      ]);
      
      console.log('📥 API Response:', {
        status: dealsRes.status,
        hasData: !!dealsRes.data,
        dataKeys: dealsRes.data ? Object.keys(dealsRes.data) : [],
        isArray: Array.isArray(dealsRes.data)
      });

      // Handle different response formats safely
      let dealsData = [];
      if (Array.isArray(dealsRes.data)) {
        dealsData = dealsRes.data;
      } else if (Array.isArray(dealsRes.data?.deals)) {
        dealsData = dealsRes.data.deals;
      } else if (Array.isArray(dealsRes.data?.data)) {
        dealsData = dealsRes.data.data;
      }
      
      // DEBUG: Log filter and results
      console.log('🔍 Filter applied:', filters.asinStatus);
      console.log('📦 Products returned:', dealsData.length);
      if (dealsData.length > 0) {
        console.log('✅ First product ASIN:', dealsData[0].asin);
      }
      
      setDeals(dealsData);
      
      // Ensure stats has all required stage keys
      const statsData = statsRes.data || { stages: {}, total: 0 };
      const defaultStages = { new: 0, analyzing: 0, reviewed: 0, top_products: 0, buy_list: 0, ordered: 0 };
      setStats({
        ...statsData,
        stages: { ...defaultStages, ...(statsData.stages || {}) },
        total: statsData.total || 0
      });
      
      // Get ASIN status counts from deals response
      if (dealsRes.data?.counts) {
        setCounts(dealsRes.data.counts);
      }
      
      // DEBUG: Log actual data structure
      console.log('Products loaded:', dealsData.length, 'items');
      if (dealsData.length > 0) {
        console.log('First product fields:', Object.keys(dealsData[0]));
        console.log('First product sample:', {
          asin: dealsData[0].asin,
          title: dealsData[0].title,
          stage: dealsData[0].stage,
          status: dealsData[0].status,
          product_status: dealsData[0].product_status,
          analysis_status: dealsData[0].analysis_status,
          roi: dealsData[0].roi,
          profit: dealsData[0].profit,
          deal_score: dealsData[0].deal_score
        });
      }
      console.log('Stats data:', statsData);
      
      // Log for debugging
      if (dealsData.length === 0 && statsData.total === 0) {
        console.warn('No products found - view might be empty or missing');
      }
    } catch (err) {
      console.error('Failed to fetch:', err);
      showToast('Failed to load products. Please try refreshing.', 'error');
    } finally {
      setLoading(false);
      fetchInProgress.current = false;
    }
  }, [activeStage, filters.minRoi, filters.minProfit, debouncedSearch, filters.supplier, filters.asinStatus, showToast]);

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

  // Fetch ASIN status stats
  const fetchAsinStatusStats = useCallback(async () => {
    try {
      const response = await api.get('/products/stats/asin-status');
      if (response.data) {
        console.log('📊 ASIN Stats:', response.data); // DEBUG
        setAsinStatusStats(response.data);
      }
    } catch (error) {
      console.error('Failed to fetch ASIN status stats:', error);
    }
  }, []);

  // Initial load - only once
  useEffect(() => {
    fetchData();
    fetchSuppliers();
    fetchAsinStatusStats();
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

  const handleSelectAllProducts = async () => {
    try {
      // Fetch ALL products with current filters to get all deal_ids
      const params = new URLSearchParams();
      if (activeStage) params.append('stage', activeStage);
      if (filters.minRoi) params.append('min_roi', filters.minRoi);
      if (filters.minProfit) params.append('min_profit', filters.minProfit);
      if (debouncedSearch) params.append('search', debouncedSearch);
      if (filters.supplier) params.append('supplier_id', filters.supplier);
      if (filters.asinStatus && filters.asinStatus !== 'all') {
        params.append('asin_status', filters.asinStatus);
      }
      params.append('limit', '10000'); // Get all products
      
      const response = await api.get(`/products?${params.toString()}`);
      let allDeals = [];
      if (Array.isArray(response.data)) {
        allDeals = response.data;
      } else if (Array.isArray(response.data?.deals)) {
        allDeals = response.data.deals;
      } else if (Array.isArray(response.data?.data)) {
        allDeals = response.data.data;
      }
      
      const allDealIds = allDeals.map(d => d.deal_id).filter(Boolean);
      setSelected(allDealIds);
      showToast(`Selected all ${allDealIds.length} products`, 'success');
    } catch (err) {
      handleApiError(err, showToast);
    }
  };

  const handleBulkDelete = async () => {
    if (!selected.length) return;
    
    try {
      await api.post('/products/bulk-action', {
        action: 'delete',
        product_ids: selected
      });
      
      showToast(`Deleted ${selected.length} product${selected.length > 1 ? 's' : ''}`, 'success');
      setSelected([]);
      fetchData(true); // Force refresh
    } catch (err) {
      handleApiError(err, showToast);
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
    // Refresh products list after upload completes
    // Only refresh once, not continuously
    fetchData(true); // Force refresh with cache bypass
    showToast(`Upload complete! ${result?.products_created || 0} products created.`, 'success');
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

  const handleSetAsin = async (productId, asin) => {
    try {
      await api.patch(`/products/${productId}/asin`, { asin });
      showToast('ASIN set successfully. Product is now ready for analysis.', 'success');
      fetchData(true); // Force refresh
    } catch (err) {
      console.error('Failed to set ASIN:', err);
      showToast('Failed to set ASIN: ' + (err.response?.data?.detail || err.message), 'error');
    }
  };

  const handleSelectAsin = async (productId, asin) => {
    try {
      await api.post(`/products/${productId}/select-asin`, { asin });
      showToast('ASIN selected and queued for analysis', 'success');
      setAsinSelectionDialog({ open: false, product: null });
      fetchData(true);
    } catch (err) {
      console.error('Failed to select ASIN:', err);
      showToast('Failed to select ASIN: ' + (err.response?.data?.detail || err.message), 'error');
    }
  };

  const handleManualAsinSubmit = async () => {
    if (!manualAsinDialog.product || manualAsinDialog.asinInput.length !== 10) return;
    
    try {
      await api.patch(`/products/${manualAsinDialog.product.product_id || manualAsinDialog.product.id}/manual-asin`, {
        asin: manualAsinDialog.asinInput.toUpperCase()
      });
      showToast('ASIN set and queued for analysis', 'success');
      setManualAsinDialog({ open: false, product: null, asinInput: '' });
      fetchData(true);
    } catch (err) {
      console.error('Failed to set manual ASIN:', err);
      showToast('Failed to set ASIN: ' + (err.response?.data?.detail || err.message), 'error');
    }
  };

  const handleDeleteClick = (deal) => {
    setDeleteDialog({ open: true, deal, deleting: false });
  };

  const handleDeleteConfirm = async () => {
    if (!deleteDialog.deal) return;
    
    setDeleteDialog(prev => ({ ...prev, deleting: true }));
    
    try {
      await api.delete(`/products/deal/${deleteDialog.deal.deal_id}`);
      showToast(`Product "${deleteDialog.deal.asin}" deleted successfully`, 'success');
      
      // Remove from local state
      setDeals(prev => prev.filter(d => d.deal_id !== deleteDialog.deal.deal_id));
      
      // Also remove from selected if selected
      setSelected(prev => prev.filter(id => id !== deleteDialog.deal.deal_id));
      
      // Refresh stats
      setTimeout(() => fetchData(true), 500);
      
      setDeleteDialog({ open: false, deal: null, deleting: false });
    } catch (err) {
      console.error('Failed to delete product:', err);
      const errorMsg = err.response?.data?.detail || err.message || 'Failed to delete product';
      showToast(errorMsg, 'error');
      setDeleteDialog(prev => ({ ...prev, deleting: false }));
    }
  };

  // Memoized filtered deals for client-side filtering (if needed)
  const filteredDeals = useMemo(() => {
    let filtered = deals;
    
    // Filter by promo if enabled
    if (showPromoOnly) {
      filtered = filtered.filter(d => d.has_promo === true);
    }
    
    // Filter by pricing status
    if (filters.pricingStatus && filters.pricingStatus !== 'all') {
      filtered = filtered.filter(d => {
        const analysis = d.analysis || {};
        const status = analysis.pricing_status || 'complete';
        if (filters.pricingStatus === 'needs_review') {
          return analysis.needs_review || status === 'no_pricing';
        }
        return status === filters.pricingStatus;
      });
    }
    
    return filtered;
  }, [deals, showPromoOnly, filters.pricingStatus]);

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" fontWeight="700">Products</Typography>
        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
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
        <FormControl size="small" sx={{ width: 180 }}>
          <InputLabel>ASIN Status</InputLabel>
          <Select
            value={filters.asinStatus}
            label="ASIN Status"
            onChange={(e) => { 
              const newFilter = e.target.value;
              console.log('🎯 ASIN Status filter changed:', newFilter);
              setFilters({ ...filters, asinStatus: newFilter }); 
              // Force immediate refetch with new filter
              setTimeout(() => fetchData(true), 100);
            }}
          >
            <MenuItem value="all">All Products ({asinStatusStats.all || 0})</MenuItem>
            <MenuItem value="asin_found">ASIN Found ({asinStatusStats.asin_found || 0})</MenuItem>
            <MenuItem value="needs_selection">Needs Selection ({asinStatusStats.needs_selection || 0})</MenuItem>
            <MenuItem value="needs_asin">Needs ASIN ({asinStatusStats.needs_asin || 0})</MenuItem>
            <MenuItem value="manual_entry">Manual Entry ({asinStatusStats.manual_entry || 0})</MenuItem>
          </Select>
        </FormControl>
        <FormControl size="small" sx={{ width: 150 }}>
          <InputLabel>Pricing Status</InputLabel>
          <Select
            value={filters.pricingStatus}
            label="Pricing Status"
            onChange={(e) => { 
              setFilters({ ...filters, pricingStatus: e.target.value }); 
            }}
          >
            <MenuItem value="all">All</MenuItem>
            <MenuItem value="complete">Has Pricing</MenuItem>
            <MenuItem value="no_pricing">No Pricing</MenuItem>
            <MenuItem value="manual">Manual Price</MenuItem>
            <MenuItem value="needs_review">Needs Review</MenuItem>
          </Select>
        </FormControl>
        <FormControlLabel
          control={
            <Checkbox 
              checked={showPromoOnly}
              onChange={(e) => setShowPromoOnly(e.target.checked)}
            />
          }
          label="Has Promo Deal"
        />
        
        <Box sx={{ flex: 1 }} />
        
        {selected.length > 0 && (
          <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
            <Typography variant="body2" color="text.secondary">
              {selected.length} selected
            </Typography>
            <Button
              size="small"
              variant="outlined"
              onClick={handleSelectAllProducts}
            >
              Select All
            </Button>
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
              startIcon={<Trash2 size={14} />}
              onClick={() => setDeleteAllDialog({ open: true, count: selected.length })}
            >
              Delete All
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
        
        <Tooltip title="Refresh products (clears cache)">
          <IconButton onClick={() => {
            // Force refresh by adding timestamp to bypass cache
            fetchData(true);
            showToast('Refreshing products...', 'info');
          }}>
            <RefreshCw size={18} />
          </IconButton>
        </Tooltip>
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
            Upload a CSV or Excel file to get started
          </Typography>
          <Button 
            variant="contained" 
            startIcon={<Upload size={16} />} 
            onClick={() => setShowUploadModal(true)}
          >
            Upload File
          </Button>
        </Card>
      ) : (
        <Card>
          {/* Table Header */}
          <Box sx={{ 
            display: { xs: 'none', md: 'grid' },
            gridTemplateColumns: '40px 50px 140px 1fr 120px 70px 60px 80px 80px 90px 80px 80px 60px',
            p: 1.5, 
            borderBottom: '1px solid',
            borderColor: 'divider',
            bgcolor: 'background.paper',
            gap: 1,
            alignItems: 'center'
          }}>
            <Checkbox
              size="small"
              checked={selected.length === filteredDeals.length && filteredDeals.length > 0}
              indeterminate={selected.length > 0 && selected.length < filteredDeals.length}
              onChange={handleSelectAll}
            />
            <Box></Box> {/* Image column header */}
            <Typography variant="caption" color="text.secondary" fontWeight={600}>ASIN</Typography>
            <Typography variant="caption" color="text.secondary" fontWeight={600}>Product</Typography>
            <Typography variant="caption" color="text.secondary" fontWeight={600}>Supplier</Typography>
            <Typography variant="caption" color="text.secondary" align="center" fontWeight={600}>MOQ</Typography>
            <Typography variant="caption" color="text.secondary" align="center" fontWeight={600}>Pack</Typography>
            <Typography variant="caption" color="text.secondary" align="right" fontWeight={600}>Unit $</Typography>
            <Typography variant="caption" color="text.secondary" align="right" fontWeight={600}>Total $</Typography>
            <Typography variant="caption" color="text.secondary" align="right" fontWeight={600}>ROI</Typography>
            <Typography variant="caption" color="text.secondary" align="right" fontWeight={600}>Profit</Typography>
            <Typography variant="caption" color="text.secondary" fontWeight={600}>Stage</Typography>
            <Typography variant="caption" color="text.secondary" fontWeight={600}>Actions</Typography>
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
                onDelete={handleDeleteClick}
                onSetAsin={handleSetAsin}
                onSelectAsin={(deal) => setAsinSelectionDialog({ open: true, product: deal })}
                onEnterAsin={(deal) => setManualAsinDialog({ open: true, product: deal, asinInput: '' })}
                onOpenManualPrice={(deal, analysis) => setManualPriceDialog({ open: true, deal, analysis })}
                analysis={deal.analysis}
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
                        {deal.title || (deal.roi === undefined && deal.profit === undefined ? 'Pending analysis...' : 'Unknown Product')}
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


      {/* File Upload Modal */}
      <FileUploadModal
        open={showUploadModal}
        onClose={() => setShowUploadModal(false)}
        onComplete={handleUploadComplete}
      />
      <ManualPriceDialog
        open={manualPriceDialog.open}
        onClose={() => setManualPriceDialog({ open: false, deal: null, analysis: null })}
        deal={manualPriceDialog.deal}
        analysis={manualPriceDialog.analysis}
        onSave={() => {
          fetchData(true);
        }}
      />

      {/* ASIN Selection Dialog - Multiple ASINs Found */}
      <Dialog
        open={asinSelectionDialog.open}
        onClose={() => setAsinSelectionDialog({ open: false, product: null })}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Choose the Correct ASIN</DialogTitle>
        <DialogContent>
          {asinSelectionDialog.product && (
            <>
              <Alert severity="info" sx={{ mb: 2 }}>
                Multiple products found for UPC <strong>{asinSelectionDialog.product.upc}</strong>.
                Select the one that matches your supplier's product.
              </Alert>
              <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 2, mt: 2 }}>
                {asinSelectionDialog.product.potential_asins?.map((asinOption) => (
                  <Card
                    key={asinOption.asin}
                    sx={{
                      cursor: 'pointer',
                      '&:hover': { boxShadow: 6 },
                      border: '2px solid transparent',
                      transition: 'all 0.2s'
                    }}
                    onClick={() => handleSelectAsin(
                      asinSelectionDialog.product.product_id || asinSelectionDialog.product.id,
                      asinOption.asin
                    )}
                  >
                    {asinOption.image && (
                      <Box
                        component="img"
                        src={asinOption.image}
                        alt={asinOption.title}
                        sx={{
                          width: '100%',
                          height: 200,
                          objectFit: 'contain',
                          p: 2,
                          bgcolor: 'background.default'
                        }}
                      />
                    )}
                    <DialogContent>
                      <Typography variant="h6" gutterBottom>
                        {asinOption.title || 'Unknown Product'}
                      </Typography>
                      <Typography variant="body2" color="text.secondary" fontFamily="monospace">
                        ASIN: {asinOption.asin}
                      </Typography>
                      {asinOption.brand && (
                        <Typography variant="body2" color="text.secondary">
                          Brand: {asinOption.brand}
                        </Typography>
                      )}
                      {asinOption.category && (
                        <Typography variant="caption" color="text.secondary">
                          Category: {asinOption.category}
                        </Typography>
                      )}
                      <Button
                        variant="contained"
                        fullWidth
                        sx={{ mt: 2 }}
                        onClick={(e) => {
                          e.stopPropagation();
                          handleSelectAsin(
                            asinSelectionDialog.product.product_id || asinSelectionDialog.product.id,
                            asinOption.asin
                          );
                        }}
                      >
                        Select This One
                      </Button>
                    </DialogContent>
                  </Card>
                ))}
              </Box>
            </>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAsinSelectionDialog({ open: false, product: null })}>Cancel</Button>
        </DialogActions>
      </Dialog>

      {/* Manual ASIN Entry Dialog */}
      <Dialog
        open={manualAsinDialog.open}
        onClose={() => setManualAsinDialog({ open: false, product: null, asinInput: '' })}
      >
        <DialogTitle>Enter ASIN Manually</DialogTitle>
        <DialogContent>
          {manualAsinDialog.product && (
            <>
              <Alert severity="info" sx={{ mb: 2 }}>
                No ASIN found for UPC <strong>{manualAsinDialog.product.upc}</strong>.
                Please enter the Amazon ASIN manually.
              </Alert>
              <TextField
                autoFocus
                margin="dense"
                label="ASIN (10 characters)"
                type="text"
                fullWidth
                value={manualAsinDialog.asinInput}
                onChange={(e) => setManualAsinDialog({
                  ...manualAsinDialog,
                  asinInput: e.target.value.toUpperCase().slice(0, 10)
                })}
                inputProps={{ maxLength: 10, style: { fontFamily: 'monospace', fontSize: 14 } }}
                helperText="Example: B07VRZ8TK3"
              />
            </>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setManualAsinDialog({ open: false, product: null, asinInput: '' })}>
            Cancel
          </Button>
          <Button
            onClick={handleManualAsinSubmit}
            variant="contained"
            disabled={manualAsinDialog.asinInput.length !== 10}
          >
            Save ASIN
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog 
        open={deleteDialog.open} 
        onClose={() => !deleteDialog.deleting && setDeleteDialog({ open: false, deal: null, deleting: false })}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <AlertTriangle size={24} style={{ color: habexa.warning.main }} />
          Delete Product
        </DialogTitle>
        <DialogContent>
          <Alert severity="warning" sx={{ mb: 2 }}>
            This action cannot be undone. All analysis data, pricing history, and related information will be permanently lost.
          </Alert>
          {deleteDialog.deal && (
            <Box>
              <Typography variant="body1" fontWeight={600} gutterBottom>
                Are you sure you want to delete this product?
              </Typography>
              <Box sx={{ mt: 2, p: 2, bgcolor: 'background.default', borderRadius: 1 }}>
                <Typography variant="body2" color="text.secondary">ASIN:</Typography>
                <Typography variant="body2" fontFamily="monospace" fontWeight={600}>
                  {deleteDialog.deal.asin}
                </Typography>
                {deleteDialog.deal.title && (
                  <>
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                      Product:
                    </Typography>
                    <Typography variant="body2">
                      {deleteDialog.deal.title}
                    </Typography>
                  </>
                )}
                {(deleteDialog.deal.roi !== undefined || deleteDialog.deal.profit !== undefined) && (
                  <>
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                      Analysis Data:
                    </Typography>
                    <Typography variant="body2">
                      {deleteDialog.deal.roi !== undefined && `ROI: ${deleteDialog.deal.roi?.toFixed(0)}%`}
                      {deleteDialog.deal.roi !== undefined && deleteDialog.deal.profit !== undefined && ' | '}
                      {deleteDialog.deal.profit !== undefined && `Profit: $${deleteDialog.deal.profit?.toFixed(2)}`}
                    </Typography>
                  </>
                )}
              </Box>
              <Typography variant="body2" color="error.main" sx={{ mt: 2, fontWeight: 600 }}>
                ⚠️ All analysis data, profit calculations, and product history will be permanently deleted.
              </Typography>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button 
            onClick={() => setDeleteDialog({ open: false, deal: null, deleting: false })}
            disabled={deleteDialog.deleting}
          >
            Cancel
          </Button>
          <Button 
            onClick={handleDeleteConfirm}
            variant="contained"
            color="error"
            disabled={deleteDialog.deleting}
            startIcon={deleteDialog.deleting ? <CircularProgress size={16} /> : <Trash2 size={16} />}
          >
            {deleteDialog.deleting ? 'Deleting...' : 'Delete Product'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Bulk Delete Confirmation Dialog */}
      <Dialog 
        open={deleteAllDialog.open} 
        onClose={() => setDeleteAllDialog({ open: false, count: 0 })}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <AlertTriangle size={24} style={{ color: habexa.error.main }} />
          Delete All Selected Products
        </DialogTitle>
        <DialogContent>
          <Alert severity="error" sx={{ mb: 2 }}>
            <Typography variant="body2" fontWeight={600}>
              This action cannot be undone!
            </Typography>
            <Typography variant="body2" sx={{ mt: 1 }}>
              All analysis data, pricing history, and related information for {deleteAllDialog.count} product{deleteAllDialog.count !== 1 ? 's' : ''} will be permanently lost.
            </Typography>
          </Alert>
          <Typography variant="body1" fontWeight={600} gutterBottom>
            Are you sure you want to delete {deleteAllDialog.count} product{deleteAllDialog.count !== 1 ? 's' : ''}?
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            This will permanently remove all selected products from your account. This action cannot be reversed.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button 
            onClick={() => setDeleteAllDialog({ open: false, count: 0 })}
          >
            Cancel
          </Button>
          <Button 
            onClick={async () => {
              setDeleteAllDialog({ open: false, count: 0 });
              await handleBulkDelete();
            }}
            variant="contained"
            color="error"
            startIcon={<Trash2 size={16} />}
          >
            Delete All {deleteAllDialog.count} Product{deleteAllDialog.count !== 1 ? 's' : ''}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
