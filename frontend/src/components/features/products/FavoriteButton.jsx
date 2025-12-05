import React, { useState, useEffect } from 'react';
import { IconButton, Tooltip, CircularProgress } from '@mui/material';
import { Star, StarBorder } from '@mui/icons-material';
import { useToast } from '../../../context/ToastContext';
import api from '../../../services/api';

const FavoriteButton = ({ productId, size = 'medium', onToggle }) => {
  const [isFavorite, setIsFavorite] = useState(false);
  const [loading, setLoading] = useState(false);
  const [checking, setChecking] = useState(true);
  const { showToast } = useToast();

  // Check if product is already favorited
  useEffect(() => {
    if (!productId) return;
    
    const checkFavorite = async () => {
      try {
        const response = await api.get(`/favorites/check/${productId}`);
        setIsFavorite(response.data.is_favorite || false);
      } catch (error) {
        console.error('Error checking favorite status:', error);
      } finally {
        setChecking(false);
      }
    };
    
    checkFavorite();
  }, [productId]);

  const handleToggle = async (e) => {
    e.stopPropagation(); // Prevent row click events
    
    if (!productId || loading) return;
    
    setLoading(true);
    
    try {
      if (isFavorite) {
        await api.delete(`/favorites/${productId}`);
        setIsFavorite(false);
        showToast('Removed from favorites', 'info');
      } else {
        await api.post('/favorites', { product_id: productId });
        setIsFavorite(true);
        showToast('Added to favorites!', 'success');
      }
      
      if (onToggle) {
        onToggle(!isFavorite);
      }
    } catch (error) {
      console.error('Error toggling favorite:', error);
      showToast('Failed to update favorites', 'error');
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

