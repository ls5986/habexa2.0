import { useState, useEffect } from 'react';
import {
  Box, Typography, Card, CardContent, Button, IconButton, TextField, InputAdornment,
  CircularProgress, Dialog, DialogTitle, DialogContent, DialogActions, Alert,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper
} from '@mui/material';
import { ShoppingCart, Plus, Minus, Trash2, X, Package } from 'lucide-react';
import api from '../services/api';
import { useToast } from '../context/ToastContext';
import { formatCurrency } from '../utils/formatters';
import { habexa } from '../theme';
import ConfirmDialog from '../components/common/ConfirmDialog';

const BuyList = () => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creatingOrder, setCreatingOrder] = useState(false);
  const [clearDialogOpen, setClearDialogOpen] = useState(false);
  const [removeDialogOpen, setRemoveDialogOpen] = useState(false);
  const [itemToRemove, setItemToRemove] = useState(null);
  const { showToast } = useToast();

  useEffect(() => {
    fetchBuyList();
  }, []);

  const fetchBuyList = async () => {
    try {
      setLoading(true);
      const response = await api.get('/buy-list');
      setItems(response.data || []);
    } catch (error) {
      console.error('Failed to fetch buy list:', error);
      showToast('Failed to load buy list', 'error');
    } finally {
      setLoading(false);
    }
  };

  const updateQuantity = async (itemId, newQuantity) => {
    if (newQuantity < 1) {
      showToast('Quantity must be at least 1', 'warning');
      return;
    }

    try {
      await api.patch(`/buy-list/${itemId}`, { quantity: newQuantity });
      showToast('Quantity updated', 'success');
      fetchBuyList();
    } catch (error) {
      showToast('Failed to update quantity', 'error');
    }
  };

  const handleRemove = (item) => {
    setItemToRemove(item);
    setRemoveDialogOpen(true);
  };

  const confirmRemove = async () => {
    if (!itemToRemove) return;

    try {
      await api.delete(`/buy-list/${itemToRemove.id}`);
      showToast('Item removed from buy list', 'success');
      setRemoveDialogOpen(false);
      setItemToRemove(null);
      fetchBuyList();
    } catch (error) {
      showToast('Failed to remove item', 'error');
    }
  };

  const handleClearAll = async () => {
    try {
      await api.delete('/buy-list');
      showToast('Buy list cleared', 'success');
      setClearDialogOpen(false);
      fetchBuyList();
    } catch (error) {
      showToast('Failed to clear buy list', 'error');
    }
  };

  const handleCreateOrder = async () => {
    if (items.length === 0) {
      showToast('Buy list is empty', 'warning');
      return;
    }

    setCreatingOrder(true);
    try {
      const response = await api.post('/buy-list/create-order');
      showToast(`Order created with ${response.data.orders_created} items!`, 'success');
      fetchBuyList();
    } catch (error) {
      showToast(error.response?.data?.detail || 'Failed to create order', 'error');
    } finally {
      setCreatingOrder(false);
    }
  };

  const totalItems = items.reduce((sum, item) => sum + (item.quantity || item.moq || 1), 0);
  const totalCost = items.reduce((sum, item) => {
    const quantity = item.quantity || item.moq || 1;
    const cost = item.buy_cost || 0;
    return sum + (quantity * cost);
  }, 0);

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
        <CircularProgress />
      </Box>
    );
  }

  if (items.length === 0) {
    return (
      <Box sx={{ p: 3 }}>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
          <Typography variant="h4" fontWeight={700}>
            Buy List
          </Typography>
        </Box>
        <Card sx={{ p: 4, textAlign: 'center' }}>
          <Package size={48} style={{ color: '#8B8B9B', margin: '0 auto 16px' }} />
          <Typography variant="h6" sx={{ mb: 1 }}>Your buy list is empty</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Add products to your buy list from the Products page
          </Typography>
          <Button
            variant="contained"
            onClick={() => window.location.href = '/products'}
            sx={{
              backgroundColor: habexa.purple.main,
              '&:hover': { backgroundColor: habexa.purple.dark },
            }}
          >
            Browse Products
          </Button>
        </Card>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" fontWeight={700}>
          Buy List
        </Typography>
        <Box display="flex" gap={2}>
          <Button
            variant="outlined"
            color="error"
            startIcon={<Trash2 size={16} />}
            onClick={() => setClearDialogOpen(true)}
            disabled={items.length === 0}
          >
            Clear All
          </Button>
          <Button
            variant="contained"
            startIcon={<ShoppingCart size={16} />}
            onClick={handleCreateOrder}
            disabled={creatingOrder || items.length === 0}
            sx={{
              backgroundColor: habexa.purple.main,
              '&:hover': { backgroundColor: habexa.purple.dark },
            }}
          >
            {creatingOrder ? 'Creating Order...' : `Create Order (${items.length} items)`}
          </Button>
        </Box>
      </Box>

      <Card>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Product</TableCell>
                <TableCell>ASIN</TableCell>
                <TableCell align="right">Unit Cost</TableCell>
                <TableCell align="center">Quantity</TableCell>
                <TableCell align="right">Subtotal</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {items.map((item) => {
                const quantity = item.quantity || item.moq || 1;
                const unitCost = item.buy_cost || 0;
                const subtotal = quantity * unitCost;

                return (
                  <TableRow key={item.id}>
                    <TableCell>
                      <Box display="flex" alignItems="center" gap={2}>
                        {item.image_url ? (
                          <Box
                            component="img"
                            src={item.image_url}
                            sx={{ width: 48, height: 48, borderRadius: 1, objectFit: 'cover' }}
                          />
                        ) : (
                          <Box sx={{ width: 48, height: 48, bgcolor: 'background.paper', borderRadius: 1 }} />
                        )}
                        <Typography variant="body2" fontWeight={500}>
                          {item.title || 'Unknown Product'}
                        </Typography>
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" fontFamily="monospace" color="text.secondary">
                        {item.asin}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      <Typography variant="body2">
                        {formatCurrency(unitCost)}
                      </Typography>
                    </TableCell>
                    <TableCell align="center">
                      <Box display="flex" alignItems="center" justifyContent="center" gap={1}>
                        <IconButton
                          size="small"
                          onClick={() => updateQuantity(item.id, quantity - 1)}
                          disabled={quantity <= 1}
                        >
                          <Minus size={16} />
                        </IconButton>
                        <TextField
                          type="number"
                          value={quantity}
                          onChange={(e) => {
                            const val = parseInt(e.target.value) || 1;
                            if (val >= 1) {
                              updateQuantity(item.id, val);
                            }
                          }}
                          inputProps={{ min: 1, style: { textAlign: 'center', width: 60 } }}
                          size="small"
                          sx={{ width: 80 }}
                        />
                        <IconButton
                          size="small"
                          onClick={() => updateQuantity(item.id, quantity + 1)}
                        >
                          <Plus size={16} />
                        </IconButton>
                      </Box>
                    </TableCell>
                    <TableCell align="right">
                      <Typography variant="body2" fontWeight={600}>
                        {formatCurrency(subtotal)}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      <IconButton
                        size="small"
                        color="error"
                        onClick={() => handleRemove(item)}
                      >
                        <Trash2 size={16} />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TableContainer>

        <Box sx={{ p: 3, borderTop: 1, borderColor: 'divider' }}>
          <Box display="flex" justifyContent="space-between" alignItems="center">
            <Box>
              <Typography variant="body2" color="text.secondary">
                Total Items
              </Typography>
              <Typography variant="h6" fontWeight={600}>
                {totalItems}
              </Typography>
            </Box>
            <Box textAlign="right">
              <Typography variant="body2" color="text.secondary">
                Total Cost
              </Typography>
              <Typography variant="h5" fontWeight={700} color={habexa.purple.main}>
                {formatCurrency(totalCost)}
              </Typography>
            </Box>
          </Box>
        </Box>
      </Card>

      <ConfirmDialog
        open={removeDialogOpen}
        onClose={() => {
          setRemoveDialogOpen(false);
          setItemToRemove(null);
        }}
        onConfirm={confirmRemove}
        title="Remove Item"
        message={`Remove "${itemToRemove?.title || itemToRemove?.asin}" from buy list?`}
        confirmText="Remove"
        danger
      />

      <ConfirmDialog
        open={clearDialogOpen}
        onClose={() => setClearDialogOpen(false)}
        onConfirm={handleClearAll}
        title="Clear Buy List"
        message="Are you sure you want to remove all items from your buy list?"
        confirmText="Clear All"
        danger
      />
    </Box>
  );
};

export default BuyList;

