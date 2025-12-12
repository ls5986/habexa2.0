import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Button,
  IconButton,
  TextField,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Grid,
  Chip,
  CircularProgress,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Menu,
  MenuItem,
} from '@mui/material';
import {
  ArrowLeft,
  Edit,
  Delete,
  MoreVertical,
  Plus,
  Minus,
  CheckCircle,
  Download,
  Send,
} from 'lucide-react';
import api from '../services/api';
import { useToast } from '../context/ToastContext';
import { formatCurrency } from '../utils/formatters';

// Format percentage helper
const formatPercentage = (value) => {
  if (value === null || value === undefined) return '0%';
  return `${parseFloat(value).toFixed(1)}%`;
};

export default function BuyListDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { showToast } = useToast();
  
  const [buyList, setBuyList] = useState(null);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);
  const [itemMenuAnchor, setItemMenuAnchor] = useState(null);
  const [selectedItem, setSelectedItem] = useState(null);
  const [editQuantityDialogOpen, setEditQuantityDialogOpen] = useState(false);
  const [newQuantity, setNewQuantity] = useState(1);

  useEffect(() => {
    fetchBuyList();
  }, [id]);

  const fetchBuyList = async () => {
    setLoading(true);
    try {
      const response = await api.get(`/buy-lists/${id}`);
      setBuyList(response.data.buy_list);
    } catch (error) {
      console.error('Error fetching buy list:', error);
      showToast('Failed to load buy list', 'error');
      navigate('/buy-lists');
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateQuantity = async (itemId, quantity) => {
    if (quantity < 1) {
      showToast('Quantity must be at least 1', 'warning');
      return;
    }

    setUpdating(true);
    try {
      await api.put(`/buy-lists/${id}/items/${itemId}`, { quantity });
      showToast('Quantity updated', 'success');
      fetchBuyList();
      setEditQuantityDialogOpen(false);
    } catch (error) {
      console.error('Error updating quantity:', error);
      showToast('Failed to update quantity', 'error');
    } finally {
      setUpdating(false);
    }
  };

  const handleRemoveItem = async (itemId) => {
    setUpdating(true);
    try {
      await api.delete(`/buy-lists/${id}/items/${itemId}`);
      showToast('Item removed', 'success');
      fetchBuyList();
      setItemMenuAnchor(null);
    } catch (error) {
      console.error('Error removing item:', error);
      showToast('Failed to remove item', 'error');
    } finally {
      setUpdating(false);
    }
  };

  const handleFinalize = async () => {
    setUpdating(true);
    try {
      await api.post(`/buy-lists/${id}/finalize`);
      showToast('Buy list finalized', 'success');
      fetchBuyList();
    } catch (error) {
      console.error('Error finalizing buy list:', error);
      showToast('Failed to finalize buy list', 'error');
    } finally {
      setUpdating(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm('Are you sure you want to delete this buy list?')) {
      return;
    }

    setUpdating(true);
    try {
      await api.delete(`/buy-lists/${id}`);
      showToast('Buy list deleted', 'success');
      navigate('/buy-lists');
    } catch (error) {
      console.error('Error deleting buy list:', error);
      showToast('Failed to delete buy list', 'error');
    } finally {
      setUpdating(false);
    }
  };

  const openEditQuantity = (item) => {
    setSelectedItem(item);
    setNewQuantity(item.quantity);
    setEditQuantityDialogOpen(true);
    setItemMenuAnchor(null);
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (!buyList) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">Buy list not found</Alert>
      </Box>
    );
  }

  const statusColors = {
    draft: 'default',
    approved: 'success',
    ordered: 'info',
    received: 'success',
    archived: 'default',
  };

  return (
    <Box sx={{ p: 3, bgcolor: '#f5f5f5', minHeight: '100vh' }}>
      {/* Header */}
      <Box sx={{ mb: 3, display: 'flex', alignItems: 'center', gap: 2 }}>
        <IconButton onClick={() => navigate('/buy-lists')}>
          <ArrowLeft size={24} />
        </IconButton>
        <Box sx={{ flex: 1 }}>
          <Typography variant="h4" fontWeight={600}>
            {buyList.name}
          </Typography>
          <Box sx={{ display: 'flex', gap: 1, mt: 1, alignItems: 'center' }}>
            <Chip
              label={buyList.status?.toUpperCase() || 'DRAFT'}
              color={statusColors[buyList.status] || 'default'}
              size="small"
            />
            <Typography variant="body2" color="text.secondary">
              Created {new Date(buyList.created_at).toLocaleDateString()}
            </Typography>
          </Box>
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          {buyList.status === 'draft' && (
            <Button
              variant="contained"
              startIcon={<CheckCircle size={16} />}
              onClick={handleFinalize}
              disabled={updating || !buyList.items || buyList.items.length === 0}
            >
              Finalize
            </Button>
          )}
          <Button
            variant="outlined"
            startIcon={<Download size={16} />}
            disabled
          >
            Export
          </Button>
          <Button
            variant="outlined"
            color="error"
            startIcon={<Delete size={16} />}
            onClick={handleDelete}
            disabled={updating}
          >
            Delete
          </Button>
        </Box>
      </Box>

      {/* Summary Cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="overline" color="text.secondary">Total Products</Typography>
              <Typography variant="h4" fontWeight={600}>
                {buyList.total_products || buyList.items?.length || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="overline" color="text.secondary">Total Units</Typography>
              <Typography variant="h4" fontWeight={600}>
                {buyList.total_units || buyList.items?.reduce((sum, item) => sum + (item.quantity || 0), 0) || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="overline" color="text.secondary">Total Cost</Typography>
              <Typography variant="h4" fontWeight={600} color="primary.main">
                {formatCurrency(buyList.total_cost || buyList.items?.reduce((sum, item) => sum + (item.total_cost || 0), 0) || 0)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="overline" color="text.secondary">Expected Profit</Typography>
              <Typography variant="h4" fontWeight={600} color="success.main">
                {formatCurrency(buyList.expected_profit || buyList.items?.reduce((sum, item) => sum + (item.expected_profit || 0), 0) || 0)}
              </Typography>
              {buyList.expected_roi && (
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                  ROI: {formatPercentage(buyList.expected_roi)}
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Items Table */}
      <Card>
        <CardContent>
          <Typography variant="h6" fontWeight={600} sx={{ mb: 2 }}>
            Products ({buyList.items?.length || 0})
          </Typography>
          {!buyList.items || buyList.items.length === 0 ? (
            <Alert severity="info">No products in this buy list</Alert>
          ) : (
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Product</TableCell>
                    <TableCell align="right">Quantity</TableCell>
                    <TableCell align="right">Unit Cost</TableCell>
                    <TableCell align="right">Total Cost</TableCell>
                    <TableCell align="right">Expected Profit</TableCell>
                    <TableCell align="right">Expected ROI</TableCell>
                    <TableCell width={50}></TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {buyList.items.map((item) => (
                    <TableRow key={item.id}>
                      <TableCell>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          {item.product?.image_url && (
                            <Box
                              component="img"
                              src={item.product.image_url}
                              alt={item.product.title}
                              sx={{ width: 50, height: 50, objectFit: 'contain', borderRadius: 1 }}
                            />
                          )}
                          <Box>
                            <Typography variant="body2" fontWeight={600}>
                              {item.product?.title || 'Unknown Product'}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              ASIN: {item.product?.asin || 'N/A'}
                            </Typography>
                            {item.product_source?.supplier_name && (
                              <Typography variant="caption" color="text.secondary" display="block">
                                Supplier: {item.product_source.supplier_name}
                              </Typography>
                            )}
                          </Box>
                        </Box>
                      </TableCell>
                      <TableCell align="right">
                        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 1 }}>
                          {buyList.status === 'draft' && (
                            <>
                              <IconButton
                                size="small"
                                onClick={() => handleUpdateQuantity(item.id, item.quantity - 1)}
                                disabled={updating || item.quantity <= 1}
                              >
                                <Minus size={16} />
                              </IconButton>
                              <Typography variant="body2" sx={{ minWidth: 40, textAlign: 'center' }}>
                                {item.quantity}
                              </Typography>
                              <IconButton
                                size="small"
                                onClick={() => handleUpdateQuantity(item.id, item.quantity + 1)}
                                disabled={updating}
                              >
                                <Plus size={16} />
                              </IconButton>
                            </>
                          )}
                          {buyList.status !== 'draft' && (
                            <Typography variant="body2">{item.quantity}</Typography>
                          )}
                        </Box>
                      </TableCell>
                      <TableCell align="right">
                        {formatCurrency(item.unit_cost)}
                      </TableCell>
                      <TableCell align="right">
                        <Typography variant="body2" fontWeight={600}>
                          {formatCurrency(item.total_cost)}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Typography
                          variant="body2"
                          color={item.expected_profit && item.expected_profit > 0 ? 'success.main' : 'error.main'}
                        >
                          {formatCurrency(item.expected_profit || 0)}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        {item.expected_roi ? (
                          <Chip
                            label={formatPercentage(item.expected_roi)}
                            size="small"
                            color={item.expected_roi >= 50 ? 'success' : item.expected_roi >= 30 ? 'warning' : item.expected_roi >= 15 ? 'info' : 'error'}
                          />
                        ) : (
                          <Typography variant="body2" color="text.disabled">—</Typography>
                        )}
                      </TableCell>
                      <TableCell>
                        {buyList.status === 'draft' && (
                          <IconButton
                            size="small"
                            onClick={(e) => {
                              setItemMenuAnchor(e.currentTarget);
                              setSelectedItem(item);
                            }}
                          >
                            <MoreVertical size={16} />
                          </IconButton>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </CardContent>
      </Card>

      {/* Item Menu */}
      <Menu
        anchorEl={itemMenuAnchor}
        open={Boolean(itemMenuAnchor)}
        onClose={() => setItemMenuAnchor(null)}
      >
        <MenuItem onClick={() => openEditQuantity(selectedItem)}>
          Edit Quantity
        </MenuItem>
        <MenuItem
          onClick={() => {
            if (selectedItem && window.confirm('Remove this product from buy list?')) {
              handleRemoveItem(selectedItem.id);
            }
          }}
          sx={{ color: 'error.main' }}
        >
          Remove
        </MenuItem>
      </Menu>

      {/* Edit Quantity Dialog */}
      <Dialog
        open={editQuantityDialogOpen}
        onClose={() => {
          setEditQuantityDialogOpen(false);
          setSelectedItem(null);
        }}
      >
        <DialogTitle>Edit Quantity</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            type="number"
            label="Quantity"
            value={newQuantity}
            onChange={(e) => setNewQuantity(parseInt(e.target.value) || 1)}
            inputProps={{ min: 1 }}
            fullWidth
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => {
              setEditQuantityDialogOpen(false);
              setSelectedItem(null);
            }}
            disabled={updating}
          >
            Cancel
          </Button>
          <Button
            onClick={() => selectedItem && handleUpdateQuantity(selectedItem.id, newQuantity)}
            variant="contained"
            disabled={updating || newQuantity < 1}
          >
            Update
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

