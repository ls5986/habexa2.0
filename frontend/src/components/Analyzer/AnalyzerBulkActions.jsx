import React, { useState } from 'react';
import {
  Box,
  Paper,
  Stack,
  Button,
  Typography,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Alert,
  Divider
} from '@mui/material';
import ShoppingCartIcon from '@mui/icons-material/ShoppingCart';
import VisibilityOffIcon from '@mui/icons-material/VisibilityOff';
import DeleteIcon from '@mui/icons-material/Delete';
import CloseIcon from '@mui/icons-material/Close';
import FavoriteIcon from '@mui/icons-material/Favorite';
import EditIcon from '@mui/icons-material/Edit';
import FileDownloadIcon from '@mui/icons-material/FileDownload';
import RefreshIcon from '@mui/icons-material/Refresh';

export default function AnalyzerBulkActions({
  selectedCount,
  selectedProducts,
  onAddToOrder,
  onHide,
  onDelete,
  onFavorite,
  onUpdateCosts,
  onRefreshData,
  onExport,
  onClearSelection
}) {
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [showUpdateCosts, setShowUpdateCosts] = useState(false);
  const [costUpdate, setCostUpdate] = useState({
    wholesale_cost: '',
    pack_size: '',
    moq: ''
  });
  const handleDelete = async () => {
    await onDelete(selectedProducts);
    setShowDeleteConfirm(false);
  };

  const handleUpdateCosts = async () => {
    await onUpdateCosts(selectedProducts, costUpdate);
    setShowUpdateCosts(false);
    setCostUpdate({ wholesale_cost: '', pack_size: '', moq: '' });
  };

  return (
    <>
      <Paper
        sx={{
          p: 1.5,
          mb: 2,
          bgcolor: 'rgba(99, 102, 241, 0.1)',
          borderLeft: '4px solid',
          borderColor: 'primary.main',
          position: 'sticky',
          top: 0,
          zIndex: 10,
          boxShadow: 2
        }}
        elevation={2}
      >
        <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" gap={1}>
          <Typography variant="body2" fontWeight="bold" color="primary">
            {selectedCount} selected
          </Typography>

          <Divider orientation="vertical" flexItem />

          {onAddToOrder && (
            <Button
              size="small"
              startIcon={<ShoppingCartIcon />}
              onClick={() => onAddToOrder(selectedProducts)}
              variant="contained"
              color="primary"
            >
              Add to Buy List
            </Button>
          )}

          {onUpdateCosts && (
            <Button
              size="small"
              startIcon={<EditIcon />}
              onClick={() => setShowUpdateCosts(true)}
              variant="outlined"
            >
              Update Costs
            </Button>
          )}

          {onRefreshData && (
            <Button
              size="small"
              startIcon={<RefreshIcon />}
              onClick={() => onRefreshData(selectedProducts)}
              variant="outlined"
              color="info"
            >
              Refresh Data
            </Button>
          )}

          {onFavorite && (
            <Button
              size="small"
              startIcon={<FavoriteIcon />}
              onClick={() => onFavorite(selectedProducts)}
              variant="outlined"
            >
              Favorite
            </Button>
          )}

          {onHide && (
            <Button
              size="small"
              startIcon={<VisibilityOffIcon />}
              onClick={() => onHide(selectedProducts)}
              variant="outlined"
            >
              Hide
            </Button>
          )}

          {onExport && (
            <Button
              size="small"
              startIcon={<FileDownloadIcon />}
              onClick={() => onExport(selectedProducts)}
              variant="outlined"
            >
              Export
            </Button>
          )}

          {onDelete && (
            <Button
              size="small"
              startIcon={<DeleteIcon />}
              onClick={() => setShowDeleteConfirm(true)}
              variant="outlined"
              color="error"
            >
              Delete
            </Button>
          )}

          <Box flex={1} />

          {onClearSelection && (
            <IconButton size="small" onClick={onClearSelection}>
              <CloseIcon fontSize="small" />
            </IconButton>
          )}
        </Stack>
      </Paper>

      {/* DELETE CONFIRMATION DIALOG */}
      <Dialog open={showDeleteConfirm} onClose={() => setShowDeleteConfirm(false)}>
        <DialogTitle>Delete {selectedCount} Products?</DialogTitle>
        <DialogContent>
          <Alert severity="warning" sx={{ mb: 2 }}>
            This action cannot be undone. Are you sure you want to delete {selectedCount} products?
          </Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowDeleteConfirm(false)}>Cancel</Button>
          <Button onClick={handleDelete} variant="contained" color="error">
            Delete {selectedCount} Products
          </Button>
        </DialogActions>
      </Dialog>

      {/* UPDATE COSTS DIALOG */}
      <Dialog open={showUpdateCosts} onClose={() => setShowUpdateCosts(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Update Costs for {selectedCount} Products</DialogTitle>
        <DialogContent>
          <Alert severity="info" sx={{ mb: 2 }}>
            Enter new values. Leave blank to keep existing values.
          </Alert>

          <Stack spacing={2} mt={2}>
            <TextField
              label="Wholesale Cost"
              type="number"
              value={costUpdate.wholesale_cost}
              onChange={(e) => setCostUpdate({ ...costUpdate, wholesale_cost: e.target.value })}
              InputProps={{ startAdornment: '$' }}
              fullWidth
            />

            <TextField
              label="Pack Size"
              type="number"
              value={costUpdate.pack_size}
              onChange={(e) => setCostUpdate({ ...costUpdate, pack_size: e.target.value })}
              fullWidth
            />

            <TextField
              label="MOQ (Minimum Order Quantity)"
              type="number"
              value={costUpdate.moq}
              onChange={(e) => setCostUpdate({ ...costUpdate, moq: e.target.value })}
              fullWidth
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowUpdateCosts(false)}>Cancel</Button>
          <Button onClick={handleUpdateCosts} variant="contained">
            Update {selectedCount} Products
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}

