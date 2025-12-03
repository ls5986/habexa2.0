import { Box, Typography, Button, Card, CardContent, Avatar, Chip, IconButton, Alert } from '@mui/material';
import { Plus, MessageCircle, Package, Edit } from 'lucide-react';
import { useState } from 'react';
import { useSuppliers } from '../hooks/useSuppliers';
import { useFeatureGate } from '../hooks/useFeatureGate';
import { getInitials, formatCurrency } from '../utils/formatters';
import EmptyState from '../components/common/EmptyState';
import { Users } from 'lucide-react';
import SupplierFormModal from '../components/features/suppliers/SupplierFormModal';
import UsageDisplay from '../components/common/UsageDisplay';
import UpgradePrompt from '../components/common/UpgradePrompt';
import { habexa } from '../theme';

const Suppliers = () => {
  const { suppliers, loading } = useSuppliers();
  const [formOpen, setFormOpen] = useState(false);
  const [editingSupplier, setEditingSupplier] = useState(null);
  const [showUpgrade, setShowUpgrade] = useState(false);
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
            <Card key={supplier.id}>
              <CardContent>
                <Box display="flex" gap={3}>
                  <Avatar
                    sx={{
                      width: 56,
                      height: 56,
                      backgroundColor: habexa.purple.main, // Changed from #7C6AFA for consistency
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
                      >
                        Message
                      </Button>
                      <Button
                        size="small"
                        startIcon={<Package size={14} />}
                        variant="outlined"
                      >
                        Orders
                      </Button>
                      <IconButton
                        size="small"
                        onClick={() => handleEditSupplier(supplier)}
                        sx={{ ml: 'auto' }}
                      >
                        <Edit size={16} />
                      </IconButton>
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
    </Box>
  );
};

export default Suppliers;

