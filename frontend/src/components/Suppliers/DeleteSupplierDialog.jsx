import React, { useState } from 'react';
import { Dialog, DialogTitle, DialogContent, DialogActions, Button, Alert, Typography, Box, Checkbox, FormControlLabel } from '@mui/material';
import WarningIcon from '@mui/icons-material/Warning';

export default function DeleteSupplierDialog({ open, supplier, onClose, onConfirm }) {
  const [deleteProducts, setDeleteProducts] = useState(false);
  const [loading, setLoading] = useState(false);

  if (!supplier) return null;

  const handleConfirm = async () => {
    setLoading(true);
    try {
      await onConfirm(deleteProducts);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        <Box display="flex" alignItems="center" gap={1}>
          <WarningIcon color="error" />
          <Typography variant="h6">Delete Supplier?</Typography>
        </Box>
      </DialogTitle>
      <DialogContent>
        <Alert severity="warning" sx={{ mb: 2 }}>
          <Typography variant="body2" fontWeight="bold" gutterBottom>
            You are about to delete "{supplier.name}"
          </Typography>
          <Typography variant="body2">This action cannot be undone.</Typography>
        </Alert>

        {supplier.deals_count > 0 && (
          <Alert severity="info" sx={{ mb: 2 }}>
            <Typography variant="body2">
              This supplier has <strong>{supplier.deals_count} products</strong>.
            </Typography>
          </Alert>
        )}

        <FormControlLabel
          control={<Checkbox checked={deleteProducts} onChange={(e) => setDeleteProducts(e.target.checked)} />}
          label={<Typography variant="body2">
            Also delete all products from this supplier ({supplier.deals_count || 0} products)
          </Typography>}
        />

        <Alert severity="error" sx={{ mt: 2 }}>
          <Typography variant="caption">
            If unchecked, products will remain but will no longer be linked to this supplier.
          </Typography>
        </Alert>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={loading}>Cancel</Button>
        <Button onClick={handleConfirm} variant="contained" color="error" disabled={loading}>
          {loading ? 'Deleting...' : `Delete ${supplier.name}`}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

