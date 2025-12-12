import React, { useState, useEffect } from 'react';
import { Paper, Typography, Box, Button, List, ListItem, ListItemText, ListItemSecondaryAction, IconButton, Alert } from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import DownloadIcon from '@mui/icons-material/Download';
import { useNavigate } from 'react-router-dom';
import api from '../../services/api';

export default function SupplierTemplatesTab({ supplierId }) {
  const navigate = useNavigate();
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { fetchTemplates(); }, [supplierId]);

  const fetchTemplates = async () => {
    try {
      const response = await api.get(`/templates/supplier/${supplierId}`);
      setTemplates(response.data?.templates || response.data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (templateId) => {
    if (!window.confirm('Delete this template?')) return;

    try {
      await api.delete(`/templates/${templateId}`);
      fetchTemplates();
    } catch (err) {
      alert('Failed to delete template');
    }
  };

  return (
    <Paper sx={{ p: 2 }}>
      <Box display="flex" justifyContent="space-between" mb={2}>
        <Typography variant="h6" fontWeight="bold">Upload Templates</Typography>
        <Button 
          variant="contained" 
          startIcon={<AddIcon />} 
          onClick={() => navigate(`/templates/new?supplier=${supplierId}`)}
        >
          Create Template
        </Button>
      </Box>

      <Alert severity="info" sx={{ mb: 2 }}>
        Templates map supplier CSV columns to Habexa fields for faster uploads.
        Create a template to automatically map columns when uploading files from this supplier.
      </Alert>

      {loading ? (
        <Typography>Loading...</Typography>
      ) : templates.length === 0 ? (
        <Box textAlign="center" py={4}>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            No templates yet
          </Typography>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            Create a template to speed up uploads from this supplier
          </Typography>
          <Button 
            variant="outlined" 
            startIcon={<AddIcon />} 
            onClick={() => navigate(`/templates/new?supplier=${supplierId}`)} 
            sx={{ mt: 2 }}
          >
            Create First Template
          </Button>
        </Box>
      ) : (
        <List>
          {templates.map(t => (
            <ListItem key={t.id} divider>
              <ListItemText
                primary={t.template_name || t.name}
                secondary={
                  `${Object.keys(t.column_mappings || {}).length} field mappings${
                    t.last_used_at ? ` • Last used ${new Date(t.last_used_at).toLocaleDateString()}` : ''
                  }`
                }
              />
              <ListItemSecondaryAction>
                <IconButton 
                  edge="end" 
                  onClick={() => {
                    // Download template as CSV
                    const csv = convertTemplateToCSV(t);
                    const blob = new Blob([csv], { type: 'text/csv' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `${t.template_name || 'template'}.csv`;
                    a.click();
                    URL.revokeObjectURL(url);
                  }}
                >
                  <DownloadIcon />
                </IconButton>
                <IconButton 
                  edge="end" 
                  onClick={() => navigate(`/templates/${t.id}/edit`)}
                >
                  <EditIcon />
                </IconButton>
                <IconButton 
                  edge="end" 
                  onClick={() => handleDelete(t.id)} 
                  color="error"
                >
                  <DeleteIcon />
                </IconButton>
              </ListItemSecondaryAction>
            </ListItem>
          ))}
        </List>
      )}
    </Paper>
  );
}

// Helper function to convert template to CSV
function convertTemplateToCSV(template) {
  const mappings = template.column_mappings || {};
  const headers = ['Supplier Column', 'Habexa Field'];
  const rows = Object.entries(mappings).map(([supplierCol, habexaField]) => 
    `"${supplierCol}","${habexaField}"`
  );
  return [headers.join(','), ...rows].join('\n');
}

