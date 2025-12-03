import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box, Typography, Card, CardContent, Chip, CircularProgress, Button,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow
} from '@mui/material';
import { ArrowLeft, Package } from 'lucide-react';
import api from '../services/api';
import { useToast } from '../context/ToastContext';
import { formatCurrency } from '../utils/formatters';
import { habexa } from '../theme';

const OrderDetails = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { showToast } = useToast();
  const [order, setOrder] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (id) {
      fetchOrder();
    }
  }, [id]);

  const fetchOrder = async () => {
    try {
      setLoading(true);
      const response = await api.get(`/orders/${id}`);
      setOrder(response.data);
    } catch (error) {
      console.error('Failed to fetch order:', error);
      showToast('Failed to load order details', 'error');
      navigate('/orders');
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

  if (!order) {
    return (
      <Box sx={{ p: 3 }}>
        <Button
          startIcon={<ArrowLeft size={16} />}
          onClick={() => navigate('/orders')}
          sx={{ mb: 3 }}
        >
          Back to Orders
        </Button>
        <Card sx={{ p: 4, textAlign: 'center' }}>
          <Typography variant="h6" color="error">
            Order not found
          </Typography>
        </Card>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Button
        startIcon={<ArrowLeft size={16} />}
        onClick={() => navigate('/orders')}
        sx={{ mb: 3 }}
      >
        Back to Orders
      </Button>

      <Typography variant="h4" fontWeight={700} mb={3}>
        Order Details
      </Typography>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box display="flex" justifyContent="space-between" alignItems="start" mb={3}>
            <Box>
              <Typography variant="body2" color="text.secondary" mb={1}>
                Order ID
              </Typography>
              <Typography variant="body1" fontFamily="monospace">
                {order.id}
              </Typography>
            </Box>
            <Chip
              label={order.status || 'pending'}
              color={getStatusColor(order.status)}
              sx={{ fontWeight: 600 }}
            />
          </Box>

          <Box display="flex" gap={4} flexWrap="wrap">
            <Box>
              <Typography variant="body2" color="text.secondary" mb={1}>
                Date
              </Typography>
              <Typography variant="body1">
                {new Date(order.created_at).toLocaleString()}
              </Typography>
            </Box>
            {order.supplier_id && (
              <Box>
                <Typography variant="body2" color="text.secondary" mb={1}>
                  Supplier
                </Typography>
                <Typography variant="body1">
                  {order.suppliers?.name || 'Unknown'}
                </Typography>
              </Box>
            )}
          </Box>
        </CardContent>
      </Card>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" fontWeight={600} mb={2}>
            Items
          </Typography>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>ASIN</TableCell>
                  <TableCell align="right">Quantity</TableCell>
                  <TableCell align="right">Unit Cost</TableCell>
                  <TableCell align="right">Subtotal</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                <TableRow>
                  <TableCell>
                    <Typography variant="body2" fontFamily="monospace">
                      {order.asin}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Typography variant="body2">
                      {order.quantity}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Typography variant="body2">
                      {formatCurrency(order.unit_cost || 0)}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Typography variant="body2" fontWeight={600}>
                      {formatCurrency(order.total_cost || (order.unit_cost * order.quantity))}
                    </Typography>
                  </TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          <Box display="flex" justifyContent="space-between" alignItems="center">
            <Typography variant="h6" fontWeight={600}>
              Total
            </Typography>
            <Typography variant="h5" fontWeight={700} color={habexa.purple.main}>
              {formatCurrency(order.total_cost || (order.unit_cost * order.quantity))}
            </Typography>
          </Box>
          {order.notes && (
            <Box mt={3}>
              <Typography variant="body2" color="text.secondary" mb={1}>
                Notes
              </Typography>
              <Typography variant="body2">
                {order.notes}
              </Typography>
            </Box>
          )}
        </CardContent>
      </Card>
    </Box>
  );
};

export default OrderDetails;

