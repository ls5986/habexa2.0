import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  Chip,
  Paper
} from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import WarningIcon from '@mui/icons-material/Warning';

export default function ColumnMappingDialog({
  open,
  onClose,
  previewData,
  onConfirm
}) {
  const [columnMapping, setColumnMapping] = useState(
    previewData?.suggested_mapping || {}
  );
  
  // Our expected fields
  const targetFields = [
    { key: 'asin', label: 'ASIN', required: false },
    { key: 'upc', label: 'UPC', required: false },
    { key: 'sku', label: 'SKU', required: false },
    { key: 'title', label: 'Product Name', required: true },
    { key: 'brand', label: 'Brand', required: true },
    { key: 'category', label: 'Category', required: false },
    { key: 'cost', label: 'Buy Cost', required: false, calculated: true }, // Can be calculated from wholesale_cost_case / case_pack
    { key: 'moq', label: 'MOQ', required: false },
    { key: 'case_pack', label: 'Case Pack', required: false },
    { key: 'wholesale_cost_case', label: 'Wholesale Cost (Case)', required: false },
    { key: 'supplier_name', label: 'Supplier', required: false }
  ];
  
  // Check if Buy Cost can be calculated (wholesale_cost_case + case_pack both mapped)
  const canCalculateBuyCost = columnMapping.wholesale_cost_case && columnMapping.case_pack;
  const hasBuyCost = columnMapping.cost;
  
  // Buy Cost is required UNLESS it can be calculated
  const buyCostRequired = !canCalculateBuyCost && !hasBuyCost;
  
  const handleMappingChange = (field, csvColumn) => {
    setColumnMapping({
      ...columnMapping,
      [field]: csvColumn
    });
  };
  
  const handleConfirm = () => {
    onConfirm(columnMapping);
  };
  
  if (!previewData) return null;
  
  const { columns, preview_data, validation } = previewData;
  
  return (
    <Dialog 
      open={open} 
      onClose={onClose}
      maxWidth="lg"
      fullWidth
    >
      <DialogTitle>
        Map Columns
      </DialogTitle>
      
      <DialogContent>
        {/* AI mapping info */}
        <Alert severity="info" sx={{ mb: 2 }}>
          AI detected your columns. Review and adjust the mapping below.
        </Alert>
        
        {/* Validation warnings */}
        {validation?.warnings?.length > 0 && (
          <Alert severity="warning" sx={{ mb: 2 }}>
            {validation.warnings.join('. ')}
          </Alert>
        )}
        
        {/* Column mapping */}
        <Typography variant="h6" gutterBottom>
          Column Mapping
        </Typography>
        
        <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2, mb: 3 }}>
          {targetFields.map((field) => (
            <FormControl key={field.key} size="small">
              <InputLabel>
                {field.label}
                {(field.required || (field.key === 'cost' && buyCostRequired)) && <span style={{ color: 'red' }}> *</span>}
                {field.key === 'cost' && canCalculateBuyCost && (
                  <span style={{ color: 'green', fontSize: '0.75rem', marginLeft: 4 }}>
                    (will be calculated)
                  </span>
                )}
              </InputLabel>
              <Select
                value={columnMapping[field.key] || ''}
                onChange={(e) => handleMappingChange(field.key, e.target.value)}
                label={field.label}
                disabled={field.key === 'cost' && canCalculateBuyCost} // Disable if it will be calculated
              >
                <MenuItem value="">
                  <em>{field.key === 'cost' && canCalculateBuyCost ? 'Auto-calculated' : 'Not mapped'}</em>
                </MenuItem>
                {columns.map((col) => (
                  <MenuItem key={col} value={col}>
                    {col}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          ))}
        </Box>
        
        {/* Preview table */}
        <Typography variant="h6" gutterBottom>
          Preview (First 5 Rows)
        </Typography>
        
        <Paper sx={{ overflow: 'auto', maxHeight: 400 }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                {Object.keys(columnMapping).map((field) => (
                  <TableCell key={field}>
                    <Box>
                      <Typography variant="caption" fontWeight="bold">
                        {field.toUpperCase()}
                      </Typography>
                      <Typography variant="caption" display="block" color="text.secondary">
                        from: {columnMapping[field]}
                      </Typography>
                    </Box>
                  </TableCell>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              {preview_data?.slice(0, 5).map((row, idx) => {
                // Calculate Buy Cost if wholesale_cost_case and case_pack are both mapped
                const calculatedBuyCost = canCalculateBuyCost && columnMapping.wholesale_cost_case && columnMapping.case_pack
                  ? (() => {
                      const wholesale = parseFloat(row[columnMapping.wholesale_cost_case]);
                      const pack = parseFloat(row[columnMapping.case_pack]);
                      if (!isNaN(wholesale) && !isNaN(pack) && pack > 0) {
                        return (wholesale / pack).toFixed(2);
                      }
                      return '—';
                    })()
                  : null;
                
                return (
                  <TableRow key={idx}>
                    {Object.entries(columnMapping).map(([field, csvCol]) => {
                      // Show calculated Buy Cost if applicable
                      if (field === 'cost' && calculatedBuyCost !== null) {
                        return (
                          <TableCell key={field}>
                            <Box>
                              <Typography variant="body2" fontWeight="bold" color="success.main">
                                {calculatedBuyCost}
                              </Typography>
                              <Typography variant="caption" color="text.secondary">
                                (calculated)
                              </Typography>
                            </Box>
                          </TableCell>
                        );
                      }
                      return (
                        <TableCell key={field}>
                          {row[csvCol] || '—'}
                        </TableCell>
                      );
                    })}
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </Paper>
        
        {/* Mapping summary */}
        <Box sx={{ mt: 2, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
          <Typography variant="body2" color="text.secondary">
            Mapped fields:
          </Typography>
          {Object.entries(columnMapping).map(([field, col]) => (
            <Chip 
              key={field}
              label={`${field} ← ${col}`}
              size="small"
              color="primary"
              variant="outlined"
            />
          ))}
        </Box>
      </DialogContent>
      
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button 
          onClick={handleConfirm}
          variant="contained"
          disabled={!validation?.valid && !canCalculateBuyCost}
          title={!validation?.valid && !canCalculateBuyCost ? 'Please map required fields' : ''}
        >
          Import {previewData.total_rows} Products
        </Button>
      </DialogActions>
    </Dialog>
  );
}

