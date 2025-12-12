import { Box, Typography, Button, Card, CardContent, Avatar, Chip, IconButton, Alert, Menu, MenuItem } from '@mui/material';
import { Plus, MessageCircle, Package, Edit, MoreVertical, Trash2 } from 'lucide-react';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useSuppliers } from '../context/SuppliersContext';
import { useFeatureGate } from '../hooks/useFeatureGate';
import { getInitials, formatCurrency } from '../utils/formatters';
import EmptyState from '../components/common/EmptyState';
import { Users } from 'lucide-react';
import SupplierFormModal from '../components/features/suppliers/SupplierFormModal';
import UsageDisplay from '../components/common/UsageDisplay';
import UpgradePrompt from '../components/common/UpgradePrompt';
import DeleteSupplierDialog from '../components/Suppliers/DeleteSupplierDialog';
import { habexa } from '../theme';
import api from '../services/api';

const Suppliers = () => {
  const navigate = useNavigate();
  const { suppliers, loading, refetch, refreshSuppliers } = useSuppliers();
  const [formOpen, setFormOpen] = useState(false);
  const [editingSupplier, setEditingSupplier] = useState(null);
  const [showUpgrade, setShowUpgrade] = useState(false);
  const [deleteDialog, setDeleteDialog] = useState({ open: false, supplier: null });
  const [menuAnchor, setMenuAnchor] = useState(null);
  const [selectedSupplier, setSelectedSupplier] = useState(null);
  const { gateFeature, getLimit, isLimitReached } = useFeatureGate();

  const handleAddSupplier = () => {
    // Check limit before opening form
    if (!gateFeature('suppliers', suppliers.length)) {
      setShowUpgrade(true);
      return;
    }
    
    setEditingSupplier(null);
    setFormOpen(true);
  };

  const handleEditSupplier = (supplier) => {
    setEditingSupplier(supplier);
    setFormOpen(true);
  };

  const handleDeleteConfirm = async (deleteProducts) => {
    try {
      const url = `/suppliers/${deleteDialog.supplier.id}`;
      await api.delete(deleteProducts ? `${url}?delete_products=true` : url);
      if (refetch) {
        refetch();
      } else if (refreshSuppliers) {
        refreshSuppliers();
      }
      setDeleteDialog({ open: false, supplier: null });
    } catch (err) {
      alert('Failed to delete supplier');
    }
  };

  const handleSupplierClick = (supplier) => {
    navigate(`/suppliers/${supplier.id}`);
  };

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box>
          <Typography variant="h4" fontWeight={700} mb={1}>
            Suppliers
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Manage your supplier relationships
          </Typography>
        </Box>
        <Button
          variant="contained"
          startIcon={<Plus size={16} />}
          onClick={handleAddSupplier}
          sx={{
            backgroundColor: habexa.purple.main, // Changed from #7C6AFA for consistency
            '&:hover': { backgroundColor: habexa.purple.dark },
          }}
        >
          Add Supplier
        </Button>
      </Box>

      {loading ? (
        <Typography>Loading...</Typography>
      ) : suppliers.length === 0 ? (
        <EmptyState
          icon={Users}
          title="No suppliers yet"
          message="Add your first supplier to start tracking deals"
          actionLabel="Add Supplier"
        />
      ) : (
        <Box display="flex" flexDirection="column" gap={2}>
          {suppliers.map((supplier) => (
            <Card 
              key={supplier.id}
              sx={{ 
                cursor: 'pointer',
                '&:hover': { 
                  transform: 'translateY(-2px)', 
                  boxShadow: 4,
                  transition: 'all 0.2s ease'
                }
              }}
              onClick={() => handleSupplierClick(supplier)}
            >
              <CardContent>
                <Box display="flex" gap={3}>
                  <Avatar
                    sx={{
                      width: 56,
                      height: 56,
                      backgroundColor: habexa.purple.main,
                      fontSize: '1.25rem',
                      fontWeight: 700,
                    }}
                  >
                    {getInitials(supplier.name)}
                  </Avatar>
                  <Box flex={1}>
                    <Box display="flex" justifyContent="space-between" alignItems="start" mb={2}>
                      <Box>
                        <Typography variant="h6" fontWeight={600} mb={0.5}>
                          {supplier.name}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          {supplier.telegram_username && `📱 ${supplier.telegram_username}`}
                          {supplier.whatsapp_number && ` • 📱 ${supplier.whatsapp_number}`}
                          {supplier.email && ` • 📧 ${supplier.email}`}
                        </Typography>
                      </Box>
                      <IconButton
                        size="small"
                        onClick={(e) => {
                          e.stopPropagation();
                          setMenuAnchor(e.currentTarget);
                          setSelectedSupplier(supplier);
                        }}
                      >
                        <MoreVertical size={16} />
                      </IconButton>
                    </Box>
                    <Box display="flex" gap={3} mb={2}>
                      <Box>
                        <Typography variant="body2" color="text.secondary">
                          Deals
                        </Typography>
                        <Typography variant="body1" fontWeight={600}>
                          {supplier.deals_analyzed || 0}
                        </Typography>
                      </Box>
                      <Box>
                        <Typography variant="body2" color="text.secondary">
                          Purchased
                        </Typography>
                        <Typography variant="body1" fontWeight={600}>
                          {supplier.deals_purchased || 0}
                        </Typography>
                      </Box>
                      <Box>
                        <Typography variant="body2" color="text.secondary">
                          Avg ROI
                        </Typography>
                        <Typography variant="body1" fontWeight={600} color="success.main">
                          {supplier.avg_roi || 0}%
                        </Typography>
                      </Box>
                    </Box>
                    {supplier.tags && supplier.tags.length > 0 && (
                      <Box display="flex" gap={1} mb={2} flexWrap="wrap">
                        {supplier.tags.map((tag, i) => (
                          <Chip key={i} label={tag} size="small" />
                        ))}
                      </Box>
                    )}
                    <Box display="flex" gap={1}>
                      <Button
                        size="small"
                        startIcon={<MessageCircle size={14} />}
                        variant="outlined"
                        onClick={(e) => e.stopPropagation()}
                      >
                        Message
                      </Button>
                      <Button
                        size="small"
                        startIcon={<Package size={14} />}
                        variant="outlined"
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate(`/orders/new?supplier=${supplier.id}`);
                        }}
                      >
                        Orders
                      </Button>
                    </Box>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          ))}
        </Box>
      )}

      <SupplierFormModal
        open={formOpen}
        onClose={() => {
          setFormOpen(false);
          setEditingSupplier(null);
        }}
        supplier={editingSupplier}
      />

      <UpgradePrompt
        open={showUpgrade}
        onClose={() => setShowUpgrade(false)}
        feature="suppliers"
        currentUsage={suppliers.length}
        limit={getLimit('suppliers')}
      />

      <Menu 
        anchorEl={menuAnchor} 
        open={Boolean(menuAnchor)} 
        onClose={() => setMenuAnchor(null)}
      >
        <MenuItem 
          onClick={() => {
            handleEditSupplier(selectedSupplier);
            setMenuAnchor(null);
          }}
        >
          <Edit size={14} style={{ marginRight: 8 }} />
          Edit
        </MenuItem>
        <MenuItem 
          onClick={() => {
            setDeleteDialog({ open: true, supplier: selectedSupplier });
            setMenuAnchor(null);
          }}
          sx={{ color: 'error.main' }}
        >
          <Trash2 size={14} style={{ marginRight: 8 }} />
          Delete
        </MenuItem>
      </Menu>

      <DeleteSupplierDialog
        open={deleteDialog.open}
        supplier={deleteDialog.supplier}
        onClose={() => setDeleteDialog({ open: false, supplier: null })}
        onConfirm={handleDeleteConfirm}
      />
    </Box>
  );
};

export default Suppliers;

