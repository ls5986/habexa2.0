import React, { useState } from 'react';
import { 
  Box, 
  Button, 
  Typography, 
  Paper, 
  CircularProgress,
  Card,
  CardContent,
  Grid,
  Chip,
  Alert,
  Accordion,
  AccordionSummary,
  AccordionDetails
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import api from '../services/api';

export default function DebugPage() {
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const runTests = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get('/debug/test-all');
      setResults(response.data);
    } catch (err) {
      setError(err.response?.data || err.message);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status) => {
    if (typeof status === 'string') {
      if (status.includes('OK') || status.includes('CONNECTED') || status.includes('EXISTS') || status === 'SET') {
        return 'success';
      }
      if (status.includes('MISSING') || status.includes('ERROR') || status.includes('FAILED')) {
        return 'error';
      }
      if (status.includes('NOT INSTALLED')) {
        return 'warning';
      }
    }
    return 'default';
  };

  const renderSection = (title, data) => {
    if (!data) return null;
    
    return (
      <Accordion>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography variant="h6">{title}</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Box component="pre" sx={{ 
            fontSize: 12, 
            overflow: 'auto', 
            bgcolor: '#1e1e1e',
            color: '#d4d4d4',
            p: 2,
            borderRadius: 1,
            maxHeight: 400
          }}>
            {JSON.stringify(data, null, 2)}
          </Box>
        </AccordionDetails>
      </Accordion>
    );
  };

  return (
    <Box p={4} sx={{ bgcolor: '#0F0F1A', minHeight: '100vh' }}>
      <Typography variant="h4" gutterBottom sx={{ color: '#fff', mb: 3 }}>
        Integration Debug Tests
      </Typography>
      
      <Button 
        variant="contained" 
        onClick={runTests}
        disabled={loading}
        sx={{ 
          mb: 3,
          bgcolor: '#7C3AED',
          '&:hover': { bgcolor: '#6D28D9' }
        }}
      >
        {loading ? <CircularProgress size={24} sx={{ color: '#fff' }} /> : 'Run All Tests'}
      </Button>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          <Typography>Error: {JSON.stringify(error, null, 2)}</Typography>
        </Alert>
      )}

      {results && (
        <Box>
          <Card sx={{ mb: 2, bgcolor: '#1A1A2E' }}>
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ color: '#fff' }}>
                User ID
              </Typography>
              <Typography sx={{ color: '#aaa' }}>{results.user}</Typography>
            </CardContent>
          </Card>

          {renderSection('Environment Variables', results.env_vars)}
          {renderSection('Database', results.database)}
          {renderSection('Stripe', results.stripe)}
          {renderSection('Amazon SP-API', results.amazon)}
          {renderSection('Telegram', results.telegram)}
          {renderSection('Keepa', results.keepa)}
          {renderSection('OpenAI', results.openai)}

          <Card sx={{ mt: 3, bgcolor: '#1A1A2E' }}>
            <CardContent>
              <Typography variant="h6" gutterBottom sx={{ color: '#fff' }}>
                Full Results (JSON)
              </Typography>
              <Box component="pre" sx={{ 
                fontSize: 11, 
                overflow: 'auto', 
                bgcolor: '#0F0F1A',
                color: '#d4d4d4',
                p: 2,
                borderRadius: 1,
                maxHeight: 500
              }}>
                {JSON.stringify(results, null, 2)}
              </Box>
            </CardContent>
          </Card>
        </Box>
      )}
    </Box>
  );
}

