import React from 'react';
import {
  Box,
  Paper,
  Stack,
  Button,
  Typography,
  Chip,
  IconButton
} from '@mui/material';
import ShoppingCartIcon from '@mui/icons-material/ShoppingCart';
import VisibilityOffIcon from '@mui/icons-material/VisibilityOff';
import DeleteIcon from '@mui/icons-material/Delete';
import CloseIcon from '@mui/icons-material/Close';
import FavoriteIcon from '@mui/icons-material/Favorite';
import FavoriteBorderIcon from '@mui/icons-material/FavoriteBorder';

export default function AnalyzerBulkActions({
  selectedCount,
  selectedProducts,
  onAddToOrder,
  onHide,
  onDelete,
  onFavorite,
  onClearSelection
}) {
  return (
    <Paper
      sx={{
        p: 2,
        mb: 2,
        bgcolor: 'primary.light',
        color: 'primary.contrastText',
        position: 'sticky',
        top: 0,
        zIndex: 10
      }}
    >
      <Box display="flex" justifyContent="space-between" alignItems="center">
        <Stack direction="row" spacing={2} alignItems="center">
          <Typography variant="body1" fontWeight="bold">
            {selectedCount} product{selectedCount !== 1 ? 's' : ''} selected
          </Typography>

          <Chip
            label={`${selectedCount} selected`}
            size="small"
            sx={{
              bgcolor: 'rgba(255, 255, 255, 0.2)',
              color: 'inherit'
            }}
          />
        </Stack>

        <Stack direction="row" spacing={1}>
          {onFavorite && (
            <Button
              variant="contained"
              size="small"
              startIcon={<FavoriteIcon />}
              onClick={() => onFavorite(selectedProducts)}
              sx={{
                bgcolor: 'rgba(255, 255, 255, 0.2)',
                '&:hover': { bgcolor: 'rgba(255, 255, 255, 0.3)' }
              }}
            >
              Favorite
            </Button>
          )}

          {onAddToOrder && (
            <Button
              variant="contained"
              size="small"
              startIcon={<ShoppingCartIcon />}
              onClick={() => onAddToOrder(selectedProducts)}
              sx={{
                bgcolor: 'rgba(255, 255, 255, 0.2)',
                '&:hover': { bgcolor: 'rgba(255, 255, 255, 0.3)' }
              }}
            >
              Add to Order
            </Button>
          )}

          {onHide && (
            <Button
              variant="contained"
              size="small"
              startIcon={<VisibilityOffIcon />}
              onClick={() => onHide(selectedProducts)}
              sx={{
                bgcolor: 'rgba(255, 255, 255, 0.2)',
                '&:hover': { bgcolor: 'rgba(255, 255, 255, 0.3)' }
              }}
            >
              Hide
            </Button>
          )}

          {onDelete && (
            <Button
              variant="contained"
              size="small"
              startIcon={<DeleteIcon />}
              onClick={() => onDelete(selectedProducts)}
              color="error"
              sx={{
                bgcolor: 'rgba(255, 255, 255, 0.2)',
                '&:hover': { bgcolor: 'rgba(255, 255, 255, 0.3)' }
              }}
            >
              Delete
            </Button>
          )}

          {onClearSelection && (
            <IconButton
              size="small"
              onClick={onClearSelection}
              sx={{ color: 'inherit' }}
            >
              <CloseIcon />
            </IconButton>
          )}
        </Stack>
      </Box>
    </Paper>
  );
}

