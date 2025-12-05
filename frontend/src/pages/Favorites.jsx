import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Chip,
  CircularProgress,
  Alert,
  Tooltip,
  Button,
} from '@mui/material';
import {
  Delete as DeleteIcon,
  OpenInNew as OpenIcon,
  Star as StarIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useToast } from '../context/ToastContext';
import api from '../services/api';

const Favorites = () => {
  const [favorites, setFavorites] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();
  const { showToast } = useToast();

  const fetchFavorites = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await api.get('/favorites');
      setFavorites(response.data || []);
    } catch (err) {
      console.error('Error fetching favorites:', err);
      setError('Failed to load favorites');
      showToast('Failed to load favorites', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFavorites();
  }, []);

  const handleRemove = async (productId) => {
    try {
      await api.delete(`/favorites/${productId}`);
      setFavorites(favorites.filter(f => f.product_id !== productId));
      showToast('Removed from favorites', 'info');
    } catch (err) {
      console.error('Error removing favorite:', err);
      showToast('Failed to remove', 'error');
    }
  };

  const handleOpenProduct = (productId) => {
    navigate(`/products?selected=${productId}`);
  };

  const formatCurrency = (value) => {
    if (value == null) return '—';
    return `$${Number(value).toFixed(2)}`;
  };

  const formatPercent = (value) => {
    if (value == null) return '—';
    return `${Number(value).toFixed(1)}%`;
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
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <StarIcon sx={{ color: 'warning.main', fontSize: 32 }} />
          <Typography variant="h4" fontWeight="bold">
            Favorites
          </Typography>
          <Chip label={favorites.length} color="primary" size="small" sx={{ ml: 1 }} />
        </Box>
        
        <Button
          startIcon={<RefreshIcon />}
          onClick={fetchFavorites}
          variant="outlined"
        >
          Refresh
        </Button>
      </Box>

      {/* Error State */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {/* Empty State */}
      {!error && favorites.length === 0 && (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <StarIcon sx={{ fontSize: 64, color: 'action.disabled', mb: 2 }} />
          <Typography variant="h6" color="text.secondary" gutterBottom>
            No favorites yet
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Click the star icon on any product to add it to your favorites.
          </Typography>
          <Button variant="contained" onClick={() => navigate('/products')}>
            Browse Products
          </Button>
        </Paper>
      )}

      {/* Favorites Table */}
      {favorites.length > 0 && (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Product</TableCell>
                <TableCell>ASIN</TableCell>
                <TableCell align="right">Buy Cost</TableCell>
                <TableCell align="right">Sell Price</TableCell>
                <TableCell align="right">ROI</TableCell>
                <TableCell align="right">Profit</TableCell>
                <TableCell align="center">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {favorites.map((fav) => (
                <TableRow 
                  key={fav.id}
                  hover
                  sx={{ cursor: 'pointer' }}
                  onClick={() => handleOpenProduct(fav.product_id)}
                >
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                      {fav.image_url && (
                        <Box
                          component="img"
                          src={fav.image_url}
                          alt={fav.title}
                          sx={{ width: 40, height: 40, objectFit: 'contain', borderRadius: 1 }}
                        />
                      )}
                      <Box>
                        <Typography variant="body2" fontWeight="medium" noWrap sx={{ maxWidth: 300 }}>
                          {fav.title || 'Unknown Product'}
                        </Typography>
                        {fav.brand && (
                          <Typography variant="caption" color="text.secondary">
                            {fav.brand}
                          </Typography>
                        )}
                      </Box>
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Chip label={fav.asin} size="small" variant="outlined" />
                  </TableCell>
                  <TableCell align="right">{formatCurrency(fav.buy_cost)}</TableCell>
                  <TableCell align="right">{formatCurrency(fav.sell_price)}</TableCell>
                  <TableCell align="right">
                    {fav.roi != null && (
                      <Chip
                        label={formatPercent(fav.roi)}
                        size="small"
                        color={fav.roi >= 30 ? 'success' : fav.roi >= 15 ? 'warning' : 'error'}
                      />
                    )}
                    {fav.roi == null && '—'}
                  </TableCell>
                  <TableCell align="right">
                    <Typography
                      color={fav.profit > 0 ? 'success.main' : 'error.main'}
                      fontWeight="medium"
                    >
                      {formatCurrency(fav.profit)}
                    </Typography>
                  </TableCell>
                  <TableCell align="center">
                    <Tooltip title="Open product">
                      <IconButton
                        size="small"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleOpenProduct(fav.product_id);
                        }}
                      >
                        <OpenIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Remove from favorites">
                      <IconButton
                        size="small"
                        color="error"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleRemove(fav.product_id);
                        }}
                      >
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Box>
  );
};

export default Favorites;

