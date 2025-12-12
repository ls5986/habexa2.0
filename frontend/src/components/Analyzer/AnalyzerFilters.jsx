import React from 'react';
import {
  Paper,
  Box,
  Typography,
  TextField,
  Stack,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  IconButton
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';

export default function AnalyzerFilters({
  filters,
  onFiltersChange,
  onClose
}) {
  const handleFilterChange = (key, value) => {
    onFiltersChange({
      ...filters,
      [key]: value
    });
  };

  const handleRangeChange = (key, subKey, value) => {
    onFiltersChange({
      ...filters,
      [key]: {
        ...filters[key],
        [subKey]: value === '' ? null : parseFloat(value)
      }
    });
  };

  const clearFilter = (key) => {
    if (key.includes('.')) {
      const [parent, child] = key.split('.');
      handleRangeChange(parent, child, null);
    } else {
      handleFilterChange(key, key === 'profit_tier' ? [] : null);
    }
  };

  return (
    <Paper sx={{ p: 3, mb: 2 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h6">Advanced Filters</Typography>
        <IconButton onClick={onClose} size="small">
          <CloseIcon />
        </IconButton>
      </Box>

      <Stack spacing={3}>
        {/* Text Search */}
        <TextField
          label="Search (ASIN, Title, SKU)"
          value={filters.search || ''}
          onChange={(e) => handleFilterChange('search', e.target.value)}
          fullWidth
          size="small"
        />

        {/* ROI Range */}
        <Box>
          <Typography variant="body2" fontWeight="bold" mb={1}>
            ROI (%)
          </Typography>
          <Stack direction="row" spacing={2}>
            <TextField
              label="Min"
              type="number"
              value={filters.roi.min ?? ''}
              onChange={(e) => handleRangeChange('roi', 'min', e.target.value)}
              size="small"
              sx={{ flex: 1 }}
            />
            <TextField
              label="Max"
              type="number"
              value={filters.roi.max ?? ''}
              onChange={(e) => handleRangeChange('roi', 'max', e.target.value)}
              size="small"
              sx={{ flex: 1 }}
            />
          </Stack>
        </Box>

        {/* Profit Range */}
        <Box>
          <Typography variant="body2" fontWeight="bold" mb={1}>
            Profit ($)
          </Typography>
          <Stack direction="row" spacing={2}>
            <TextField
              label="Min"
              type="number"
              value={filters.profit.min ?? ''}
              onChange={(e) => handleRangeChange('profit', 'min', e.target.value)}
              size="small"
              sx={{ flex: 1 }}
            />
            <TextField
              label="Max"
              type="number"
              value={filters.profit.max ?? ''}
              onChange={(e) => handleRangeChange('profit', 'max', e.target.value)}
              size="small"
              sx={{ flex: 1 }}
            />
          </Stack>
        </Box>

        {/* Pack Size Range */}
        <Box>
          <Typography variant="body2" fontWeight="bold" mb={1}>
            Pack Size
          </Typography>
          <Stack direction="row" spacing={2}>
            <TextField
              label="Min"
              type="number"
              value={filters.pack_size.min ?? ''}
              onChange={(e) => handleRangeChange('pack_size', 'min', e.target.value)}
              size="small"
              sx={{ flex: 1 }}
            />
            <TextField
              label="Max"
              type="number"
              value={filters.pack_size.max ?? ''}
              onChange={(e) => handleRangeChange('pack_size', 'max', e.target.value)}
              size="small"
              sx={{ flex: 1 }}
            />
          </Stack>
        </Box>

        {/* Profit Tier */}
        <FormControl fullWidth size="small">
          <InputLabel>Profit Tier</InputLabel>
          <Select
            multiple
            value={filters.profit_tier || []}
            onChange={(e) => handleFilterChange('profit_tier', e.target.value)}
            renderValue={(selected) => (
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                {selected.map((value) => (
                  <Chip key={value} label={value} size="small" />
                ))}
              </Box>
            )}
          >
            <MenuItem value="excellent">Excellent (50%+)</MenuItem>
            <MenuItem value="good">Good (30-50%)</MenuItem>
            <MenuItem value="acceptable">Acceptable (15-30%)</MenuItem>
            <MenuItem value="marginal">Marginal (5-15%)</MenuItem>
            <MenuItem value="unprofitable">Unprofitable (&lt;5%)</MenuItem>
          </Select>
        </FormControl>

        {/* Boolean Filters */}
        <Stack direction="row" spacing={2}>
          <FormControl fullWidth size="small">
            <InputLabel>Has Promo</InputLabel>
            <Select
              value={filters.has_promo === null ? '' : filters.has_promo}
              onChange={(e) => handleFilterChange('has_promo', e.target.value === '' ? null : e.target.value)}
            >
              <MenuItem value="">All</MenuItem>
              <MenuItem value={true}>Yes</MenuItem>
              <MenuItem value={false}>No</MenuItem>
            </Select>
          </FormControl>

          <FormControl fullWidth size="small">
            <InputLabel>In Stock</InputLabel>
            <Select
              value={filters.in_stock === null ? '' : filters.in_stock}
              onChange={(e) => handleFilterChange('in_stock', e.target.value === '' ? null : e.target.value)}
            >
              <MenuItem value="">All</MenuItem>
              <MenuItem value={true}>Yes</MenuItem>
              <MenuItem value={false}>No</MenuItem>
            </Select>
          </FormControl>
        </Stack>

        {/* Active Filters Chips */}
        {(filters.search || 
          filters.roi.min !== null || filters.roi.max !== null ||
          filters.profit.min !== null || filters.profit.max !== null ||
          filters.pack_size.min || filters.pack_size.max ||
          filters.profit_tier.length > 0 ||
          filters.has_promo !== null || filters.in_stock !== null) && (
          <Box>
            <Typography variant="body2" fontWeight="bold" mb={1}>
              Active Filters
            </Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap" gap={1}>
              {filters.search && (
                <Chip
                  label={`Search: ${filters.search}`}
                  onDelete={() => clearFilter('search')}
                  size="small"
                />
              )}
              {(filters.roi.min !== null || filters.roi.max !== null) && (
                <Chip
                  label={`ROI: ${filters.roi.min ?? '0'}% - ${filters.roi.max ?? '∞'}%`}
                  onDelete={() => {
                    handleFilterChange('roi', { min: null, max: null });
                  }}
                  size="small"
                />
              )}
              {(filters.profit.min !== null || filters.profit.max !== null) && (
                <Chip
                  label={`Profit: $${filters.profit.min ?? '0'} - $${filters.profit.max ?? '∞'}`}
                  onDelete={() => {
                    handleFilterChange('profit', { min: null, max: null });
                  }}
                  size="small"
                />
              )}
              {filters.profit_tier.length > 0 && (
                <Chip
                  label={`Tier: ${filters.profit_tier.join(', ')}`}
                  onDelete={() => clearFilter('profit_tier')}
                  size="small"
                />
              )}
              {filters.has_promo !== null && (
                <Chip
                  label={`Promo: ${filters.has_promo ? 'Yes' : 'No'}`}
                  onDelete={() => clearFilter('has_promo')}
                  size="small"
                />
              )}
              {filters.in_stock !== null && (
                <Chip
                  label={`Stock: ${filters.in_stock ? 'Yes' : 'No'}`}
                  onDelete={() => clearFilter('in_stock')}
                  size="small"
                />
              )}
            </Stack>
          </Box>
        )}

        {/* Actions */}
        <Stack direction="row" spacing={2} justifyContent="flex-end">
          <Button
            variant="outlined"
            onClick={() => {
              onFiltersChange({
                search: '',
                roi: { min: null, max: null },
                profit: { min: null, max: null },
                pack_size: { min: null, max: null },
                profit_tier: [],
                has_promo: null,
                in_stock: null
              });
            }}
          >
            Clear All
          </Button>
          <Button variant="contained" onClick={onClose}>
            Apply Filters
          </Button>
        </Stack>
      </Stack>
    </Paper>
  );
}

