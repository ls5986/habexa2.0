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
  Select,
  MenuItem,
  FormControl,
  InputLabel,
} from '@mui/material';
import {
  ArrowLeft,
  Edit,
  Delete,
  Download,
  Send,
  CheckCircle,
  Package,
} from 'lucide-react';
import api from '../services/api';
import { useToast } from '../context/ToastContext';

// Format currency helper
const formatCurrency = (value) => {
  if (value === null || value === undefined) return '$0.00';
  return `$${parseFloat(value).toFixed(2)}`;
};

// Format percentage helper
const formatPercentage = (value) => {
  if (value === null || value === undefined) return '0%';
  return `${parseFloat(value).toFixed(1)}%`;
};

export default function SupplierOrderDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { showToast } = useToast();
  
  const [order, setOrder] = useState(null);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editData, setEditData] = useState({
    order_number: '',
    status: 'draft',
    shipping_method: '',
    estimated_delivery_date: '',
    notes: '',
  });
  const [createInboundDialogOpen, setCreateInboundDialogOpen] = useState(false);
  const [warehouses, setWarehouses] = useState([]);
  const [selectedWarehouse, setSelectedWarehouse] = useState('');
  const [inboundData, setInboundData] = useState({
    tracking_number: '',
    carrier: '',
    shipped_date: '',
    expected_delivery_date: '',
    requires_prep: false,
    prep_instructions: '',
    notes: '',
  });
  const [creatingInbound, setCreatingInbound] = useState(false);

  useEffect(() => {
    fetchOrder();
    fetchWarehouses();
  }, [id]);

  const fetchWarehouses = async () => {
    try {
      const response = await api.get('/tpl/warehouses?active_only=true');
      setWarehouses(response.data.warehouses || []);
    } catch (error) {
      console.error('Error fetching warehouses:', error);
    }
  };

  const fetchOrder = async () => {
    setLoading(true);
    try {
      const response = await api.get(`/supplier-orders/${id}`);
      setOrder(response.data.supplier_order);
      setEditData({
        order_number: response.data.supplier_order.order_number || '',
        status: response.data.supplier_order.status || 'draft',
        shipping_method: response.data.supplier_order.shipping_method || '',
        estimated_delivery_date: response.data.supplier_order.estimated_delivery_date || '',
        notes: response.data.supplier_order.notes || '',
      });
    } catch (error) {
      console.error('Error fetching supplier order:', error);
      showToast('Failed to load supplier order', 'error');
      navigate('/supplier-orders');
    } finally {
      setLoading(false);
    }
  };

  const handleUpdate = async () => {
    setUpdating(true);
    try {
      await api.put(`/supplier-orders/${id}`, editData);
      showToast('Order updated', 'success');
      setEditDialogOpen(false);
      fetchOrder();
    } catch (error) {
      console.error('Error updating order:', error);
      showToast('Failed to update order', 'error');
    } finally {
      setUpdating(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm('Are you sure you want to delete this supplier order?')) {
      return;
    }

    setUpdating(true);
    try {
      await api.delete(`/supplier-orders/${id}`);
      showToast('Supplier order deleted', 'success');
      navigate('/supplier-orders');
    } catch (error) {
      console.error('Error deleting order:', error);
      showToast('Failed to delete order', 'error');
    } finally {
      setUpdating(false);
    }
  };

  const handleExport = async () => {
    try {
      const response = await api.post(`/supplier-orders/${id}/export?format=csv`, {}, {
        responseType: 'blob'
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `supplier_order_${id.substring(0, 8)}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      showToast('Order exported', 'success');
    } catch (error) {
      console.error('Error exporting order:', error);
      showToast('Failed to export order', 'error');
    }
  };

  const handleMarkAsSent = async () => {
    setUpdating(true);
    try {
      await api.put(`/supplier-orders/${id}`, {
        status: 'sent',
        sent_date: new Date().toISOString()
      });
      showToast('Order marked as sent', 'success');
      fetchOrder();
    } catch (error) {
      console.error('Error marking order as sent:', error);
      showToast('Failed to update order', 'error');
    } finally {
      setUpdating(false);
    }
  };

  const handleCreateInbound = async () => {
    if (!selectedWarehouse) {
      showToast('Please select a 3PL warehouse', 'warning');
      return;
    }

    setCreatingInbound(true);
    try {
      const response = await api.post(`/tpl/inbounds/create-from-supplier-order?supplier_order_id=${id}&tpl_warehouse_id=${selectedWarehouse}`, {
        tracking_number: inboundData.tracking_number || null,
        carrier: inboundData.carrier || null,
        shipped_date: inboundData.shipped_date || null,
        expected_delivery_date: inboundData.expected_delivery_date || null,
        requires_prep: inboundData.requires_prep,
        prep_instructions: inboundData.prep_instructions || null,
        notes: inboundData.notes || null,
      });
      
      showToast('3PL inbound created', 'success');
      setCreateInboundDialogOpen(false);
      setInboundData({
        tracking_number: '',
        carrier: '',
        shipped_date: '',
        expected_delivery_date: '',
        requires_prep: false,
        prep_instructions: '',
        notes: '',
      });
      setSelectedWarehouse('');
      
      // Navigate to inbound detail
      if (response.data.inbound?.id) {
        setTimeout(() => {
          window.location.href = `/tpl/inbounds/${response.data.inbound.id}`;
        }, 1500);
      }
    } catch (error) {
      console.error('Error creating inbound:', error);
      showToast(error.response?.data?.detail || 'Failed to create inbound', 'error');
    } finally {
      setCreatingInbound(false);
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (!order) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">Supplier order not found</Alert>
      </Box>
    );
  }

  const statusColors = {
    draft: 'default',
    sent: 'info',
    confirmed: 'warning',
    in_transit: 'primary',
    received: 'success',
    cancelled: 'error',
  };

  return (
    <Box sx={{ p: 3, bgcolor: '#f5f5f5', minHeight: '100vh' }}>
      {/* Header */}
      <Box sx={{ mb: 3, display: 'flex', alignItems: 'center', gap: 2 }}>
        <IconButton onClick={() => navigate('/supplier-orders')}>
          <ArrowLeft size={24} />
        </IconButton>
        <Box sx={{ flex: 1 }}>
          <Typography variant="h4" fontWeight={600}>
            Supplier Order
          </Typography>
          <Box sx={{ display: 'flex', gap: 1, mt: 1, alignItems: 'center' }}>
            <Chip
              label={order.status?.toUpperCase() || 'DRAFT'}
              color={statusColors[order.status] || 'default'}
              size="small"
            />
            {order.supplier_name && (
              <Typography variant="body2" color="text.secondary">
                Supplier: {order.supplier_name}
              </Typography>
            )}
            {order.order_number && (
              <Typography variant="body2" color="text.secondary">
                Order #: {order.order_number}
              </Typography>
            )}
          </Box>
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          {order.status === 'draft' && (
            <Button
              variant="contained"
              startIcon={<Send size={16} />}
              onClick={handleMarkAsSent}
              disabled={updating}
            >
              Mark as Sent
            </Button>
          )}
          {(order.status === 'sent' || order.status === 'confirmed' || order.status === 'in_transit') && (
            <Button
              variant="contained"
              color="primary"
              startIcon={<Package size={16} />}
              onClick={() => setCreateInboundDialogOpen(true)}
              disabled={creatingInbound || warehouses.length === 0}
            >
              Create 3PL Inbound
            </Button>
          )}
          <Button
            variant="outlined"
            startIcon={<Download size={16} />}
            onClick={handleExport}
          >
            Export CSV
          </Button>
          <Button
            variant="outlined"
            startIcon={<Edit size={16} />}
            onClick={() => setEditDialogOpen(true)}
            disabled={updating}
          >
            Edit
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
                {order.total_products || order.items?.length || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="overline" color="text.secondary">Total Units</Typography>
              <Typography variant="h4" fontWeight={600}>
                {order.total_units || order.items?.reduce((sum, item) => sum + (item.quantity || 0), 0) || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="overline" color="text.secondary">Total Cost</Typography>
              <Typography variant="h4" fontWeight={600} color="primary.main">
                {formatCurrency(order.total_cost || order.items?.reduce((sum, item) => sum + (item.total_cost || 0), 0) || 0)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="overline" color="text.secondary">Expected Profit</Typography>
              <Typography variant="h4" fontWeight={600} color="success.main">
                {formatCurrency(order.expected_profit || order.items?.reduce((sum, item) => sum + (item.expected_profit || 0), 0) || 0)}
              </Typography>
              {order.expected_roi && (
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                  ROI: {formatPercentage(order.expected_roi)}
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Supplier Info */}
      {order.supplier_name && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" fontWeight={600} sx={{ mb: 2 }}>
              Supplier Information
            </Typography>
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <Typography variant="body2" color="text.secondary">Name</Typography>
                <Typography variant="body1" fontWeight={500}>
                  {order.supplier_name}
                </Typography>
              </Grid>
              {order.supplier_email && (
                <Grid item xs={12} sm={6}>
                  <Typography variant="body2" color="text.secondary">Email</Typography>
                  <Typography variant="body1">{order.supplier_email}</Typography>
                </Grid>
              )}
              {order.supplier_phone && (
                <Grid item xs={12} sm={6}>
                  <Typography variant="body2" color="text.secondary">Phone</Typography>
                  <Typography variant="body1">{order.supplier_phone}</Typography>
                </Grid>
              )}
              {order.shipping_method && (
                <Grid item xs={12} sm={6}>
                  <Typography variant="body2" color="text.secondary">Shipping Method</Typography>
                  <Typography variant="body1">{order.shipping_method}</Typography>
                </Grid>
              )}
              {order.estimated_delivery_date && (
                <Grid item xs={12} sm={6}>
                  <Typography variant="body2" color="text.secondary">Estimated Delivery</Typography>
                  <Typography variant="body1">
                    {new Date(order.estimated_delivery_date).toLocaleDateString()}
                  </Typography>
                </Grid>
              )}
            </Grid>
          </CardContent>
        </Card>
      )}

      {/* Items Table */}
      <Card>
        <CardContent>
          <Typography variant="h6" fontWeight={600} sx={{ mb: 2 }}>
            Products ({order.items?.length || 0})
          </Typography>
          {!order.items || order.items.length === 0 ? (
            <Alert severity="info">No products in this order</Alert>
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
                  </TableRow>
                </TableHead>
                <TableBody>
                  {order.items.map((item) => (
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
                          </Box>
                        </Box>
                      </TableCell>
                      <TableCell align="right">
                        <Typography variant="body2">{item.quantity}</Typography>
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
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </CardContent>
      </Card>

      {/* Edit Dialog */}
      <Dialog
        open={editDialogOpen}
        onClose={() => setEditDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Edit Supplier Order</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
            <TextField
              label="Order Number"
              value={editData.order_number}
              onChange={(e) => setEditData({ ...editData, order_number: e.target.value })}
              fullWidth
            />
            <FormControl fullWidth>
              <InputLabel>Status</InputLabel>
              <Select
                value={editData.status}
                onChange={(e) => setEditData({ ...editData, status: e.target.value })}
                label="Status"
              >
                <MenuItem value="draft">Draft</MenuItem>
                <MenuItem value="sent">Sent</MenuItem>
                <MenuItem value="confirmed">Confirmed</MenuItem>
                <MenuItem value="in_transit">In Transit</MenuItem>
                <MenuItem value="received">Received</MenuItem>
                <MenuItem value="cancelled">Cancelled</MenuItem>
              </Select>
            </FormControl>
            <TextField
              label="Shipping Method"
              value={editData.shipping_method}
              onChange={(e) => setEditData({ ...editData, shipping_method: e.target.value })}
              fullWidth
            />
            <TextField
              label="Estimated Delivery Date"
              type="date"
              value={editData.estimated_delivery_date}
              onChange={(e) => setEditData({ ...editData, estimated_delivery_date: e.target.value })}
              fullWidth
              InputLabelProps={{ shrink: true }}
            />
            <TextField
              label="Notes"
              value={editData.notes}
              onChange={(e) => setEditData({ ...editData, notes: e.target.value })}
              fullWidth
              multiline
              rows={3}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => setEditDialogOpen(false)}
            disabled={updating}
          >
            Cancel
          </Button>
          <Button
            onClick={handleUpdate}
            variant="contained"
            disabled={updating}
          >
            Update
          </Button>
        </DialogActions>
      </Dialog>

      {/* Create 3PL Inbound Dialog */}
      <Dialog
        open={createInboundDialogOpen}
        onClose={() => {
          setCreateInboundDialogOpen(false);
          setInboundData({
            tracking_number: '',
            carrier: '',
            shipped_date: '',
            expected_delivery_date: '',
            requires_prep: false,
            prep_instructions: '',
            notes: '',
          });
          setSelectedWarehouse('');
        }}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Create 3PL Inbound</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
            <FormControl fullWidth required>
              <InputLabel>3PL Warehouse</InputLabel>
              <Select
                value={selectedWarehouse}
                onChange={(e) => setSelectedWarehouse(e.target.value)}
                label="3PL Warehouse"
              >
                {warehouses.map((warehouse) => (
                  <MenuItem key={warehouse.id} value={warehouse.id}>
                    {warehouse.name} {warehouse.company && `(${warehouse.company})`}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <TextField
              label="Tracking Number"
              value={inboundData.tracking_number}
              onChange={(e) => setInboundData({ ...inboundData, tracking_number: e.target.value })}
              fullWidth
            />
            <TextField
              label="Carrier"
              value={inboundData.carrier}
              onChange={(e) => setInboundData({ ...inboundData, carrier: e.target.value })}
              fullWidth
              placeholder="UPS, FedEx, etc."
            />
            <TextField
              label="Shipped Date"
              type="datetime-local"
              value={inboundData.shipped_date}
              onChange={(e) => setInboundData({ ...inboundData, shipped_date: e.target.value })}
              fullWidth
              InputLabelProps={{ shrink: true }}
            />
            <TextField
              label="Expected Delivery Date"
              type="date"
              value={inboundData.expected_delivery_date}
              onChange={(e) => setInboundData({ ...inboundData, expected_delivery_date: e.target.value })}
              fullWidth
              InputLabelProps={{ shrink: true }}
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={inboundData.requires_prep}
                  onChange={(e) => setInboundData({ ...inboundData, requires_prep: e.target.checked })}
                />
              }
              label="Requires Prep"
            />
            {inboundData.requires_prep && (
              <TextField
                label="Prep Instructions"
                value={inboundData.prep_instructions}
                onChange={(e) => setInboundData({ ...inboundData, prep_instructions: e.target.value })}
                fullWidth
                multiline
                rows={3}
                placeholder="Special prep requirements, labeling instructions, etc."
              />
            )}
            <TextField
              label="Notes"
              value={inboundData.notes}
              onChange={(e) => setInboundData({ ...inboundData, notes: e.target.value })}
              fullWidth
              multiline
              rows={2}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => {
              setCreateInboundDialogOpen(false);
              setInboundData({
                tracking_number: '',
                carrier: '',
                shipped_date: '',
                expected_delivery_date: '',
                requires_prep: false,
                prep_instructions: '',
                notes: '',
              });
              setSelectedWarehouse('');
            }}
            disabled={creatingInbound}
          >
            Cancel
          </Button>
          <Button
            onClick={handleCreateInbound}
            variant="contained"
            disabled={creatingInbound || !selectedWarehouse}
            startIcon={<Package size={16} />}
          >
            {creatingInbound ? 'Creating...' : 'Create Inbound'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

