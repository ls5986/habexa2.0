import React, { useState } from 'react';
import {
  Paper,
  Box,
  Typography,
  Checkbox,
  FormControlLabel,
  Stack,
  Button,
  IconButton,
  Divider
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import SearchIcon from '@mui/icons-material/Search';
import TextField from '@mui/material/TextField';

export default function AnalyzerColumnMenu({
  columns,
  visibleColumns,
  onVisibleColumnsChange,
  onClose
}) {
  const [searchTerm, setSearchTerm] = useState('');

  const filteredColumns = columns.filter(col =>
    col.label.toLowerCase().includes(searchTerm.toLowerCase()) ||
    col.id.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleToggleColumn = (columnId) => {
    if (visibleColumns.includes(columnId)) {
      onVisibleColumnsChange(visibleColumns.filter(id => id !== columnId));
    } else {
      onVisibleColumnsChange([...visibleColumns, columnId]);
    }
  };

  const handleSelectAll = () => {
    onVisibleColumnsChange(columns.map(col => col.id));
  };

  const handleDeselectAll = () => {
    // Keep essential columns visible
    const essentialColumns = ['image', 'asin', 'title'];
    onVisibleColumnsChange(essentialColumns);
  };

  const handleReset = () => {
    const defaultVisible = columns
      .filter(col => col.defaultVisible)
      .map(col => col.id);
    onVisibleColumnsChange(defaultVisible);
  };

  return (
    <Paper
      sx={{
        p: 3,
        mb: 2,
        position: 'absolute',
        right: 0,
        top: 60,
        zIndex: 1000,
        minWidth: 300,
        maxHeight: 600,
        overflow: 'auto'
      }}
    >
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h6">Column Visibility</Typography>
        <IconButton onClick={onClose} size="small">
          <CloseIcon />
        </IconButton>
      </Box>

      {/* Search */}
      <TextField
        fullWidth
        size="small"
        placeholder="Search columns..."
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
        InputProps={{
          startAdornment: <SearchIcon sx={{ mr: 1, color: 'text.secondary' }} />
        }}
        sx={{ mb: 2 }}
      />

      {/* Quick Actions */}
      <Stack direction="row" spacing={1} mb={2}>
        <Button size="small" onClick={handleSelectAll}>
          Select All
        </Button>
        <Button size="small" onClick={handleDeselectAll}>
          Deselect All
        </Button>
        <Button size="small" onClick={handleReset}>
          Reset
        </Button>
      </Stack>

      <Divider sx={{ mb: 2 }} />

      {/* Column List */}
      <Stack spacing={1}>
        {filteredColumns.map((column) => {
          const isVisible = visibleColumns.includes(column.id);
          const isRequired = ['image', 'asin', 'title'].includes(column.id);

          return (
            <FormControlLabel
              key={column.id}
              control={
                <Checkbox
                  checked={isVisible}
                  onChange={() => handleToggleColumn(column.id)}
                  disabled={isRequired}
                />
              }
              label={
                <Box>
                  <Typography variant="body2">{column.label}</Typography>
                  {isRequired && (
                    <Typography variant="caption" color="text.secondary">
                      (Required)
                    </Typography>
                  )}
                </Box>
              }
            />
          );
        })}
      </Stack>

      {/* Footer */}
      <Box mt={2} pt={2} borderTop="1px solid" borderColor="divider">
        <Typography variant="caption" color="text.secondary">
          {visibleColumns.length} of {columns.length} columns visible
        </Typography>
      </Box>
    </Paper>
  );
}

