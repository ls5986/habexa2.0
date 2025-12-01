import { Box, Typography, Tabs, Tab, TextField, Select, MenuItem, FormControl, InputLabel, Button, Chip } from '@mui/material';
import { useState } from 'react';
import { Zap, Flame, Clock, Star, Search, MessageSquare } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useDeals } from '../hooks/useDeals';
import DealCard from '../components/common/DealCard';
import DealDetailPanel from '../components/features/deals/DealDetailPanel';
import { DealCardSkeleton } from '../components/common/LoadingSkeleton';
import EmptyState from '../components/common/EmptyState';
import { Inbox } from 'lucide-react';

const Deals = () => {
  const navigate = useNavigate();
  const [tab, setTab] = useState(0);
  const [filters, setFilters] = useState({
    status: null,
    minRoi: null,
    category: null,
    gating: null,
  });
  const [selectedDeals, setSelectedDeals] = useState(new Set());

  const statusFilter = tab === 0 ? null : tab === 1 ? 'analyzed' : tab === 2 ? 'pending' : 'saved';
  const { deals, loading, saveDeal, dismissDeal } = useDeals({
    ...filters,
    status: statusFilter,
  });

  const [selectedDeal, setSelectedDeal] = useState(null);

  const filteredDeals = deals.filter(deal => {
    if (tab === 1) return deal.is_profitable && deal.roi >= 20;
    if (tab === 2) return deal.status === 'pending';
    if (tab === 3) return deal.status === 'saved';
    return true;
  });

  const handleSave = async (deal) => {
    try {
      await saveDeal(deal.id);
    } catch (error) {
      console.error('Failed to save deal:', error);
    }
  };

  const handleDismiss = async (deal) => {
    try {
      await dismissDeal(deal.id);
    } catch (error) {
      console.error('Failed to dismiss deal:', error);
    }
  };

  const profitableCount = deals.filter(d => d.is_profitable && d.roi >= 20).length;
  const pendingCount = deals.filter(d => d.status === 'pending').length;
  const savedCount = deals.filter(d => d.status === 'saved').length;

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" fontWeight="700" color="white">
            Deal Feed
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Analyze and track profitable products
          </Typography>
        </Box>
        
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          {/* Live indicator */}
          <Chip
            icon={
              <Box 
                sx={{ 
                  width: 8, 
                  height: 8, 
                  borderRadius: '50%', 
                  bgcolor: '#10B981',
                  '@keyframes pulse': {
                    '0%, 100%': { opacity: 1 },
                    '50%': { opacity: 0.5 },
                  },
                  animation: 'pulse 2s infinite',
                }} 
              />
            }
            label="Live"
            size="small"
            sx={{ 
              bgcolor: 'rgba(16, 185, 129, 0.1)', 
              color: '#10B981',
              border: '1px solid rgba(16, 185, 129, 0.2)'
            }}
          />
          
          {/* Quick Analyze button moved to TopBar */}
        </Box>
      </Box>

      {/* Filters - Better Styled */}
      <Box 
        sx={{ 
          display: 'flex', 
          gap: 2, 
          mb: 3,
          p: 2,
          borderRadius: 2,
          bgcolor: '#1A1A2E',
          border: '1px solid #2D2D3D'
        }}
      >
        <FormControl size="small" sx={{ minWidth: 140 }}>
          <InputLabel sx={{ color: '#A0A0B0' }}>Channel</InputLabel>
          <Select
            value={filters.supplierId || ''}
            label="Channel"
            onChange={(e) => setFilters({ ...filters, supplierId: e.target.value })}
            sx={{
              bgcolor: '#252540',
              '& .MuiOutlinedInput-notchedOutline': { borderColor: '#2D2D3D' },
              '&:hover .MuiOutlinedInput-notchedOutline': { borderColor: '#7C3AED' },
            }}
          >
            <MenuItem value="">All Channels</MenuItem>
          </Select>
        </FormControl>
        
        <FormControl size="small" sx={{ minWidth: 140 }}>
          <InputLabel sx={{ color: '#A0A0B0' }}>Min ROI</InputLabel>
          <Select
            value={filters.minRoi || ''}
            label="Min ROI"
            onChange={(e) => setFilters({ ...filters, minRoi: e.target.value })}
            sx={{
              bgcolor: '#252540',
              '& .MuiOutlinedInput-notchedOutline': { borderColor: '#2D2D3D' },
              '&:hover .MuiOutlinedInput-notchedOutline': { borderColor: '#7C3AED' },
            }}
          >
            <MenuItem value="">Any</MenuItem>
            <MenuItem value={20}>≥ 20%</MenuItem>
            <MenuItem value={30}>≥ 30%</MenuItem>
            <MenuItem value={40}>≥ 40%</MenuItem>
          </Select>
        </FormControl>
        
        <FormControl size="small" sx={{ minWidth: 140 }}>
          <InputLabel sx={{ color: '#A0A0B0' }}>Category</InputLabel>
          <Select
            value={filters.category || ''}
            label="Category"
            onChange={(e) => setFilters({ ...filters, category: e.target.value })}
            sx={{
              bgcolor: '#252540',
              '& .MuiOutlinedInput-notchedOutline': { borderColor: '#2D2D3D' },
              '&:hover .MuiOutlinedInput-notchedOutline': { borderColor: '#7C3AED' },
            }}
          >
            <MenuItem value="">All Categories</MenuItem>
          </Select>
        </FormControl>
        
        <FormControl size="small" sx={{ minWidth: 140 }}>
          <InputLabel sx={{ color: '#A0A0B0' }}>Gating</InputLabel>
          <Select
            value={filters.gating || ''}
            label="Gating"
            onChange={(e) => setFilters({ ...filters, gating: e.target.value })}
            sx={{
              bgcolor: '#252540',
              '& .MuiOutlinedInput-notchedOutline': { borderColor: '#2D2D3D' },
              '&:hover .MuiOutlinedInput-notchedOutline': { borderColor: '#7C3AED' },
            }}
          >
            <MenuItem value="">Any</MenuItem>
            <MenuItem value="ungated">Ungated</MenuItem>
            <MenuItem value="gated">Gated</MenuItem>
          </Select>
        </FormControl>
        
        <TextField
          size="small"
          placeholder="Search ASIN..."
          InputProps={{
            startAdornment: <Search size={18} style={{ color: '#6B6B7B', marginRight: 8 }} />,
          }}
          sx={{
            ml: 'auto',
            minWidth: 200,
            '& .MuiOutlinedInput-root': {
              bgcolor: '#252540',
              '& fieldset': { borderColor: '#2D2D3D' },
              '&:hover fieldset': { borderColor: '#7C3AED' },
            }
          }}
        />
      </Box>

      {/* Tabs - Better Styled */}
      <Tabs
        value={tab}
        onChange={(e, v) => setTab(v)}
        sx={{
          mb: 3,
          '& .MuiTab-root': {
            color: '#A0A0B0',
            textTransform: 'none',
            fontWeight: 500,
            '&.Mui-selected': { color: '#FFFFFF' },
          },
          '& .MuiTabs-indicator': {
            bgcolor: '#7C3AED',
            height: 3,
            borderRadius: '3px 3px 0 0',
          },
        }}
      >
        <Tab label={`All (${deals.length})`} />
        <Tab icon={<Flame size={16} />} iconPosition="start" label={`Profitable (${profitableCount})`} />
        <Tab icon={<Clock size={16} />} iconPosition="start" label={`Pending (${pendingCount})`} />
        <Tab icon={<Star size={16} />} iconPosition="start" label={`Saved (${savedCount})`} />
      </Tabs>

      {/* Deal List */}
      {loading ? (
        <Box display="flex" flexDirection="column" gap={2}>
          {[1, 2, 3].map(i => (
            <DealCardSkeleton key={i} />
          ))}
        </Box>
      ) : filteredDeals.length === 0 ? (
        <Box
          sx={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            py: 10,
            px: 4,
            borderRadius: 3,
            bgcolor: '#1A1A2E',
            border: '1px dashed #2D2D3D',
          }}
        >
          <Box
            sx={{
              width: 80,
              height: 80,
              borderRadius: '50%',
              bgcolor: 'rgba(124, 58, 237, 0.1)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              mb: 3,
            }}
          >
            <Inbox size={40} style={{ color: '#7C3AED' }} />
          </Box>
          
          <Typography variant="h6" fontWeight="600" color="white" gutterBottom>
            No deals yet
          </Typography>
          
          <Typography variant="body2" color="text.secondary" textAlign="center" maxWidth={400} mb={3}>
            Start by analyzing products or connect your Telegram channels to automatically extract deals from supplier messages.
          </Typography>
          
          <Box sx={{ display: 'flex', gap: 2 }}>
            <Button
              variant="contained"
              startIcon={<Zap size={18} />}
              onClick={() => navigate('/analyze')}
              sx={{ background: 'linear-gradient(135deg, #7C3AED 0%, #5B21B6 100%)' }}
            >
              Analyze Product
            </Button>
            <Button
              variant="outlined"
              startIcon={<MessageSquare size={18} />}
              onClick={() => navigate('/settings?tab=integrations')}
              sx={{ borderColor: '#2D2D3D', color: '#A0A0B0' }}
            >
              Connect Telegram
            </Button>
          </Box>
        </Box>
      ) : (
        <Box display="flex" flexDirection="column" gap={2}>
          {filteredDeals.map((deal) => (
            <DealCard
              key={deal.id}
              deal={deal}
              onView={(deal) => setSelectedDeal(deal)}
              onSave={handleSave}
              onDismiss={handleDismiss}
            />
          ))}
        </Box>
      )}

      <DealDetailPanel
        deal={selectedDeal}
        open={!!selectedDeal}
        onClose={() => setSelectedDeal(null)}
        onSave={() => selectedDeal && handleSave(selectedDeal)}
        onOrder={() => {
          // TODO: Implement order functionality
          console.log('Order:', selectedDeal);
        }}
      />
    </Box>
  );
};

export default Deals;

