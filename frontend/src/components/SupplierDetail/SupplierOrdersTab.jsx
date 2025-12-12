import React, { useState, useEffect } from 'react';
import { Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography, Box, Button, Chip } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import AddIcon from '@mui/icons-material/Add';
import api from '../../services/api';

export default function SupplierOrdersTab({ supplierId }) {
  const navigate = useNavigate();
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { fetchOrders(); }, [supplierId]);

  const fetchOrders = async () => {
    try {
      const response = await api.get(`/supplier-orders?supplier_id=${supplierId}`);
      setOrders(response.data?.orders || response.data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status) => {
    const colors = { 
      'draft': 'default', 
      'sent': 'info', 
      'confirmed': 'primary', 
      'in_transit': 'warning', 
      'received': 'success', 
      'cancelled': 'error' 
    };
    return colors[status] || 'default';
  };

  const formatDate = (d) => {
    if (!d) return '-';
    const date = new Date(d);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  return (
    <Paper sx={{ p: 2 }}>
      <Box display="flex" justifyContent="space-between" mb={2}>
        <Typography variant="h6" fontWeight="bold">Order History ({orders.length})</Typography>
        <Button 
          variant="contained" 
          startIcon={<AddIcon />} 
          onClick={() => navigate(`/orders/new?supplier=${supplierId}`)}
        >
          New Order
        </Button>
      </Box>

      <TableContainer>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Order #</TableCell>
              <TableCell>Date</TableCell>
              <TableCell>Items</TableCell>
              <TableCell>Total</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={6} align="center">Loading...</TableCell>
              </TableRow>
            ) : orders.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} align="center">
                  <Typography variant="body2" color="text.secondary">No orders yet</Typography>
                  <Button 
                    size="small" 
                    variant="outlined" 
                    onClick={() => navigate(`/orders/new?supplier=${supplierId}`)} 
                    sx={{ mt: 2 }}
                  >
                    Create First Order
                  </Button>
                </TableCell>
              </TableRow>
            ) : (
              orders.map(o => (
                <TableRow 
                  key={o.id} 
                  hover 
                  onClick={() => navigate(`/supplier-orders/${o.id}`)} 
                  sx={{ cursor: 'pointer' }}
                >
                  <TableCell>
                    <Typography variant="body2" fontWeight="bold">
                      #{o.order_number || o.id.slice(0, 8)}
                    </Typography>
                  </TableCell>
                  <TableCell>{formatDate(o.created_at)}</TableCell>
                  <TableCell>{o.total_products || o.items_count || 0} items</TableCell>
                  <TableCell>
                    <Typography variant="body2" fontWeight="bold">
                      ${(o.total_cost || 0).toFixed(2)}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip 
                      label={o.status || 'draft'} 
                      color={getStatusColor(o.status)} 
                      size="small" 
                    />
                  </TableCell>
                  <TableCell>
                    <Button 
                      size="small" 
                      onClick={(e) => { 
                        e.stopPropagation(); 
                        navigate(`/supplier-orders/${o.id}`); 
                      }}
                    >
                      View
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Paper>
  );
}

