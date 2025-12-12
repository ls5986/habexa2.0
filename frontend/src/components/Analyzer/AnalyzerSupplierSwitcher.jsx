import React, { useState, useEffect } from 'react';
import {
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  CircularProgress
} from '@mui/material';
import api from '../../services/api';

export default function AnalyzerSupplierSwitcher({
  currentSupplier,
  onSupplierChange
}) {
  const [suppliers, setSuppliers] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSuppliers();
  }, []);

  const fetchSuppliers = async () => {
    try {
      const response = await api.get('/suppliers');
      setSuppliers(response.data || []);
    } catch (error) {
      console.error('Failed to fetch suppliers:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <CircularProgress size={20} />;
  }

  return (
    <FormControl size="small" sx={{ minWidth: 200 }}>
      <InputLabel>Supplier</InputLabel>
      <Select
        value={currentSupplier}
        label="Supplier"
        onChange={(e) => onSupplierChange(e.target.value)}
      >
        <MenuItem value="all">All Suppliers</MenuItem>
        {suppliers.map((supplier) => (
          <MenuItem key={supplier.id} value={supplier.id}>
            {supplier.name}
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  );
}

