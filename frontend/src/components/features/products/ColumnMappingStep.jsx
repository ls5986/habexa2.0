import React, { useState } from 'react';
import {
  Box, Typography, Button, FormControl, InputLabel, Select, MenuItem,
  Table, TableBody, TableCell, TableHead, TableRow, Chip, Alert
} from '@mui/material';
import { Info as InfoIcon } from '@mui/icons-material';

// Field definitions (should match backend MAPPABLE_FIELDS)
const FIELDS = [
  { key: 'upc', label: 'UPC', required: true, description: 'Universal Product Code (12-14 digits)' },
  { key: 'buy_cost', label: 'Buy Cost', required: true, description: 'Cost per SINGLE UNIT (not per case)' },
  { key: 'promo_buy_cost', label: 'Promo Buy Cost', required: false, description: 'Temporary promotional price' },
  { key: 'pack_size', label: 'Pack Size', required: false, description: 'Units per case/pack' },
  { key: 'moq', label: 'MOQ', required: false, description: 'Minimum order quantity (in cases)' },
  { key: 'title', label: 'Product Title', required: false, description: 'Product name/description' },
  { key: 'brand', label: 'Brand', required: false, description: 'Product brand/manufacturer' },
  { key: 'supplier_sku', label: 'Supplier SKU', required: false, description: "Supplier's internal product code" },
];

export default function ColumnMappingStep({ fileInfo, columnMapping, onMappingChange, onBack, onNext }) {
  const [mapping, setMapping] = useState(columnMapping);
  const [showExplanations, setShowExplanations] = useState(false);
  const [errors, setErrors] = useState([]);

  const handleMapColumn = (fieldKey, columnName) => {
    // Check for duplicates
    const existingField = Object.entries(mapping)
      .find(([k, v]) => v === columnName && k !== fieldKey);

    if (existingField) {
      setErrors([`'${columnName}' is already mapped to ${FIELDS.find(f => f.key === existingField[0])?.label || existingField[0]}`]);
      return;
    }

    const newMapping = { ...mapping, [fieldKey]: columnName };
    setMapping(newMapping);
    setErrors([]);
    onMappingChange(newMapping);
  };

  const getMappedField = (columnName) => {
    return Object.entries(mapping).find(([k, v]) => v === columnName)?.[0] || null;
  };

  const requiredFieldsMapped = FIELDS.filter(f => f.required).every(f => mapping[f.key]);
  const canProceed = requiredFieldsMapped && errors.length === 0;

  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        Step 2: Map Your Columns
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Match your file columns to the required fields. Required fields are marked with *
      </Typography>

      {/* Saved Mappings */}
      {fileInfo.saved_mappings && fileInfo.saved_mappings.length > 0 && (
        <Box sx={{ mb: 3 }}>
          <FormControl fullWidth>
            <InputLabel>Load Saved Mapping</InputLabel>
            <Select
              value=""
              label="Load Saved Mapping"
              onChange={(e) => {
                const saved = fileInfo.saved_mappings.find(m => m.id === e.target.value);
                if (saved) {
                  setMapping(saved.mapping);
                  onMappingChange(saved.mapping);
                }
              }}
            >
              <MenuItem value="">Select a saved mapping...</MenuItem>
              {fileInfo.saved_mappings.map(m => (
                <MenuItem key={m.id} value={m.id}>
                  {m.name} {m.is_default && '(Default)'}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Box>
      )}

      {/* Mapping Table */}
      <Table size="small" sx={{ mb: 2 }}>
        <TableHead>
          <TableRow>
            <TableCell>Your Column</TableCell>
            <TableCell>→</TableCell>
            <TableCell>Map To</TableCell>
            <TableCell>Sample Data</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {fileInfo.columns.map(col => {
            const mappedField = getMappedField(col.name);
            return (
              <TableRow key={col.name}>
                <TableCell>
                  <Typography variant="body2" fontWeight={mappedField ? 600 : 400}>
                    {col.name}
                  </Typography>
                </TableCell>
                <TableCell>→</TableCell>
                <TableCell>
                  <Select
                    value={mappedField || ''}
                    size="small"
                    onChange={(e) => handleMapColumn(e.target.value, col.name)}
                    sx={{ minWidth: 200 }}
                  >
                    <MenuItem value="">Skip Column</MenuItem>
                    {FIELDS.map(f => (
                      <MenuItem key={f.key} value={f.key}>
                        {f.label} {f.required && '*'}
                      </MenuItem>
                    ))}
                  </Select>
                </TableCell>
                <TableCell>
                  <Box sx={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {col.sample_values && col.sample_values.length > 0 ? (
                      <Typography variant="caption" color="text.secondary">
                        {col.sample_values.slice(0, 3).join(', ')}
                        {col.sample_values.length > 3 && '...'}
                      </Typography>
                    ) : (
                      <Typography variant="caption" color="text.secondary">—</Typography>
                    )}
                  </Box>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>

      {/* Required Fields Indicator */}
      {!requiredFieldsMapped && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          Please map all required fields: {FIELDS.filter(f => f.required && !mapping[f.key]).map(f => f.label).join(', ')}
        </Alert>
      )}

      {errors.length > 0 && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {errors[0]}
        </Alert>
      )}

      {/* Field Explanations Button */}
      <Box sx={{ mb: 2 }}>
        <Button
          startIcon={<InfoIcon />}
          onClick={() => setShowExplanations(!showExplanations)}
          size="small"
        >
          {showExplanations ? 'Hide' : 'Show'} Field Explanations
        </Button>
      </Box>

      {showExplanations && (
        <Box sx={{ p: 2, bgcolor: 'background.default', borderRadius: 1, mb: 2 }}>
          {FIELDS.map(field => (
            <Box key={field.key} sx={{ mb: 2 }}>
              <Typography variant="subtitle2" fontWeight={600}>
                {field.label} {field.required && '*'}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {field.description}
              </Typography>
            </Box>
          ))}
        </Box>
      )}

      {/* Navigation */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 3 }}>
        <Button onClick={onBack}>Back</Button>
        <Button
          variant="contained"
          onClick={onNext}
          disabled={!canProceed}
        >
          Next: Review
        </Button>
      </Box>
    </Box>
  );
}

