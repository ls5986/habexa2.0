import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Grid,
  Chip,
  Divider,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableRow,
  Button,
  CircularProgress,
  Alert
} from '@mui/material';
// Using native Date formatting instead of date-fns
const formatDate = (dateString) => {
  if (!dateString) return '—';
  try {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric', 
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    });
  } catch (e) {
    return '—';
  }
};
import { ExternalLink, Upload, MessageSquare, FileText } from 'lucide-react';
import api from '../../../services/api';
import { habexa } from '../../../theme';

export default function UploadDetailsPanel({ deal }) {
  const [telegramMessage, setTelegramMessage] = useState(null);
  const [loadingMessage, setLoadingMessage] = useState(false);
  const [originalData, setOriginalData] = useState(null);

  // Fetch Telegram message if source is telegram
  useEffect(() => {
    if (deal?.source === 'telegram' && deal?.message_id) {
      setLoadingMessage(true);
      api.get(`/integrations/telegram/messages/${deal.message_id}`)
        .then(res => {
          setTelegramMessage(res.data);
        })
        .catch(err => {
          console.error('Failed to fetch Telegram message:', err);
        })
        .finally(() => {
          setLoadingMessage(false);
        });
    }
  }, [deal?.source, deal?.message_id]);

  // Parse original_upload_data if available
  useEffect(() => {
    if (deal?.original_upload_data) {
      try {
        const data = typeof deal.original_upload_data === 'string' 
          ? JSON.parse(deal.original_upload_data)
          : deal.original_upload_data;
        setOriginalData(data);
      } catch (e) {
        console.error('Failed to parse original_upload_data:', e);
      }
    }
  }, [deal?.original_upload_data]);

  // Map internal column names to readable labels
  const uploadFields = [
    { key: 'asin', label: 'ASIN', value: deal?.asin },
    { key: 'upc', label: 'UPC', value: deal?.upc },
    { key: 'sku', label: 'SKU', value: deal?.sku || deal?.supplier_sku },
    { key: 'title', label: 'Product Name', value: deal?.uploaded_title || deal?.title },
    { key: 'brand', label: 'Brand', value: deal?.uploaded_brand || deal?.brand },
    { key: 'category', label: 'Category', value: deal?.category },
    { key: 'buy_cost', label: 'Buy Cost', value: deal?.buy_cost ? `$${deal.buy_cost.toFixed(4)}` : null },
    { key: 'moq', label: 'MOQ', value: deal?.moq || 1 },
    { key: 'pack_size', label: 'Pack Size', value: deal?.pack_size || deal?.case_pack },
    { key: 'wholesale_cost', label: 'Wholesale Cost (Case)', value: deal?.wholesale_cost ? `$${deal.wholesale_cost.toFixed(2)}` : null },
    { key: 'supplier', label: 'Supplier', value: deal?.supplier?.name || deal?.supplier_id },
  ];

  // Upload metadata
  const getSourceLabel = (source) => {
    const labels = {
      'csv': 'CSV Import',
      'telegram': 'Telegram Channel',
      'manual': 'Manual Entry',
      'quick_analyze': 'Quick Analyze',
      'api': 'API'
    };
    return labels[source] || source || 'Unknown';
  };

  const uploadMetadata = [
    { 
      label: 'Upload Source', 
      value: getSourceLabel(deal?.source)
    },
    { 
      label: 'Upload Date', 
      value: deal?.created_at ? formatDate(deal.created_at) : '—'
    },
    { 
      label: 'Last Updated', 
      value: deal?.updated_at ? formatDate(deal.updated_at) : '—'
    },
    { 
      label: 'Source File', 
      value: deal?.source_filename || deal?.source_detail || '—'
    },
    {
      label: 'Upload Job',
      value: deal?.job_id ? (
        <Chip 
          label={`Job #${deal.job_id.slice(0, 8)}`} 
          size="small"
          onClick={() => window.open(`/jobs/${deal.job_id}`, '_blank')}
          sx={{ cursor: 'pointer' }}
        />
      ) : '—'
    }
  ];

  return (
    <Box>
      {/* Upload Data Section */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
          <Upload size={20} color={habexa.purple.main} />
          <Typography variant="h6">
            Uploaded Product Data
          </Typography>
        </Box>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Data as it was provided in the upload
        </Typography>
        
        <TableContainer>
          <Table size="small">
            <TableBody>
              {uploadFields.map((field) => (
                <TableRow key={field.key}>
                  <TableCell sx={{ fontWeight: 600, width: '30%' }}>
                    {field.label}
                  </TableCell>
                  <TableCell>
                    {field.value || (
                      <Typography variant="body2" color="text.disabled">
                        Not provided
                      </Typography>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      {/* Upload Metadata Section */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
          <FileText size={20} color={habexa.purple.main} />
          <Typography variant="h6">
            Upload Information
          </Typography>
        </Box>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          When and how this product was added
        </Typography>
        <Grid container spacing={2}>
          {uploadMetadata.map((item, idx) => (
            <Grid item xs={12} sm={6} key={idx}>
              <Box>
                <Typography variant="caption" color="text.secondary">
                  {item.label}
                </Typography>
                <Typography variant="body1">
                  {item.value}
                </Typography>
              </Box>
            </Grid>
          ))}
        </Grid>
      </Paper>

      {/* Telegram Message Section */}
      {deal?.source === 'telegram' && (
        <Paper sx={{ p: 3, mb: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
            <MessageSquare size={20} color={habexa.purple.main} />
            <Typography variant="h6">
              Telegram Message
            </Typography>
          </Box>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Original message from Telegram channel
          </Typography>
          
          {loadingMessage ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
              <CircularProgress size={24} />
            </Box>
          ) : telegramMessage ? (
            <Box>
              {telegramMessage.channel_name && (
                <Box sx={{ mb: 2 }}>
                  <Typography variant="caption" color="text.secondary">
                    Channel
                  </Typography>
                  <Typography variant="body1" fontWeight={600}>
                    {telegramMessage.channel_name}
                    {telegramMessage.channel_username && (
                      <Typography component="span" variant="body2" color="text.secondary" sx={{ ml: 1 }}>
                        (@{telegramMessage.channel_username})
                      </Typography>
                    )}
                  </Typography>
                </Box>
              )}
              
              {telegramMessage.telegram_date && (
                <Box sx={{ mb: 2 }}>
                  <Typography variant="caption" color="text.secondary">
                    Message Date
                  </Typography>
                  <Typography variant="body1">
                    {formatDate(telegramMessage.telegram_date)}
                  </Typography>
                </Box>
              )}
              
              <Box 
                sx={{ 
                  p: 2, 
                  bgcolor: 'grey.100',
                  borderRadius: 1,
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                  fontFamily: 'monospace',
                  fontSize: '0.875rem',
                  maxHeight: 400,
                  overflow: 'auto'
                }}
              >
                {telegramMessage.content || 'No message content available'}
              </Box>
              
              {telegramMessage.telegram_message_id && (
                <Button
                  size="small"
                  startIcon={<ExternalLink size={14} />}
                  sx={{ mt: 2 }}
                  onClick={() => {
                    // Link to Telegram message (if we have channel username)
                    if (telegramMessage.channel_username) {
                      window.open(`https://t.me/${telegramMessage.channel_username}/${telegramMessage.telegram_message_id}`, '_blank');
                    }
                  }}
                >
                  View on Telegram
                </Button>
              )}
            </Box>
          ) : (
            <Alert severity="info">
              Message not found or not available
            </Alert>
          )}
        </Paper>
      )}

      {/* Original CSV Data (if available) */}
      {originalData && (
        <Paper sx={{ p: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
            <FileText size={20} color={habexa.purple.main} />
            <Typography variant="h6">
              Raw Upload Data
            </Typography>
          </Box>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Exact data from the CSV file
          </Typography>
          
          <Box 
            component="pre" 
            sx={{ 
              p: 2, 
              bgcolor: 'grey.100',
              borderRadius: 1,
              overflow: 'auto',
              fontSize: '0.875rem',
              maxHeight: 400
            }}
          >
            {JSON.stringify(originalData, null, 2)}
          </Box>
        </Paper>
      )}

      {/* Source Detail (if available and not already shown) */}
      {deal?.source_detail && deal?.source !== 'telegram' && !originalData && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            Source Details
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Additional information about the upload source
          </Typography>
          <Box 
            sx={{ 
              p: 2, 
              bgcolor: 'grey.100',
              borderRadius: 1,
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word'
            }}
          >
            {deal.source_detail}
          </Box>
        </Paper>
      )}
    </Box>
  );
}

