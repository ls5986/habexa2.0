import React, { useState, useEffect } from 'react';
import {
  Dialog, DialogTitle, DialogContent, DialogActions, Button,
  Stepper, Step, StepLabel, Box, IconButton, Alert
} from '@mui/material';
import { Close as CloseIcon } from '@mui/icons-material';
import FileUploadStep from './FileUploadStep';
import ColumnMappingStep from './ColumnMappingStep';
import ReviewStep from './ReviewStep';
import api from '../../../services/api';

const steps = ['Select File', 'Map Columns', 'Review & Start'];

export default function UploadWizard({ open, onClose, onComplete }) {
  const [activeStep, setActiveStep] = useState(0);
  const [jobId, setJobId] = useState(null);
  const [supplierId, setSupplierId] = useState('');
  const [file, setFile] = useState(null);
  const [fileInfo, setFileInfo] = useState(null); // From analyze endpoint
  const [columnMapping, setColumnMapping] = useState({});
  const [error, setError] = useState(null);

  // Reset on open
  useEffect(() => {
    if (open) {
      reset();
    }
  }, [open]);

  const reset = () => {
    setActiveStep(0);
    setJobId(null);
    setSupplierId('');
    setFile(null);
    setFileInfo(null);
    setColumnMapping({});
    setError(null);
  };

  // Step 1: Prepare upload
  const handleFileSelect = async (selectedFile, selectedSupplierId) => {
    setFile(selectedFile);
    setSupplierId(selectedSupplierId);
    setError(null);

    try {
      // Step 1: Prepare
      const prepareRes = await api.post('/upload/prepare', null, {
        params: {
          supplier_id: selectedSupplierId,
          filename: selectedFile.name
        }
      });

      const newJobId = prepareRes.data.job_id;
      setJobId(newJobId);

      // Step 2: Analyze (upload file)
      const formData = new FormData();
      formData.append('file', selectedFile);

      const analyzeRes = await api.post(`/upload/${newJobId}/analyze`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      setFileInfo(analyzeRes.data);
      setColumnMapping(analyzeRes.data.auto_mapping || {});
      setActiveStep(1); // Move to mapping step
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to analyze file');
    }
  };

  // Step 2: Update mapping
  const handleMappingChange = (mapping) => {
    setColumnMapping(mapping);
  };

  // Step 3: Start processing
  const handleStart = async (saveMapping, mappingName) => {
    setError(null);

    try {
      const formData = new FormData();
      formData.append('column_mapping', JSON.stringify(columnMapping));
      formData.append('save_mapping', saveMapping);
      if (mappingName) {
        formData.append('mapping_name', mappingName);
      }

      await api.post(`/upload/${jobId}/start`, formData);

      // Close wizard and notify parent
      if (onComplete) {
        onComplete({ jobId, status: 'processing' });
      }
      onClose();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to start processing');
    }
  };

  const handleBack = () => {
    if (activeStep > 0) {
      setActiveStep(activeStep - 1);
    }
  };

  const handleClose = () => {
    if (activeStep < 2 || !jobId) {
      // Can close freely if not started processing
      reset();
      onClose();
    } else {
      // Already started - just close
      onClose();
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth>
      <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        Upload Price List
        <IconButton onClick={handleClose} size="small">
          <CloseIcon />
        </IconButton>
      </DialogTitle>

      <DialogContent>
        <Stepper activeStep={activeStep} sx={{ mb: 4, mt: 2 }}>
          {steps.map((label) => (
            <Step key={label}>
              <StepLabel>{label}</StepLabel>
            </Step>
          ))}
        </Stepper>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        <Box sx={{ minHeight: 400 }}>
          {activeStep === 0 && (
            <FileUploadStep
              onFileSelect={handleFileSelect}
              error={error}
            />
          )}

          {activeStep === 1 && fileInfo && (
            <ColumnMappingStep
              fileInfo={fileInfo}
              columnMapping={columnMapping}
              onMappingChange={handleMappingChange}
              onBack={handleBack}
              onNext={() => setActiveStep(2)}
            />
          )}

          {activeStep === 2 && fileInfo && (
            <ReviewStep
              fileInfo={fileInfo}
              columnMapping={columnMapping}
              supplierId={supplierId}
              onStart={handleStart}
              onBack={handleBack}
            />
          )}
        </Box>
      </DialogContent>

      <DialogActions>
        <Button onClick={handleClose}>Cancel</Button>
        {activeStep > 0 && activeStep < 2 && (
          <Button onClick={handleBack}>Back</Button>
        )}
      </DialogActions>
    </Dialog>
  );
}

