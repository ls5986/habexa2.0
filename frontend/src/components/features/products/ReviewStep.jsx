import React, { useState } from 'react';
import {
  Box, Typography, Button, TextField, Checkbox, FormControlLabel,
  Alert, Table, TableBody, TableCell, TableHead, TableRow, Chip
} from '@mui/material';

export default function ReviewStep({ fileInfo, columnMapping, supplierId, onStart, onBack }) {
  const [saveMapping, setSaveMapping] = useState(false);
  const [mappingName, setMappingName] = useState('');
  const [starting, setStarting] = useState(false);

  const handleStart = async () => {
    setStarting(true);
    try {
      await onStart(saveMapping, mappingName);
    } catch (err) {
      console.error('Error starting upload:', err);
    } finally {
      setStarting(false);
    }
  };

  // Count mapped fields
  const mappedCount = Object.keys(columnMapping).length;
  const requiredFields = ['upc', 'buy_cost'];
  const requiredMapped = requiredFields.every(f => columnMapping[f]);

  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        Step 3: Review & Start
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Review your settings and start processing
      </Typography>

      {/* Summary */}
      <Alert severity="info" sx={{ mb: 3 }}>
        <Typography variant="subtitle2" gutterBottom>
          Upload Summary
        </Typography>
        <Typography variant="body2">
          <strong>File:</strong> {fileInfo.filename}
        </Typography>
        <Typography variant="body2">
          <strong>Total Rows:</strong> {fileInfo.total_rows?.toLocaleString() || 0}
        </Typography>
        <Typography variant="body2">
          <strong>Columns Mapped:</strong> {mappedCount} of {fileInfo.columns?.length || 0}
        </Typography>
        <Typography variant="body2">
          <strong>Estimated Time:</strong> ~{Math.ceil((fileInfo.total_rows || 0) / 500) * 10} seconds
        </Typography>
      </Alert>

      {/* Mapping Preview */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="subtitle2" gutterBottom>
          Column Mapping
        </Typography>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Field</TableCell>
              <TableCell>Your Column</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {Object.entries(columnMapping).map(([field, column]) => (
              <TableRow key={field}>
                <TableCell>
                  <Chip label={field} size="small" color={['upc', 'buy_cost'].includes(field) ? 'primary' : 'default'} />
                </TableCell>
                <TableCell>{column}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>

      {/* Save Mapping */}
      <Box sx={{ mb: 3 }}>
        <FormControlLabel
          control={
            <Checkbox
              checked={saveMapping}
              onChange={(e) => setSaveMapping(e.target.checked)}
            />
          }
          label="Save this mapping for future uploads"
        />
        {saveMapping && (
          <TextField
            fullWidth
            size="small"
            label="Mapping Name"
            value={mappingName}
            onChange={(e) => setMappingName(e.target.value)}
            placeholder="e.g., KEHE Default"
            sx={{ mt: 1 }}
          />
        )}
      </Box>

      {!requiredMapped && (
        <Alert severity="error" sx={{ mb: 2 }}>
          Required fields (UPC, Buy Cost) must be mapped before starting
        </Alert>
      )}

      {/* Navigation */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 3 }}>
        <Button onClick={onBack} disabled={starting}>Back</Button>
        <Button
          variant="contained"
          onClick={handleStart}
          disabled={!requiredMapped || starting}
        >
          {starting ? 'Starting...' : 'Start Processing'}
        </Button>
      </Box>
    </Box>
  );
}

