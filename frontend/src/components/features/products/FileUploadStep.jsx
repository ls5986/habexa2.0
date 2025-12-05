import React, { useState, useEffect } from 'react';
import {
  Box, Typography, Button, TextField, FormControl, InputLabel,
  Select, MenuItem, IconButton, CircularProgress, Alert
} from '@mui/material';
import { Upload as UploadIcon, Add as AddIcon, Close as CloseIcon } from '@mui/icons-material';
import api from '../../../services/api';

export default function FileUploadStep({ onFileSelect, error }) {
  const [suppliers, setSuppliers] = useState([]);
  const [selectedSupplier, setSelectedSupplier] = useState('');
  const [newSupplierName, setNewSupplierName] = useState('');
  const [showNewSupplier, setShowNewSupplier] = useState(false);
  const [creatingSupplier, setCreatingSupplier] = useState(false);
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchSuppliers();
  }, []);

  const fetchSuppliers = async () => {
    try {
      const res = await api.get('/suppliers');
      setSuppliers(res.data.suppliers || res.data || []);
    } catch (err) {
      console.error('Error fetching suppliers:', err);
    }
  };

  const createSupplier = async () => {
    if (!newSupplierName.trim()) return;

    setCreatingSupplier(true);
    try {
      const res = await api.post('/suppliers', { name: newSupplierName.trim() });
      const newSupplier = res.data;

      setSuppliers([...suppliers, newSupplier]);
      setSelectedSupplier(newSupplier.id);
      setShowNewSupplier(false);
      setNewSupplierName('');
    } catch (err) {
      console.error('Failed to create supplier:', err);
    } finally {
      setCreatingSupplier(false);
    }
  };

  const handleFileChange = (e) => {
    const selected = e.target.files?.[0];
    if (!selected) return;

    const ext = selected.name.toLowerCase().slice(selected.name.lastIndexOf('.'));
    if (!['.csv', '.xlsx', '.xls'].includes(ext)) {
      alert('Please upload a .csv or .xlsx file');
      return;
    }

    setFile(selected);
  };

  const handleNext = async () => {
    if (!file || !selectedSupplier) {
      return;
    }

    setLoading(true);
    try {
      await onFileSelect(file, selectedSupplier);
    } catch (err) {
      console.error('Error in file select:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        Step 1: Select File and Supplier
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Choose a supplier and upload your price list file (.csv or .xlsx)
      </Typography>

      {/* Supplier Selection */}
      <Box sx={{ mb: 3 }}>
        <FormControl fullWidth sx={{ mb: 2 }}>
          <InputLabel>Supplier *</InputLabel>
          <Select
            value={selectedSupplier}
            label="Supplier *"
            onChange={(e) => setSelectedSupplier(e.target.value)}
            renderValue={(selected) => {
              if (!selected) return <em style={{ color: '#999' }}>Select supplier...</em>;
              const supplier = suppliers.find(s => s.id === selected);
              return supplier?.name || 'Unknown';
            }}
          >
            <MenuItem value="">Select supplier...</MenuItem>
            {suppliers.map(s => (
              <MenuItem key={s.id} value={s.id}>{s.name}</MenuItem>
            ))}
          </Select>
        </FormControl>

        {!showNewSupplier ? (
          <Button
            variant="outlined"
            size="small"
            startIcon={<AddIcon />}
            onClick={() => setShowNewSupplier(true)}
            fullWidth
          >
            Add New Supplier
          </Button>
        ) : (
          <Box sx={{ display: 'flex', gap: 1 }}>
            <TextField
              fullWidth
              size="small"
              label="New supplier name"
              value={newSupplierName}
              onChange={(e) => setNewSupplierName(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && createSupplier()}
              autoFocus
            />
            <Button
              variant="contained"
              size="small"
              onClick={createSupplier}
              disabled={creatingSupplier || !newSupplierName.trim()}
            >
              {creatingSupplier ? <CircularProgress size={16} /> : 'Add'}
            </Button>
            <IconButton
              size="small"
              onClick={() => {
                setShowNewSupplier(false);
                setNewSupplierName('');
              }}
            >
              <CloseIcon fontSize="small" />
            </IconButton>
          </Box>
        )}
      </Box>

      {/* File Upload */}
      <Box sx={{ mb: 3 }}>
        <input
          type="file"
          id="file-upload"
          hidden
          accept=".csv,.xlsx,.xls"
          onChange={handleFileChange}
        />
        <label htmlFor="file-upload">
          <Box
            sx={{
              border: '2px dashed',
              borderColor: file ? 'primary.main' : 'divider',
              borderRadius: 2,
              p: 4,
              textAlign: 'center',
              cursor: 'pointer',
              bgcolor: file ? 'primary.50' : 'background.paper',
              '&:hover': {
                borderColor: 'primary.main',
                bgcolor: 'action.hover'
              }
            }}
          >
            {file ? (
              <Box>
                <Typography variant="body1" fontWeight="600">
                  {file.name}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {(file.size / 1024).toFixed(1)} KB
                </Typography>
                <Typography variant="caption" color="primary" sx={{ display: 'block', mt: 1 }}>
                  Click to change
                </Typography>
              </Box>
            ) : (
              <Box>
                <UploadIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 1 }} />
                <Typography variant="body2" color="text.secondary">
                  Drop CSV or Excel file here
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  .csv, .xlsx, .xls
                </Typography>
              </Box>
            )}
          </Box>
        </label>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
        <Button
          variant="contained"
          onClick={handleNext}
          disabled={!file || !selectedSupplier || loading}
          startIcon={loading ? <CircularProgress size={16} /> : null}
        >
          {loading ? 'Analyzing...' : 'Next: Map Columns'}
        </Button>
      </Box>
    </Box>
  );
}

