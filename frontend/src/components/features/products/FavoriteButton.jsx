import React, { useState, useEffect } from 'react';
import { IconButton, Tooltip, CircularProgress } from '@mui/material';
import { Star, StarBorder } from '@mui/icons-material';
import { useToast } from '../../../context/ToastContext';
import api from '../../../services/api';

const FavoriteButton = ({ productId, dealId, size = 'medium', onToggle }) => {
  const [isFavorite, setIsFavorite] = useState(false);
  const [loading, setLoading] = useState(false);
  const [checking, setChecking] = useState(true);
  const { showToast } = useToast();

  // Use dealId if provided, otherwise try to get it from product
  const effectiveDealId = dealId;

  // Check if product is already favorited
  useEffect(() => {
    if (!effectiveDealId && !productId) {
      setChecking(false);
      return;
    }
    
    const checkFavorite = async () => {
      try {
        // Try to check favorite status via deal_id endpoint
        if (effectiveDealId) {
          // Get product details to check is_favorite field
          const response = await api.get(`/products?deal_id=${effectiveDealId}`);
          if (response.data?.deals && response.data.deals.length > 0) {
            const deal = response.data.deals[0];
            setIsFavorite(deal.is_favorite || false);
          }
        } else if (productId) {
          // Fallback: try favorites check endpoint
          try {
            const response = await api.get(`/favorites/check/${productId}`);
            setIsFavorite(response.data.is_favorite || false);
          } catch {
            // If endpoint doesn't exist, try getting product
            const response = await api.get(`/products/${productId}`);
            setIsFavorite(response.data.is_favorite || false);
          }
        }
      } catch (error) {
        console.error('Error checking favorite status:', error);
        // Default to false if check fails
        setIsFavorite(false);
      } finally {
        setChecking(false);
      }
    };
    
    checkFavorite();
  }, [productId, effectiveDealId]);

  const handleToggle = async (e) => {
    e.stopPropagation(); // Prevent row click events
    
    if ((!effectiveDealId && !productId) || loading) return;
    
    setLoading(true);
    
    try {
      // Use PATCH /products/deal/{deal_id}/favorite if dealId available (preferred)
      if (effectiveDealId) {
        const response = await api.patch(`/products/deal/${effectiveDealId}/favorite`);
        const newFavoriteState = response.data?.is_favorite ?? !isFavorite;
        setIsFavorite(newFavoriteState);
        showToast(
          newFavoriteState ? 'Added to favorites!' : 'Removed from favorites',
          newFavoriteState ? 'success' : 'info'
        );
      } else if (productId) {
        // Fallback: use /favorites endpoint
        if (isFavorite) {
          await api.delete(`/favorites/${productId}`);
          setIsFavorite(false);
          showToast('Removed from favorites', 'info');
        } else {
          await api.post('/favorites', { product_id: productId });
          setIsFavorite(true);
          showToast('Added to favorites!', 'success');
        }
      }
      
      if (onToggle) {
        onToggle(!isFavorite);
      }
    } catch (error) {
      console.error('Error toggling favorite:', error);
      const errorMsg = error.response?.data?.detail || error.message || 'Failed to update favorites';
      showToast(errorMsg, 'error');
    } finally {
      setLoading(false);
    }
  };

  if (checking) {
    return (
      <IconButton size={size} disabled>
        <CircularProgress size={20} />
      </IconButton>
    );
  }

  return (
    <Tooltip title={isFavorite ? 'Remove from favorites' : 'Add to favorites'}>
      <IconButton
        onClick={handleToggle}
        disabled={loading}
        size={size}
        sx={{
          color: isFavorite ? 'warning.main' : 'action.disabled',
          '&:hover': {
            color: isFavorite ? 'warning.dark' : 'warning.light',
          },
        }}
      >
        {loading ? (
          <CircularProgress size={20} />
        ) : isFavorite ? (
          <Star />
        ) : (
          <StarBorder />
        )}
      </IconButton>
    </Tooltip>
  );
};

export default FavoriteButton;

