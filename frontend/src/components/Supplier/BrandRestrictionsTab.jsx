import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  IconButton,
  Alert
} from '@mui/material';
import { Add, Delete, Edit } from '@mui/icons-material';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export default function BrandRestrictionsTab({ supplierId }) {
  const [restrictions, setRestrictions] = useState([]);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingRestriction, setEditingRestriction] = useState(null);
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    brand_name: '',
    restriction_type: 'cannot_sell',
    notes: ''
  });

  useEffect(() => {
    fetchRestrictions();
  }, [supplierId]);

  const fetchRestrictions = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      const response = await axios.get(
        `${API_URL}/api/v1/brand-restrictions?supplier_id=${supplierId}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setRestrictions(response.data || []);
    } catch (err) {
      console.error('Error fetching brand restrictions:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAdd = () => {
    setEditingRestriction(null);
    setFormData({
      brand_name: '',
      restriction_type: 'cannot_sell',
      notes: ''
    });
    setDialogOpen(true);
  };

  const handleEdit = (restriction) => {
    setEditingRestriction(restriction);
    setFormData({
      brand_name: restriction.brand_name,
      restriction_type: restriction.restriction_type,
      notes: restriction.notes || ''
    });
    setDialogOpen(true);
  };

  const handleSave = async () => {
    try {
      const token = localStorage.getItem('token');
      const url = editingRestriction
        ? `${API_URL}/api/v1/brand-restrictions/${editingRestriction.id}`
        : `${API_URL}/api/v1/brand-restrictions`;

      const payload = {
        brand_name: formData.brand_name,
        restriction_type: formData.restriction_type,
        is_global: false,
        supplier_id: supplierId,
        notes: formData.notes || null
      };

      if (editingRestriction) {
        await axios.put(url, payload, {
          headers: { Authorization: `Bearer ${token}` }
        });
      } else {
        await axios.post(url, payload, {
          headers: { Authorization: `Bearer ${token}` }
        });
      }

      setDialogOpen(false);
      fetchRestrictions();
    } catch (err) {
      console.error('Error saving brand restriction:', err);
      alert('Failed to save brand restriction: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleDelete = async (restrictionId) => {
    if (!window.confirm('Are you sure you want to delete this brand restriction?')) {
      return;
    }

    try {
      const token = localStorage.getItem('token');
      await axios.delete(
        `${API_URL}/api/v1/brand-restrictions/${restrictionId}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      fetchRestrictions();
    } catch (err) {
      console.error('Error deleting brand restriction:', err);
      alert('Failed to delete brand restriction: ' + (err.response?.data?.detail || err.message));
    }
  };

  const getRestrictionColor = (type) => {
    switch (type) {
      case 'cannot_sell':
        return 'error';
      case 'requires_approval':
        return 'warning';
      case 'can_sell':
        return 'success';
      default:
        return 'default';
    }
  };

  const getRestrictionLabel = (type) => {
    switch (type) {
      case 'cannot_sell':
        return 'Cannot Sell';
      case 'requires_approval':
        return 'Requires Approval';
      case 'can_sell':
        return 'Can Sell';
      default:
        return type;
    }
  };

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h6">Brand Restrictions</Typography>
        <Button
          variant="contained"
          startIcon={<Add />}
          onClick={handleAdd}
        >
          Add Brand Restriction
        </Button>
      </Box>

      <Alert severity="info" sx={{ mb: 2 }}>
        Configure which brands you can or cannot order from this supplier. This helps prevent
        ordering restricted products.
      </Alert>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Brand Name</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Notes</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {restrictions.length === 0 ? (
              <TableRow>
                <TableCell colSpan={4} align="center">
                  <Typography color="text.secondary" sx={{ py: 3 }}>
                    No brand restrictions configured. Click "Add Brand Restriction" to get started.
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              restrictions.map((restriction) => (
                <TableRow key={restriction.id}>
                  <TableCell>
                    <Typography fontWeight="medium">{restriction.brand_name}</Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={getRestrictionLabel(restriction.restriction_type)}
                      color={getRestrictionColor(restriction.restriction_type)}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" color="text.secondary">
                      {restriction.notes || '—'}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <IconButton
                      size="small"
                      onClick={() => handleEdit(restriction)}
                    >
                      <Edit fontSize="small" />
                    </IconButton>
                    <IconButton
                      size="small"
                      color="error"
                      onClick={() => handleDelete(restriction.id)}
                    >
                      <Delete fontSize="small" />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>
          {editingRestriction ? 'Edit Brand Restriction' : 'Add Brand Restriction'}
        </DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2 }}>
            <TextField
              label="Brand Name"
              value={formData.brand_name}
              onChange={(e) => setFormData({ ...formData, brand_name: e.target.value })}
              fullWidth
              required
              sx={{ mb: 2 }}
            />

            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>Restriction Type</InputLabel>
              <Select
                value={formData.restriction_type}
                onChange={(e) => setFormData({ ...formData, restriction_type: e.target.value })}
                label="Restriction Type"
              >
                <MenuItem value="can_sell">Can Sell</MenuItem>
                <MenuItem value="cannot_sell">Cannot Sell</MenuItem>
                <MenuItem value="requires_approval">Requires Approval</MenuItem>
              </Select>
            </FormControl>

            <TextField
              label="Notes"
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              fullWidth
              multiline
              rows={3}
              helperText="Optional notes about this brand restriction"
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleSave}
            disabled={!formData.brand_name}
          >
            {editingRestriction ? 'Update' : 'Add'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

