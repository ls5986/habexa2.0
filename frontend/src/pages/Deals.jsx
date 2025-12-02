import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box, Typography, Card, Button, Chip, CircularProgress,
  IconButton, Tabs, Tab, TextField, InputAdornment
} from '@mui/material';
import { Search, RefreshCw, ExternalLink, Package, TrendingUp, Clock, Zap } from 'lucide-react';
import api from '../services/api';

export default function Deals() {
  const [deals, setDeals] = useState([]);
  const [stats, setStats] = useState({ total: 0, pending: 0, analyzed: 0, profitable: 0 });
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState(0);
  const [search, setSearch] = useState('');
  const navigate = useNavigate();
  const fetchedRef = useRef(false);

  // Single fetch on mount - NO dependencies that cause re-fetch
  useEffect(() => {
    if (fetchedRef.current) return;
    fetchedRef.current = true;
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    const start = Date.now();
    
    try {
      // PARALLEL fetch - both at same time
      const [dealsRes, statsRes] = await Promise.all([
        api.get('/deals?limit=50'),
        api.get('/deals/stats')
      ]);
      
      console.log(`✅ API calls took ${Date.now() - start}ms`);
      
      setDeals(dealsRes.data.deals || dealsRes.data || []);
      setStats(statsRes.data || { total: 0, pending: 0, analyzed: 0, profitable: 0 });
    } catch (err) {
      console.error('Fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  // Filter deals by tab - NO API call, just filter existing data
  const filteredDeals = React.useMemo(() => {
    let result = deals;
    
    if (tab === 1) {
      result = deals.filter(d => d.analysis?.roi >= 30);
    } else if (tab === 2) {
      result = deals.filter(d => d.status === 'pending' || !d.status);
    }
    
    if (search) {
      result = result.filter(d => d.asin?.toLowerCase().includes(search.toLowerCase()));
    }
    
    return result;
  }, [deals, tab, search]);

  const handleRefresh = () => {
    fetchedRef.current = false;
    fetchData();
  };

  const handleAnalyzeAll = async () => {
    try {
      await api.post('/deals/analyze-batch', { analyze_all_pending: true });
      handleRefresh();
    } catch (err) {
      console.error('Batch analysis failed:', err);
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" fontWeight="700">Deal Feed</Typography>
          <Typography variant="body2" color="text.secondary">
            {stats.total} deals - {stats.pending} pending - {stats.profitable} profitable
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 2 }}>
          {stats.pending > 0 && (
            <Button variant="contained" startIcon={<Zap size={16} />} onClick={handleAnalyzeAll}>
              Analyze All ({stats.pending})
            </Button>
          )}
          <IconButton onClick={handleRefresh}><RefreshCw size={20} /></IconButton>
        </Box>
      </Box>

      {/* Tabs - client-side filtering only */}
      <Tabs value={tab} onChange={(e, v) => setTab(v)} sx={{ mb: 3 }}>
        <Tab label={`All (${stats.total})`} />
        <Tab icon={<TrendingUp size={14} />} iconPosition="start" label={`Profitable (${stats.profitable})`} />
        <Tab icon={<Clock size={14} />} iconPosition="start" label={`Pending (${stats.pending})`} />
      </Tabs>

      {/* Search */}
      <TextField
        size="small"
        placeholder="Search ASIN..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        sx={{ mb: 3, width: 250 }}
        InputProps={{
          startAdornment: <InputAdornment position="start"><Search size={16} /></InputAdornment>
        }}
      />

      {/* Deals List - Simple cards */}
      {filteredDeals.length === 0 ? (
        <Card sx={{ p: 4, textAlign: 'center' }}>
          <Package size={48} color="#666" />
          <Typography variant="h6" sx={{ mt: 2 }}>No deals found</Typography>
        </Card>
      ) : (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          {filteredDeals.map((deal) => (
            <DealCard key={deal.id} deal={deal} onClick={() => navigate(`/deals/${deal.id}`)} />
          ))}
        </Box>
      )}
    </Box>
  );
}

// Separate component to prevent re-renders
const DealCard = React.memo(({ deal, onClick }) => {
  const analysis = deal.analysis;
  const roi = analysis?.roi || 0;
  
  return (
    <Card 
      onClick={onClick}
      sx={{ 
        p: 2, 
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        gap: 2,
        '&:hover': { bgcolor: 'action.hover' }
      }}
    >
      {/* Image */}
      <Box sx={{ width: 50, height: 50, bgcolor: '#252540', borderRadius: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
        {analysis?.image_url ? (
          <img src={analysis.image_url} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: 4 }} />
        ) : (
          <Package size={24} color="#666" />
        )}
      </Box>

      {/* Info */}
      <Box sx={{ flex: 1, minWidth: 0 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Typography variant="body2" fontFamily="monospace">{deal.asin}</Typography>
          <Chip 
            label={deal.status || 'pending'} 
            size="small" 
            color={deal.status === 'analyzed' ? 'success' : 'warning'}
            sx={{ height: 20, fontSize: 11 }}
          />
        </Box>
        <Typography variant="body2" noWrap color="text.secondary">
          {analysis?.product_title || deal.product_title || 'Pending analysis...'}
        </Typography>
      </Box>

      {/* Stats */}
      <Box sx={{ display: 'flex', gap: 3, alignItems: 'center' }}>
        <Box sx={{ textAlign: 'right' }}>
          <Typography variant="caption" color="text.secondary">Buy</Typography>
          <Typography variant="body2">${deal.buy_cost?.toFixed(2) || '—'}</Typography>
        </Box>
        {analysis && (
          <>
            <Box sx={{ textAlign: 'right' }}>
              <Typography variant="caption" color="text.secondary">Profit</Typography>
              <Typography variant="body2" color={analysis.profit > 0 ? 'success.main' : 'error.main'}>
                ${analysis.profit?.toFixed(2) || '—'}
              </Typography>
            </Box>
            <Box sx={{ textAlign: 'right' }}>
              <Typography variant="caption" color="text.secondary">ROI</Typography>
              <Typography variant="body2" fontWeight="700" color={roi >= 30 ? 'success.main' : 'warning.main'}>
                {roi.toFixed(0)}%
              </Typography>
            </Box>
          </>
        )}
      </Box>

      {/* Amazon Link */}
      <IconButton 
        size="small" 
        component="a" 
        href={`https://amazon.com/dp/${deal.asin}`}
        target="_blank"
        onClick={(e) => e.stopPropagation()}
      >
        <ExternalLink size={16} />
      </IconButton>
    </Card>
  );
});
