import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  Box, 
  Paper, 
  Typography, 
  Tabs, 
  Tab, 
  IconButton, 
  Avatar, 
  Stack, 
  Chip, 
  Breadcrumbs, 
  Link,
  CircularProgress,
  Alert
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import RefreshIcon from '@mui/icons-material/Refresh';
import SupplierProductsTab from '../components/SupplierDetail/SupplierProductsTab';
import SupplierOrdersTab from '../components/SupplierDetail/SupplierOrdersTab';
import SupplierTemplatesTab from '../components/SupplierDetail/SupplierTemplatesTab';
import BrandRestrictionsTab from '../components/Supplier/BrandRestrictionsTab';
import DeleteSupplierDialog from '../components/Suppliers/DeleteSupplierDialog';
import api from '../services/api';

export default function SupplierDetail() {
  const { supplierId } = useParams();
  const navigate = useNavigate();
  const [supplier, setSupplier] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [currentTab, setCurrentTab] = useState(0);
  const [deleteDialog, setDeleteDialog] = useState(false);

  useEffect(() => { 
    fetchSupplier(); 
  }, [supplierId]);

  const fetchSupplier = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get(`/suppliers/${supplierId}`);
      setSupplier(response.data);
    } catch (err) {
      console.error('Error fetching supplier:', err);
      setError('Supplier not found');
      setTimeout(() => navigate('/suppliers'), 2000);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (deleteProducts) => {
    try {
      const url = `/suppliers/${supplierId}`;
      await api.delete(deleteProducts ? `${url}?delete_products=true` : url);
      navigate('/suppliers');
    } catch (err) {
      alert('Failed to delete supplier');
    }
  };

  const getInitials = (name) => {
    if (!name) return '??';
    return name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error || !supplier) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">{error || 'Supplier not found'}</Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Breadcrumbs sx={{ mb: 2 }}>
        <Link 
          underline="hover" 
          color="inherit" 
          onClick={() => navigate('/suppliers')} 
          sx={{ cursor: 'pointer' }}
        >
          Suppliers
        </Link>
        <Typography color="text.primary">{supplier.name}</Typography>
      </Breadcrumbs>

      <Paper sx={{ p: 3, mb: 3 }}>
        <Box display="flex" alignItems="start" gap={3}>
          <IconButton onClick={() => navigate('/suppliers')}>
            <ArrowBackIcon />
          </IconButton>

          <Avatar 
            sx={{ 
              bgcolor: 'primary.main', 
              width: 80, 
              height: 80, 
              fontSize: 28, 
              fontWeight: 'bold' 
            }}
          >
            {getInitials(supplier.name)}
          </Avatar>

          <Box flex={1}>
            <Typography variant="h4" fontWeight="bold" gutterBottom>
              {supplier.name}
            </Typography>
            {supplier.website && (
              <Typography variant="body2" color="text.secondary" gutterBottom>
                {supplier.website}
              </Typography>
            )}
            <Stack direction="row" spacing={2} mt={2}>
              <Chip 
                label={`${supplier.products_count || supplier.deals_count || 0} Products`} 
                variant="outlined" 
              />
              <Chip 
                label={`${supplier.orders_count || 0} Orders`} 
                variant="outlined" 
              />
              <Chip 
                label={`${supplier.avg_roi || 0}% Avg ROI`} 
                color={supplier.avg_roi > 30 ? 'success' : 'default'} 
              />
            </Stack>
          </Box>

          <Stack direction="row" spacing={1}>
            <IconButton onClick={fetchSupplier}>
              <RefreshIcon />
            </IconButton>
            <IconButton onClick={() => navigate(`/suppliers/${supplierId}/edit`)}>
              <EditIcon />
            </IconButton>
            <IconButton onClick={() => setDeleteDialog(true)} color="error">
              <DeleteIcon />
            </IconButton>
          </Stack>
        </Box>
      </Paper>

      <Paper sx={{ mb: 2 }}>
        <Tabs value={currentTab} onChange={(e, v) => setCurrentTab(v)}>
          <Tab label="Products" />
          <Tab label="Orders" />
          <Tab label="Templates" />
          <Tab label="Brand Restrictions" />
          <Tab label="Analytics" />
          <Tab label="Settings" />
        </Tabs>
      </Paper>

      <Box>
        {currentTab === 0 && <SupplierProductsTab supplierId={supplierId} />}
        {currentTab === 1 && <SupplierOrdersTab supplierId={supplierId} />}
        {currentTab === 2 && <SupplierTemplatesTab supplierId={supplierId} />}
        {currentTab === 3 && <BrandRestrictionsTab supplierId={supplierId} />}
        {currentTab === 4 && (
          <Paper sx={{ p: 4, textAlign: 'center' }}>
            <Typography>Analytics coming soon</Typography>
          </Paper>
        )}
        {currentTab === 5 && (
          <Paper sx={{ p: 4, textAlign: 'center' }}>
            <Typography>Settings coming soon</Typography>
          </Paper>
        )}
      </Box>

      <DeleteSupplierDialog 
        open={deleteDialog} 
        supplier={supplier} 
        onClose={() => setDeleteDialog(false)} 
        onConfirm={handleDelete} 
      />
    </Box>
  );
}

