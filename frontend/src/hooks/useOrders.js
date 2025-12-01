import { useState, useEffect } from 'react';
import api from '../services/api';

export const useOrders = (filters = {}) => {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchOrders = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      
      if (filters.status) params.append('status', filters.status);
      if (filters.supplierId) params.append('supplier_id', filters.supplierId);
      if (filters.limit) params.append('limit', filters.limit);
      if (filters.offset) params.append('offset', filters.offset);

      const response = await api.get(`/orders?${params.toString()}`);
      setOrders(response.data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOrders();
  }, [JSON.stringify(filters)]);

  const createOrder = async (orderData) => {
    try {
      const response = await api.post('/orders', orderData);
      await fetchOrders();
      return response.data;
    } catch (err) {
      throw new Error(err.response?.data?.detail || 'Failed to create order');
    }
  };

  const updateOrder = async (orderId, orderData) => {
    try {
      const response = await api.put(`/orders/${orderId}`, orderData);
      await fetchOrders();
      return response.data;
    } catch (err) {
      throw new Error(err.response?.data?.detail || 'Failed to update order');
    }
  };

  const updateOrderStatus = async (orderId, status) => {
    try {
      const response = await api.put(`/orders/${orderId}/status?status=${status}`);
      await fetchOrders();
      return response.data;
    } catch (err) {
      throw new Error(err.response?.data?.detail || 'Failed to update order status');
    }
  };

  return {
    orders,
    loading,
    error,
    refetch: fetchOrders,
    createOrder,
    updateOrder,
    updateOrderStatus,
  };
};

