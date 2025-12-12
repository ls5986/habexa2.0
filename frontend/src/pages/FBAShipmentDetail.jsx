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
  Truck,
  Package,
  Download,
  CheckCircle,
} from 'lucide-react';
import api from '../services/api';
import { useToast } from '../context/ToastContext';

export default function FBAShipmentDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { showToast } = useToast();
  
  const [shipment, setShipment] = useState(null);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editData, setEditData] = useState({
    shipment_name: '',
    status: 'draft',
    shipment_type: 'SP',
    label_prep_type: 'SELLER_LABEL',
    carrier_name: '',
    tracking_number: '',
    shipped_date: '',
    delivered_date: '',
    received_date: '',
    estimated_shipping_cost: '',
    actual_shipping_cost: '',
    notes: '',
  });
  const [itemEditDialogOpen, setItemEditDialogOpen] = useState(false);
  const [selectedItem, setSelectedItem] = useState(null);
  const [itemEditData, setItemEditData] = useState({
    quantity_received: 0,
    box_id: '',
  });

  useEffect(() => {
    fetchShipment();
  }, [id]);

  const fetchShipment = async () => {
    setLoading(true);
    try {
      const response = await api.get(`/fba-shipments/${id}`);
      setShipment(response.data.fba_shipment);
      const s = response.data.fba_shipment;
      setEditData({
        shipment_name: s.shipment_name || '',
        status: s.status || 'draft',
        shipment_type: s.shipment_type || 'SP',
        label_prep_type: s.label_prep_type || 'SELLER_LABEL',
        carrier_name: s.carrier_name || '',
        tracking_number: s.tracking_number || '',
        shipped_date: s.shipped_date ? s.shipped_date.substring(0, 16) : '',
        delivered_date: s.delivered_date ? s.delivered_date.substring(0, 16) : '',
        received_date: s.received_date ? s.received_date.substring(0, 16) : '',
        estimated_shipping_cost: s.estimated_shipping_cost || '',
        actual_shipping_cost: s.actual_shipping_cost || '',
        notes: s.notes || '',
      });
    } catch (error) {
      console.error('Error fetching FBA shipment:', error);
      showToast('Failed to load FBA shipment', 'error');
      navigate('/fba-shipments');
    } finally {
      setLoading(false);
    }
  };

  const handleUpdate = async () => {
    setUpdating(true);
    try {
      await api.put(`/fba-shipments/${id}`, editData);
      showToast('Shipment updated', 'success');
      setEditDialogOpen(false);
      fetchShipment();
    } catch (error) {
      console.error('Error updating shipment:', error);
      showToast('Failed to update shipment', 'error');
    } finally {
      setUpdating(false);
    }
  };

  const handleUpdateItem = async () => {
    if (!selectedItem) return;

    setUpdating(true);
    try {
      await api.put(`/fba-shipments/${id}/items/${selectedItem.id}`, {
        quantity_received: itemEditData.quantity_received,
        box_id: itemEditData.box_id || null,
      });
      showToast('Item updated', 'success');
      setItemEditDialogOpen(false);
      setSelectedItem(null);
      fetchShipment();
    } catch (error) {
      console.error('Error updating item:', error);
      showToast('Failed to update item', 'error');
    } finally {
      setUpdating(false);
    }
  };

  const handleGenerateLabels = async () => {
    setUpdating(true);
    try {
      await api.post(`/fba-shipments/${id}/generate-fnsku-labels`);
      showToast('FNSKU labels generated', 'success');
      fetchShipment();
    } catch (error) {
      console.error('Error generating labels:', error);
      showToast('Failed to generate labels', 'error');
    } finally {
      setUpdating(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm('Are you sure you want to delete this FBA shipment?')) {
      return;
    }

    setUpdating(true);
    try {
      await api.delete(`/fba-shipments/${id}`);
      showToast('FBA shipment deleted', 'success');
      navigate('/fba-shipments');
    } catch (error) {
      console.error('Error deleting shipment:', error);
      showToast('Failed to delete shipment', 'error');
    } finally {
      setUpdating(false);
    }
  };

  const openItemEdit = (item) => {
    setSelectedItem(item);
    setItemEditData({
      quantity_received: item.quantity_received || 0,
      box_id: item.box_id || '',
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

  if (!shipment) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">FBA shipment not found</Alert>
      </Box>
    );
  }

  const statusColors = {
    draft: 'default',
    working: 'info',
    ready_to_ship: 'warning',
    shipped: 'primary',
    in_transit: 'info',
    delivered: 'success',
    received: 'success',
    closed: 'success',
    cancelled: 'error',
  };

  return (
    <Box sx={{ p: 3, bgcolor: '#f5f5f5', minHeight: '100vh' }}>
      {/* Header */}
      <Box sx={{ mb: 3, display: 'flex', alignItems: 'center', gap: 2 }}>
        <IconButton onClick={() => navigate('/fba-shipments')}>
          <ArrowLeft size={24} />
        </IconButton>
        <Box sx={{ flex: 1 }}>
          <Typography variant="h4" fontWeight={600}>
            {shipment.shipment_name || 'FBA Shipment'}
          </Typography>
          <Box sx={{ display: 'flex', gap: 1, mt: 1, alignItems: 'center' }}>
            <Chip
              label={shipment.status?.toUpperCase().replace('_', ' ') || 'DRAFT'}
              color={statusColors[shipment.status] || 'default'}
              size="small"
            />
            {shipment.shipment_id && (
              <Typography variant="body2" color="text.secondary">
                Shipment ID: {shipment.shipment_id}
              </Typography>
            )}
            {shipment.tracking_number && (
              <Typography variant="body2" color="text.secondary">
                Tracking: {shipment.tracking_number}
              </Typography>
            )}
          </Box>
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          {shipment.status === 'draft' && (
            <Button
              variant="contained"
              startIcon={<Download size={16} />}
              onClick={handleGenerateLabels}
              disabled={updating}
            >
              Generate FNSKU Labels
            </Button>
          )}
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
              <Typography variant="overline" color="text.secondary">Total SKUs</Typography>
              <Typography variant="h4" fontWeight={600}>
                {shipment.total_skus || shipment.items?.length || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="overline" color="text.secondary">Total Units</Typography>
              <Typography variant="h4" fontWeight={600}>
                {shipment.total_units || shipment.items?.reduce((sum, item) => sum + (item.quantity_shipped || 0), 0) || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="overline" color="text.secondary">Units Received</Typography>
              <Typography variant="h4" fontWeight={600} color="success.main">
                {shipment.items?.reduce((sum, item) => sum + (item.quantity_received || 0), 0) || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="overline" color="text.secondary">Total Boxes</Typography>
              <Typography variant="h4" fontWeight={600}>
                {shipment.total_boxes || shipment.boxes?.length || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Shipment Info */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" fontWeight={600} sx={{ mb: 2 }}>
            Shipment Information
          </Typography>
          <Grid container spacing={2}>
            {shipment.destination_fulfillment_center_id && (
              <Grid item xs={12} sm={6}>
                <Typography variant="body2" color="text.secondary">Destination FC</Typography>
                <Typography variant="body1" fontWeight={500}>
                  {shipment.destination_fulfillment_center_id}
                </Typography>
              </Grid>
            )}
            <Grid item xs={12} sm={6}>
              <Typography variant="body2" color="text.secondary">Shipment Type</Typography>
              <Typography variant="body1">{shipment.shipment_type || 'SP'}</Typography>
            </Grid>
            <Grid item xs={12} sm={6}>
              <Typography variant="body2" color="text.secondary">Label Prep Type</Typography>
              <Typography variant="body1">{shipment.label_prep_type || 'SELLER_LABEL'}</Typography>
            </Grid>
            {shipment.carrier_name && (
              <Grid item xs={12} sm={6}>
                <Typography variant="body2" color="text.secondary">Carrier</Typography>
                <Typography variant="body1">{shipment.carrier_name}</Typography>
              </Grid>
            )}
            {shipment.shipped_date && (
              <Grid item xs={12} sm={6}>
                <Typography variant="body2" color="text.secondary">Shipped Date</Typography>
                <Typography variant="body1">
                  {new Date(shipment.shipped_date).toLocaleString()}
                </Typography>
              </Grid>
            )}
            {shipment.delivered_date && (
              <Grid item xs={12} sm={6}>
                <Typography variant="body2" color="text.secondary">Delivered Date</Typography>
                <Typography variant="body1" color="success.main">
                  {new Date(shipment.delivered_date).toLocaleString()}
                </Typography>
              </Grid>
            )}
            {shipment.received_date && (
              <Grid item xs={12} sm={6}>
                <Typography variant="body2" color="text.secondary">Received Date</Typography>
                <Typography variant="body1" color="success.main">
                  {new Date(shipment.received_date).toLocaleString()}
                </Typography>
              </Grid>
            )}
          </Grid>
        </CardContent>
      </Card>

      {/* Items Table */}
      <Card>
        <CardContent>
          <Typography variant="h6" fontWeight={600} sx={{ mb: 2 }}>
            Products ({shipment.items?.length || 0})
          </Typography>
          {!shipment.items || shipment.items.length === 0 ? (
            <Alert severity="info">No products in this shipment</Alert>
          ) : (
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Product</TableCell>
                    <TableCell>ASIN</TableCell>
                    <TableCell>FNSKU</TableCell>
                    <TableCell align="right">Shipped</TableCell>
                    <TableCell align="right">Received</TableCell>
                    <TableCell>Label Status</TableCell>
                    <TableCell align="right">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {shipment.items.map((item) => (
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
                              SKU: {item.seller_sku || 'N/A'}
                            </Typography>
                          </Box>
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" fontFamily="monospace">
                          {item.asin || 'N/A'}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" fontFamily="monospace" color="primary.main">
                          {item.fnsku || 'Pending'}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Typography variant="body2">{item.quantity_shipped}</Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Typography
                          variant="body2"
                          color={item.quantity_received === item.quantity_shipped ? 'success.main' : 'text.secondary'}
                        >
                          {item.quantity_received || 0}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        {item.fnsku_label ? (
                          <Chip
                            label={item.fnsku_label.status?.toUpperCase() || 'PENDING'}
                            size="small"
                            color={
                              item.fnsku_label.status === 'applied' ? 'success' :
                              item.fnsku_label.status === 'printed' ? 'warning' :
                              item.fnsku_label.status === 'generated' ? 'info' : 'default'
                            }
                          />
                        ) : (
                          <Typography variant="body2" color="text.disabled">—</Typography>
                        )}
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

      {/* Boxes Table */}
      {shipment.boxes && shipment.boxes.length > 0 && (
        <Card sx={{ mt: 3 }}>
          <CardContent>
            <Typography variant="h6" fontWeight={600} sx={{ mb: 2 }}>
              Boxes ({shipment.boxes.length})
            </Typography>
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Box #</TableCell>
                    <TableCell>Name</TableCell>
                    <TableCell>Weight (lbs)</TableCell>
                    <TableCell>Dimensions</TableCell>
                    <TableCell>Tracking</TableCell>
                    <TableCell>Status</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {shipment.boxes.map((box) => (
                    <TableRow key={box.id}>
                      <TableCell>{box.box_number}</TableCell>
                      <TableCell>{box.box_name || `Box ${box.box_number}`}</TableCell>
                      <TableCell>{box.weight || '—'}</TableCell>
                      <TableCell>
                        {box.dimensions_length && box.dimensions_width && box.dimensions_height
                          ? `${box.dimensions_length}" × ${box.dimensions_width}" × ${box.dimensions_height}"`
                          : '—'}
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" fontFamily="monospace">
                          {box.tracking_number || '—'}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={box.status?.toUpperCase() || 'PENDING'}
                          size="small"
                          color={
                            box.status === 'received' ? 'success' :
                            box.status === 'delivered' ? 'success' :
                            box.status === 'shipped' ? 'info' : 'default'
                          }
                        />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      )}

      {/* Edit Dialog */}
      <Dialog
        open={editDialogOpen}
        onClose={() => setEditDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Edit FBA Shipment</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
            <TextField
              label="Shipment Name"
              value={editData.shipment_name}
              onChange={(e) => setEditData({ ...editData, shipment_name: e.target.value })}
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
                <MenuItem value="working">Working</MenuItem>
                <MenuItem value="ready_to_ship">Ready to Ship</MenuItem>
                <MenuItem value="shipped">Shipped</MenuItem>
                <MenuItem value="in_transit">In Transit</MenuItem>
                <MenuItem value="delivered">Delivered</MenuItem>
                <MenuItem value="received">Received</MenuItem>
                <MenuItem value="closed">Closed</MenuItem>
                <MenuItem value="cancelled">Cancelled</MenuItem>
              </Select>
            </FormControl>
            <TextField
              label="Carrier"
              value={editData.carrier_name}
              onChange={(e) => setEditData({ ...editData, carrier_name: e.target.value })}
              fullWidth
            />
            <TextField
              label="Tracking Number"
              value={editData.tracking_number}
              onChange={(e) => setEditData({ ...editData, tracking_number: e.target.value })}
              fullWidth
            />
            <TextField
              label="Shipped Date"
              type="datetime-local"
              value={editData.shipped_date}
              onChange={(e) => setEditData({ ...editData, shipped_date: e.target.value })}
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
                  Quantity Shipped: {selectedItem.quantity_shipped}
                </Typography>
              </>
            )}
            <TextField
              label="Quantity Received"
              type="number"
              value={itemEditData.quantity_received}
              onChange={(e) => setItemEditData({ ...itemEditData, quantity_received: parseInt(e.target.value) || 0 })}
              fullWidth
              inputProps={{ min: 0, max: selectedItem?.quantity_shipped }}
            />
            {shipment.boxes && shipment.boxes.length > 0 && (
              <FormControl fullWidth>
                <InputLabel>Box</InputLabel>
                <Select
                  value={itemEditData.box_id}
                  onChange={(e) => setItemEditData({ ...itemEditData, box_id: e.target.value })}
                  label="Box"
                >
                  <MenuItem value="">None</MenuItem>
                  {shipment.boxes.map((box) => (
                    <MenuItem key={box.id} value={box.id}>
                      {box.box_name || `Box ${box.box_number}`}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            )}
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

