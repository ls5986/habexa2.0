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
  Package,
  CheckCircle,
} from 'lucide-react';
import api from '../services/api';
import { useToast } from '../context/ToastContext';

export default function TPLInboundDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { showToast } = useToast();
  
  const [inbound, setInbound] = useState(null);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editData, setEditData] = useState({
    inbound_number: '',
    tracking_number: '',
    carrier: '',
    status: 'pending',
    shipped_date: '',
    expected_delivery_date: '',
    received_date: '',
    prep_started_date: '',
    prep_completed_date: '',
    requires_prep: false,
    prep_instructions: '',
    notes: '',
  });
  const [itemEditDialogOpen, setItemEditDialogOpen] = useState(false);
  const [selectedItem, setSelectedItem] = useState(null);
  const [itemEditData, setItemEditData] = useState({
    quantity_received: 0,
    quantity_prepped: 0,
    prep_status: 'pending',
    prep_notes: '',
  });

  useEffect(() => {
    fetchInbound();
  }, [id]);

  const fetchInbound = async () => {
    setLoading(true);
    try {
      const response = await api.get(`/tpl/inbounds/${id}`);
      setInbound(response.data.inbound);
      setEditData({
        inbound_number: response.data.inbound.inbound_number || '',
        tracking_number: response.data.inbound.tracking_number || '',
        carrier: response.data.inbound.carrier || '',
        status: response.data.inbound.status || 'pending',
        shipped_date: response.data.inbound.shipped_date ? response.data.inbound.shipped_date.substring(0, 16) : '',
        expected_delivery_date: response.data.inbound.expected_delivery_date || '',
        received_date: response.data.inbound.received_date ? response.data.inbound.received_date.substring(0, 16) : '',
        prep_started_date: response.data.inbound.prep_started_date ? response.data.inbound.prep_started_date.substring(0, 16) : '',
        prep_completed_date: response.data.inbound.prep_completed_date ? response.data.inbound.prep_completed_date.substring(0, 16) : '',
        requires_prep: response.data.inbound.requires_prep || false,
        prep_instructions: response.data.inbound.prep_instructions || '',
        notes: response.data.inbound.notes || '',
      });
    } catch (error) {
      console.error('Error fetching inbound:', error);
      showToast('Failed to load 3PL inbound', 'error');
      navigate('/tpl/inbounds');
    } finally {
      setLoading(false);
    }
  };

  const handleUpdate = async () => {
    setUpdating(true);
    try {
      await api.put(`/tpl/inbounds/${id}`, editData);
      showToast('Inbound updated', 'success');
      setEditDialogOpen(false);
      fetchInbound();
    } catch (error) {
      console.error('Error updating inbound:', error);
      showToast('Failed to update inbound', 'error');
    } finally {
      setUpdating(false);
    }
  };

  const handleUpdateItem = async () => {
    if (!selectedItem) return;

    setUpdating(true);
    try {
      await api.put(`/tpl/inbounds/${id}/items/${selectedItem.id}`, {
        quantity_received: itemEditData.quantity_received,
        quantity_prepped: itemEditData.quantity_prepped,
        prep_status: itemEditData.prep_status,
        prep_notes: itemEditData.prep_notes,
      });
      showToast('Item updated', 'success');
      setItemEditDialogOpen(false);
      setSelectedItem(null);
      fetchInbound();
    } catch (error) {
      console.error('Error updating item:', error);
      showToast('Failed to update item', 'error');
    } finally {
      setUpdating(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm('Are you sure you want to delete this 3PL inbound?')) {
      return;
    }

    setUpdating(true);
    try {
      await api.delete(`/tpl/inbounds/${id}`);
      showToast('3PL inbound deleted', 'success');
      navigate('/tpl/inbounds');
    } catch (error) {
      console.error('Error deleting inbound:', error);
      showToast('Failed to delete inbound', 'error');
    } finally {
      setUpdating(false);
    }
  };

  const openItemEdit = (item) => {
    setSelectedItem(item);
    setItemEditData({
      quantity_received: item.quantity_received || 0,
      quantity_prepped: item.quantity_prepped || 0,
      prep_status: item.prep_status || 'pending',
      prep_notes: item.prep_notes || '',
    });
    setItemEditDialogOpen(true);
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (!inbound) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">3PL inbound not found</Alert>
      </Box>
    );
  }

  const statusColors = {
    pending: 'default',
    in_transit: 'info',
    received: 'success',
    prep_in_progress: 'warning',
    prep_complete: 'success',
    ready_for_fba: 'success',
    cancelled: 'error',
  };

  return (
    <Box sx={{ p: 3, bgcolor: '#f5f5f5', minHeight: '100vh' }}>
      {/* Header */}
      <Box sx={{ mb: 3, display: 'flex', alignItems: 'center', gap: 2 }}>
        <IconButton onClick={() => navigate('/tpl/inbounds')}>
          <ArrowLeft size={24} />
        </IconButton>
        <Box sx={{ flex: 1 }}>
          <Typography variant="h4" fontWeight={600}>
            3PL Inbound Shipment
          </Typography>
          <Box sx={{ display: 'flex', gap: 1, mt: 1, alignItems: 'center' }}>
            <Chip
              label={inbound.status?.toUpperCase().replace('_', ' ') || 'PENDING'}
              color={statusColors[inbound.status] || 'default'}
              size="small"
            />
            {inbound.warehouse_name && (
              <Typography variant="body2" color="text.secondary">
                Warehouse: {inbound.warehouse_name}
              </Typography>
            )}
            {inbound.tracking_number && (
              <Typography variant="body2" color="text.secondary">
                Tracking: {inbound.tracking_number}
              </Typography>
            )}
          </Box>
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
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
                {inbound.total_products || inbound.items?.length || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="overline" color="text.secondary">Total Units</Typography>
              <Typography variant="h4" fontWeight={600}>
                {inbound.total_units || inbound.items?.reduce((sum, item) => sum + (item.quantity || 0), 0) || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="overline" color="text.secondary">Units Received</Typography>
              <Typography variant="h4" fontWeight={600} color="success.main">
                {inbound.items?.reduce((sum, item) => sum + (item.quantity_received || 0), 0) || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="overline" color="text.secondary">Units Prepped</Typography>
              <Typography variant="h4" fontWeight={600} color="info.main">
                {inbound.items?.reduce((sum, item) => sum + (item.quantity_prepped || 0), 0) || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Warehouse & Shipping Info */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" fontWeight={600} sx={{ mb: 2 }}>
            Warehouse & Shipping Information
          </Typography>
          <Grid container spacing={2}>
            {inbound.warehouse_name && (
              <Grid item xs={12} sm={6}>
                <Typography variant="body2" color="text.secondary">Warehouse</Typography>
                <Typography variant="body1" fontWeight={500}>
                  {inbound.warehouse_name} {inbound.warehouse_company && `(${inbound.warehouse_company})`}
                </Typography>
                {inbound.warehouse_address && (
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                    {inbound.warehouse_address}
                  </Typography>
                )}
              </Grid>
            )}
            {inbound.tracking_number && (
              <Grid item xs={12} sm={6}>
                <Typography variant="body2" color="text.secondary">Tracking Number</Typography>
                <Typography variant="body1">{inbound.tracking_number}</Typography>
              </Grid>
            )}
            {inbound.carrier && (
              <Grid item xs={12} sm={6}>
                <Typography variant="body2" color="text.secondary">Carrier</Typography>
                <Typography variant="body1">{inbound.carrier}</Typography>
              </Grid>
            )}
            {inbound.shipped_date && (
              <Grid item xs={12} sm={6}>
                <Typography variant="body2" color="text.secondary">Shipped Date</Typography>
                <Typography variant="body1">
                  {new Date(inbound.shipped_date).toLocaleString()}
                </Typography>
              </Grid>
            )}
            {inbound.expected_delivery_date && (
              <Grid item xs={12} sm={6}>
                <Typography variant="body2" color="text.secondary">Expected Delivery</Typography>
                <Typography variant="body1">
                  {new Date(inbound.expected_delivery_date).toLocaleDateString()}
                </Typography>
              </Grid>
            )}
            {inbound.received_date && (
              <Grid item xs={12} sm={6}>
                <Typography variant="body2" color="text.secondary">Received Date</Typography>
                <Typography variant="body1" color="success.main">
                  {new Date(inbound.received_date).toLocaleString()}
                </Typography>
              </Grid>
            )}
            {inbound.requires_prep && (
              <Grid item xs={12}>
                <Typography variant="body2" color="text.secondary">Prep Required</Typography>
                <Typography variant="body1">Yes</Typography>
                {inbound.prep_instructions && (
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                    Instructions: {inbound.prep_instructions}
                  </Typography>
                )}
              </Grid>
            )}
          </Grid>
        </CardContent>
      </Card>

      {/* Items Table */}
      <Card>
        <CardContent>
          <Typography variant="h6" fontWeight={600} sx={{ mb: 2 }}>
            Products ({inbound.items?.length || 0})
          </Typography>
          {!inbound.items || inbound.items.length === 0 ? (
            <Alert severity="info">No products in this inbound</Alert>
          ) : (
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Product</TableCell>
                    <TableCell align="right">Quantity</TableCell>
                    <TableCell align="right">Received</TableCell>
                    <TableCell align="right">Prepped</TableCell>
                    <TableCell>Prep Status</TableCell>
                    <TableCell align="right">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {inbound.items.map((item) => (
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
                        <Typography
                          variant="body2"
                          color={item.quantity_received === item.quantity ? 'success.main' : 'text.secondary'}
                        >
                          {item.quantity_received || 0}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Typography
                          variant="body2"
                          color={item.quantity_prepped === item.quantity ? 'success.main' : 'text.secondary'}
                        >
                          {item.quantity_prepped || 0}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={item.prep_status?.toUpperCase().replace('_', ' ') || 'PENDING'}
                          size="small"
                          color={
                            item.prep_status === 'complete' ? 'success' :
                            item.prep_status === 'in_progress' ? 'warning' :
                            item.prep_status === 'not_required' ? 'default' : 'default'
                          }
                        />
                      </TableCell>
                      <TableCell align="right">
                        <Button
                          size="small"
                          onClick={() => openItemEdit(item)}
                          disabled={updating}
                        >
                          Update
                        </Button>
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
        <DialogTitle>Edit 3PL Inbound</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
            <TextField
              label="Inbound Number"
              value={editData.inbound_number}
              onChange={(e) => setEditData({ ...editData, inbound_number: e.target.value })}
              fullWidth
            />
            <TextField
              label="Tracking Number"
              value={editData.tracking_number}
              onChange={(e) => setEditData({ ...editData, tracking_number: e.target.value })}
              fullWidth
            />
            <TextField
              label="Carrier"
              value={editData.carrier}
              onChange={(e) => setEditData({ ...editData, carrier: e.target.value })}
              fullWidth
            />
            <FormControl fullWidth>
              <InputLabel>Status</InputLabel>
              <Select
                value={editData.status}
                onChange={(e) => setEditData({ ...editData, status: e.target.value })}
                label="Status"
              >
                <MenuItem value="pending">Pending</MenuItem>
                <MenuItem value="in_transit">In Transit</MenuItem>
                <MenuItem value="received">Received</MenuItem>
                <MenuItem value="prep_in_progress">Prep In Progress</MenuItem>
                <MenuItem value="prep_complete">Prep Complete</MenuItem>
                <MenuItem value="ready_for_fba">Ready for FBA</MenuItem>
                <MenuItem value="cancelled">Cancelled</MenuItem>
              </Select>
            </FormControl>
            <TextField
              label="Shipped Date"
              type="datetime-local"
              value={editData.shipped_date}
              onChange={(e) => setEditData({ ...editData, shipped_date: e.target.value })}
              fullWidth
              InputLabelProps={{ shrink: true }}
            />
            <TextField
              label="Expected Delivery Date"
              type="date"
              value={editData.expected_delivery_date}
              onChange={(e) => setEditData({ ...editData, expected_delivery_date: e.target.value })}
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

      {/* Item Edit Dialog */}
      <Dialog
        open={itemEditDialogOpen}
        onClose={() => {
          setItemEditDialogOpen(false);
          setSelectedItem(null);
        }}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Update Item</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
            {selectedItem && (
              <>
                <Typography variant="body2" color="text.secondary">
                  Product: {selectedItem.product?.title}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Expected Quantity: {selectedItem.quantity}
                </Typography>
              </>
            )}
            <TextField
              label="Quantity Received"
              type="number"
              value={itemEditData.quantity_received}
              onChange={(e) => setItemEditData({ ...itemEditData, quantity_received: parseInt(e.target.value) || 0 })}
              fullWidth
              inputProps={{ min: 0 }}
            />
            <TextField
              label="Quantity Prepped"
              type="number"
              value={itemEditData.quantity_prepped}
              onChange={(e) => setItemEditData({ ...itemEditData, quantity_prepped: parseInt(e.target.value) || 0 })}
              fullWidth
              inputProps={{ min: 0 }}
            />
            <FormControl fullWidth>
              <InputLabel>Prep Status</InputLabel>
              <Select
                value={itemEditData.prep_status}
                onChange={(e) => setItemEditData({ ...itemEditData, prep_status: e.target.value })}
                label="Prep Status"
              >
                <MenuItem value="pending">Pending</MenuItem>
                <MenuItem value="in_progress">In Progress</MenuItem>
                <MenuItem value="complete">Complete</MenuItem>
                <MenuItem value="not_required">Not Required</MenuItem>
              </Select>
            </FormControl>
            <TextField
              label="Prep Notes"
              value={itemEditData.prep_notes}
              onChange={(e) => setItemEditData({ ...itemEditData, prep_notes: e.target.value })}
              fullWidth
              multiline
              rows={2}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => {
              setItemEditDialogOpen(false);
              setSelectedItem(null);
            }}
            disabled={updating}
          >
            Cancel
          </Button>
          <Button
            onClick={handleUpdateItem}
            variant="contained"
            disabled={updating}
          >
            Update
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

