import React, { useState, useEffect, useRef } from 'react';
import { TextField, InputAdornment, IconButton, Box, Typography } from '@mui/material';
import CheckIcon from '@mui/icons-material/Check';
import CloseIcon from '@mui/icons-material/Close';
import EditIcon from '@mui/icons-material/Edit';

export default function InlineEditCell({
  value,
  type = 'text',
  onSave,
  onCancel,
  editable = true,
  formatValue,
  displayValue,
  min,
  max,
  step,
  prefix,
  suffix,
  ...props
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState(value);
  const [error, setError] = useState(null);
  const inputRef = useRef(null);

  useEffect(() => {
    setEditValue(value);
  }, [value]);

  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [isEditing]);

  const handleStartEdit = () => {
    if (!editable) return;
    setIsEditing(true);
    setEditValue(value);
    setError(null);
  };

  const handleCancel = () => {
    setIsEditing(false);
    setEditValue(value);
    setError(null);
    if (onCancel) onCancel();
  };

  const handleSave = () => {
    // Validate
    let finalValue = editValue;

    if (type === 'number') {
      const numValue = parseFloat(editValue);
      if (isNaN(numValue)) {
        setError('Invalid number');
        return;
      }
      if (min !== undefined && numValue < min) {
        setError(`Must be at least ${min}`);
        return;
      }
      if (max !== undefined && numValue > max) {
        setError(`Must be at most ${max}`);
        return;
      }
      finalValue = numValue;
    }

    if (type === 'integer') {
      const intValue = parseInt(editValue);
      if (isNaN(intValue)) {
        setError('Invalid integer');
        return;
      }
      if (min !== undefined && intValue < min) {
        setError(`Must be at least ${min}`);
        return;
      }
      if (max !== undefined && intValue > max) {
        setError(`Must be at most ${max}`);
        return;
      }
      finalValue = intValue;
    }

    setError(null);
    setIsEditing(false);
    if (onSave) {
      onSave(finalValue);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSave();
    } else if (e.key === 'Escape') {
      e.preventDefault();
      handleCancel();
    }
  };

  const handleBlur = () => {
    // Don't auto-save on blur, require explicit save
    // handleSave();
  };

  if (!isEditing) {
    return (
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 0.5,
          cursor: editable ? 'pointer' : 'default',
          '&:hover': editable ? {
            bgcolor: 'action.hover',
            borderRadius: 1
          } : {},
          px: 0.5,
          py: 0.25
        }}
        onClick={handleStartEdit}
        {...props}
      >
        <Typography variant="body2" sx={{ flex: 1 }}>
          {displayValue !== undefined ? displayValue(value) : formatValue ? formatValue(value) : value ?? '—'}
        </Typography>
        {editable && (
          <EditIcon sx={{ fontSize: 14, opacity: 0.5 }} />
        )}
      </Box>
    );
  }

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
      <TextField
        inputRef={inputRef}
        value={editValue}
        onChange={(e) => setEditValue(e.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={handleBlur}
        error={!!error}
        helperText={error}
        size="small"
        type={type === 'number' || type === 'integer' ? 'number' : 'text'}
        inputProps={{
          min,
          max,
          step: step || (type === 'number' ? 0.01 : 1)
        }}
        InputProps={{
          startAdornment: prefix ? (
            <InputAdornment position="start">{prefix}</InputAdornment>
          ) : null,
          endAdornment: suffix ? (
            <InputAdornment position="end">{suffix}</InputAdornment>
          ) : null
        }}
        sx={{ flex: 1 }}
        autoFocus
      />
      <IconButton
        size="small"
        onClick={handleSave}
        color="primary"
        sx={{ p: 0.5 }}
      >
        <CheckIcon fontSize="small" />
      </IconButton>
      <IconButton
        size="small"
        onClick={handleCancel}
        sx={{ p: 0.5 }}
      >
        <CloseIcon fontSize="small" />
      </IconButton>
    </Box>
  );
}

