import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Button,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  CircularProgress,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
} from '@mui/material';
import {
  Plus,
  ArrowRight,
  Edit,
  Delete,
  ShoppingCart,
} from 'lucide-react';
import api from '../services/api';
import { useToast } from '../context/ToastContext';
import { formatCurrency, formatPercentage } from '../utils/formatters';

export default function BuyLists() {
  const navigate = useNavigate();
  const { showToast } = useToast();
  
  const [buyLists, setBuyLists] = useState([]);
  const [loading, setLoading] = useState(true);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [newBuyListName, setNewBuyListName] = useState('');
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    fetchBuyLists();
  }, []);

  const fetchBuyLists = async () => {
    setLoading(true);
    try {
      const response = await api.get('/buy-lists');
      setBuyLists(response.data.buy_lists || []);
    } catch (error) {
      console.error('Error fetching buy lists:', error);
      showToast('Failed to load buy lists', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateBuyList = async () => {
    if (!newBuyListName.trim()) {
      showToast('Please enter a buy list name', 'warning');
      return;
    }

    setCreating(true);
    try {
      const response = await api.post('/buy-lists', {
        name: newBuyListName.trim()
      });
      showToast('Buy list created', 'success');
      setCreateDialogOpen(false);
      setNewBuyListName('');
      navigate(`/buy-lists/${response.data.buy_list.id}`);
    } catch (error) {
      console.error('Error creating buy list:', error);
      showToast('Failed to create buy list', 'error');
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (buyListId, buyListName) => {
    if (!window.confirm(`Delete buy list "${buyListName}"?`)) {
      return;
    }

    try {
      await api.delete(`/buy-lists/${buyListId}`);
      showToast('Buy list deleted', 'success');
      fetchBuyLists();
    } catch (error) {
      console.error('Error deleting buy list:', error);
      showToast('Failed to delete buy list', 'error');
    }
  };

  const statusColors = {
    draft: 'default',
    approved: 'success',
    ordered: 'info',
    received: 'success',
    archived: 'default',
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3, bgcolor: '#f5f5f5', minHeight: '100vh' }}>
      {/* Header */}
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h4" fontWeight={600}>
          Buy Lists
        </Typography>
        <Button
          variant="contained"
          startIcon={<Plus size={16} />}
          onClick={() => setCreateDialogOpen(true)}
        >
          Create Buy List
        </Button>
      </Box>

      {/* Buy Lists Table */}
      {buyLists.length === 0 ? (
        <Card>
          <CardContent sx={{ textAlign: 'center', py: 6 }}>
            <ShoppingCart size={48} style={{ color: '#8B8B9B', margin: '0 auto 16px' }} />
            <Typography variant="h6" sx={{ mb: 1 }}>No buy lists yet</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              Create a buy list to start organizing your product purchases
            </Typography>
            <Button
              variant="contained"
              startIcon={<Plus size={16} />}
              onClick={() => setCreateDialogOpen(true)}
            >
              Create Your First Buy List
            </Button>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Name</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell align="right">Products</TableCell>
                  <TableCell align="right">Units</TableCell>
                  <TableCell align="right">Total Cost</TableCell>
                  <TableCell align="right">Expected Profit</TableCell>
                  <TableCell align="right">Expected ROI</TableCell>
                  <TableCell>Created</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {buyLists.map((buyList) => (
                  <TableRow
                    key={buyList.id}
                    hover
                    sx={{ cursor: 'pointer' }}
                    onClick={() => navigate(`/buy-lists/${buyList.id}`)}
                  >
                    <TableCell>
                      <Typography variant="body2" fontWeight={600}>
                        {buyList.name}
                      </Typography>
                      {buyList.description && (
                        <Typography variant="caption" color="text.secondary">
                          {buyList.description}
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={buyList.status?.toUpperCase() || 'DRAFT'}
                        color={statusColors[buyList.status] || 'default'}
                        size="small"
                      />
                    </TableCell>
                    <TableCell align="right">
                      {buyList.total_products || 0}
                    </TableCell>
                    <TableCell align="right">
                      {buyList.total_units || 0}
                    </TableCell>
                    <TableCell align="right">
                      <Typography variant="body2" fontWeight={600}>
                        {formatCurrency(buyList.total_cost || 0)}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      <Typography
                        variant="body2"
                        color={buyList.expected_profit && buyList.expected_profit > 0 ? 'success.main' : 'text.secondary'}
                      >
                        {formatCurrency(buyList.expected_profit || 0)}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      {buyList.expected_roi ? (
                        <Chip
                          label={formatPercentage(buyList.expected_roi)}
                          size="small"
                          color={buyList.expected_roi >= 50 ? 'success' : buyList.expected_roi >= 30 ? 'warning' : buyList.expected_roi >= 15 ? 'info' : 'error'}
                        />
                      ) : (
                        <Typography variant="body2" color="text.disabled">—</Typography>
                      )}
                    </TableCell>
                    <TableCell>
                      <Typography variant="caption" color="text.secondary">
                        {new Date(buyList.created_at).toLocaleDateString()}
                      </Typography>
                    </TableCell>
                    <TableCell align="right" onClick={(e) => e.stopPropagation()}>
                      <IconButton
                        size="small"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDelete(buyList.id, buyList.name);
                        }}
                        color="error"
                      >
                        <Delete size={16} />
                      </IconButton>
                      <IconButton
                        size="small"
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate(`/buy-lists/${buyList.id}`);
                        }}
                      >
                        <ArrowRight size={16} />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Card>
      )}

      {/* Create Buy List Dialog */}
      <Dialog
        open={createDialogOpen}
        onClose={() => {
          setCreateDialogOpen(false);
          setNewBuyListName('');
        }}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Create New Buy List</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            fullWidth
            label="Buy List Name"
            value={newBuyListName}
            onChange={(e) => setNewBuyListName(e.target.value)}
            placeholder="e.g., KEHE Order #47 - Dec 2025"
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => {
              setCreateDialogOpen(false);
              setNewBuyListName('');
            }}
            disabled={creating}
          >
            Cancel
          </Button>
          <Button
            onClick={handleCreateBuyList}
            variant="contained"
            disabled={creating || !newBuyListName.trim()}
            startIcon={<Plus size={16} />}
          >
            {creating ? 'Creating...' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

