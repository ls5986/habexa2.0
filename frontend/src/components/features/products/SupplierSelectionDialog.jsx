import React, { useState, useEffect } from 'react';
import {
  Dialog, DialogTitle, DialogContent, DialogActions, Button,
  FormControl, InputLabel, Select, MenuItem, Typography, Box,
  Alert, TextField, Divider
} from '@mui/material';
import { Add as Plus } from '@mui/icons-material';
import { useSuppliers } from '../../../hooks/useSuppliers';
import SupplierFormModal from '../suppliers/SupplierFormModal';
import { useToast } from '../../../context/ToastContext';
import api from '../../../services/api';

export default function SupplierSelectionDialog({
  open,
  onClose,
  productsWithoutSuppliers = [],
  groupedByFile = {},
  productCount = 0,
  onConfirm
}) {
  const { suppliers, loading, createSupplier, refetch: fetchSuppliers } = useSuppliers();
  const { showToast } = useToast();
  const [selectedSupplierId, setSelectedSupplierId] = useState('');
  const [showNewSupplierForm, setShowNewSupplierForm] = useState(false);
  const [assigning, setAssigning] = useState(false);

  useEffect(() => {
    if (open && suppliers.length > 0 && !selectedSupplierId) {
      // Auto-select first supplier if available
      setSelectedSupplierId(suppliers[0].id);
    }
  }, [open, suppliers, selectedSupplierId]);

  const handleConfirm = async () => {
    if (!selectedSupplierId) {
      showToast('Please select a supplier', 'error');
      return;
    }

    setAssigning(true);
    try {
      // Assign supplier to all products without suppliers
      // Filter out placeholder products
      const productIds = productsWithoutSuppliers
        .map(p => p?.id || p?.product_id)
        .filter(id => id && !id.toString().startsWith('placeholder-'));
      
      if (productIds.length === 0) {
        // If we have placeholders (backend found products but couldn't fetch details),
        // use assign_all_pending flag to assign all products without suppliers
        const res = await api.post('/products/assign-supplier', {
          supplier_id: selectedSupplierId,
          assign_all_pending: true  // Assign all products without suppliers
        });
        
      const assignedCount = res.data.total || productsWithoutSuppliers.length;
      showToast(`Assigned supplier to ${assignedCount} products`, 'success');
      
      // Wait a moment for database to commit, then confirm
      setTimeout(() => {
        onConfirm(selectedSupplierId);
        onClose();
      }, 1000);
        return;
      }

      // Use bulk assign endpoint
      const res = await api.post('/products/assign-supplier', {
        product_ids: productIds,
        supplier_id: selectedSupplierId
      });

        const assignedCount = res.data.total;
        showToast(`Assigned supplier to ${assignedCount} products`, 'success');
        
        // Wait a moment for database to commit, then confirm
        setTimeout(() => {
          onConfirm(selectedSupplierId);
          onClose();
        }, 1000);
    } catch (err) {
      console.error('Failed to assign suppliers:', err);
      const errorMsg = err.response?.data?.detail?.message || err.response?.data?.detail || 'Failed to assign suppliers';
      showToast(errorMsg, 'error');
    } finally {
      setAssigning(false);
    }
  };

  const handleNewSupplierCreated = () => {
    // Refresh suppliers list - the hook will update automatically
    setShowNewSupplierForm(false);
    // The supplier will be selected automatically via useEffect when suppliers update
  };

  return (
    <>
      <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
        <DialogTitle>
          <Typography variant="h6" fontWeight={600}>
            Select Supplier for Analysis
          </Typography>
        </DialogTitle>
        
        <DialogContent>
          <Alert severity="warning" sx={{ mb: 3 }}>
            <Typography variant="body2" fontWeight={600} gutterBottom>
              {productCount || productsWithoutSuppliers.length} product{(productCount || productsWithoutSuppliers.length) !== 1 ? 's' : ''} {(productCount || productsWithoutSuppliers.length) === 1 ? 'has' : 'have'} no supplier assigned.
            </Typography>
            <Typography variant="body2">
              Analysis requires a supplier to track where products come from. Please select a supplier to assign to these products.
            </Typography>
          </Alert>

          <Box sx={{ mb: 2 }}>
            <FormControl fullWidth>
              <InputLabel>Supplier</InputLabel>
              <Select
                value={selectedSupplierId}
                onChange={(e) => setSelectedSupplierId(e.target.value)}
                label="Supplier"
                disabled={assigning || loading}
              >
                {suppliers.map((supplier) => (
                  <MenuItem key={supplier.id} value={supplier.id}>
                    {supplier.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Box>

          <Box sx={{ display: 'flex', justifyContent: 'center', mb: 2 }}>
            <Button
              startIcon={<Plus />}
              onClick={() => setShowNewSupplierForm(true)}
              variant="outlined"
              size="small"
            >
              Create New Supplier
            </Button>
          </Box>

          <Divider sx={{ my: 2 }} />

          {/* Show products grouped by file if available */}
          {Object.keys(groupedByFile).length > 0 ? (
            <Box sx={{ mb: 2 }}>
              <Typography variant="body2" fontWeight={600} gutterBottom>
                Products grouped by file:
              </Typography>
              {Object.entries(groupedByFile).map(([filename, products]) => (
                <Box key={filename} sx={{ mb: 1, p: 1, bgcolor: 'action.hover', borderRadius: 1 }}>
                  <Typography variant="caption" fontWeight={600} display="block">
                    {filename}: {products.length} product{products.length !== 1 ? 's' : ''}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {products.slice(0, 5).map(p => p.asin).join(', ')}
                    {products.length > 5 && ` ... and ${products.length - 5} more`}
                  </Typography>
                </Box>
              ))}
            </Box>
          ) : productsWithoutSuppliers.length > 0 && (
            <Typography variant="caption" color="text.secondary">
              Products: {productsWithoutSuppliers.slice(0, 10).map(p => p.asin).join(', ')}
              {productsWithoutSuppliers.length > 10 && ` ... and ${productsWithoutSuppliers.length - 10} more`}
            </Typography>
          )}
        </DialogContent>

        <DialogActions>
          <Button onClick={onClose} disabled={assigning}>
            Cancel
          </Button>
          <Button
            onClick={handleConfirm}
            variant="contained"
            disabled={!selectedSupplierId || assigning}
          >
            {assigning ? 'Assigning...' : `Assign to ${productCount || productsWithoutSuppliers.length} Product${(productCount || productsWithoutSuppliers.length) !== 1 ? 's' : ''}`}
          </Button>
        </DialogActions>
      </Dialog>

      <SupplierFormModal
        open={showNewSupplierForm}
        onClose={async () => {
          setShowNewSupplierForm(false);
          // Refresh suppliers after modal closes (in case new one was created)
          if (fetchSuppliers) {
            await fetchSuppliers();
          }
        }}
        supplier={null}
      />
    </>
  );
}

