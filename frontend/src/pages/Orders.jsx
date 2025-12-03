import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box, Typography, Card, CardContent, Button, Chip, CircularProgress, IconButton,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper
} from '@mui/material';
import { Package, ExternalLink } from 'lucide-react';
import api from '../services/api';
import { useToast } from '../context/ToastContext';
import { formatCurrency } from '../utils/formatters';
import { habexa } from '../theme';

const Orders = () => {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const { showToast } = useToast();

  useEffect(() => {
    fetchOrders();
  }, []);

  const fetchOrders = async () => {
    try {
      setLoading(true);
      const response = await api.get('/orders?limit=100');
      setOrders(response.data || []);
    } catch (error) {
      console.error('Failed to fetch orders:', error);
      showToast('Failed to load orders', 'error');
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status) => {
    const colors = {
      pending: 'warning',
      confirmed: 'info',
      shipped: 'primary',
      received: 'success',
      cancelled: 'error',
    };
    return colors[status] || 'default';
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
        <CircularProgress />
      </Box>
    );
  }

  if (orders.length === 0) {
    return (
      <Box sx={{ p: 3 }}>
        <Typography variant="h4" fontWeight={700} mb={3}>
          Orders
        </Typography>
        <Card sx={{ p: 4, textAlign: 'center' }}>
          <Package size={48} style={{ color: '#8B8B9B', margin: '0 auto 16px' }} />
          <Typography variant="h6" sx={{ mb: 1 }}>No orders yet</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Create your first order from the buy list or products page
          </Typography>
          <Button
            variant="contained"
            onClick={() => navigate('/buy-list')}
            sx={{
              backgroundColor: habexa.purple.main,
              '&:hover': { backgroundColor: habexa.purple.dark },
              mr: 2,
            }}
          >
            View Buy List
          </Button>
          <Button
            variant="outlined"
            onClick={() => navigate('/products')}
          >
            Browse Products
          </Button>
        </Card>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" fontWeight={700} mb={3}>
        Orders
      </Typography>

      <Card>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Order ID</TableCell>
                <TableCell>Date</TableCell>
                <TableCell>ASIN</TableCell>
                <TableCell>Quantity</TableCell>
                <TableCell>Total</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {orders.map((order) => (
                <TableRow
                  key={order.id}
                  sx={{ cursor: 'pointer', '&:hover': { bgcolor: 'action.hover' } }}
                  onClick={() => navigate(`/orders/${order.id}`)}
                >
                  <TableCell>
                    <Typography variant="body2" fontFamily="monospace">
                      {order.id.slice(0, 8)}...
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">
                      {new Date(order.created_at).toLocaleDateString()}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" fontFamily="monospace">
                      {order.asin}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">
                      {order.quantity}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" fontWeight={600}>
                      {formatCurrency(order.total_cost || (order.unit_cost * order.quantity))}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={order.status || 'pending'}
                      color={getStatusColor(order.status)}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    <IconButton
                      size="small"
                      onClick={(e) => {
                        e.stopPropagation();
                        navigate(`/orders/${order.id}`);
                      }}
                    >
                      <ExternalLink size={16} />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Card>
    </Box>
  );
};

export default Orders;

