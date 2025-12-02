import React, { useState, useEffect } from 'react';
import {
  Box, Typography, Card, CardContent, Grid, Chip, CircularProgress
} from '@mui/material';
import { Layers, Package } from 'lucide-react';
import api from '../../../services/api';

export default function VariationAnalysis({ asin, keepaData }) {
  const [loading, setLoading] = useState(true);
  const [variations, setVariations] = useState([]);

  useEffect(() => {
    fetchVariations();
  }, [asin]);

  const fetchVariations = async () => {
    setLoading(true);
    try {
      // TODO: Implement variation analysis endpoint
      // const res = await api.get(`/products/${asin}/variations`);
      // setVariations(res.data);
      
      // Placeholder data
      setTimeout(() => {
        setVariations([]);
        setLoading(false);
      }, 500);
    } catch (err) {
      console.error('Failed to fetch variations:', err);
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Card>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress />
          </Box>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
          <Layers size={20} />
          <Typography variant="h6" fontWeight="600">Product Variations</Typography>
        </Box>

        {variations.length === 0 ? (
          <Box sx={{ textAlign: 'center', py: 6 }}>
            <Layers size={48} color="#666" style={{ marginBottom: 16 }} />
            <Typography variant="h6" gutterBottom>No Variations Found</Typography>
            <Typography color="text.secondary">
              This product doesn't have variations, or variation data is not available.
            </Typography>
          </Box>
        ) : (
          <Grid container spacing={2}>
            {variations.map((variation, i) => (
              <Grid item xs={12} sm={6} md={4} key={i}>
                <Card sx={{ bgcolor: '#1A1A2E' }}>
                  <CardContent>
                    <Typography variant="body2" fontWeight="600" gutterBottom>
                      {variation.title || `Variation ${i + 1}`}
                    </Typography>
                    <Typography variant="caption" color="text.secondary" display="block">
                      ASIN: {variation.asin}
                    </Typography>
                    {variation.price && (
                      <Typography variant="body2" sx={{ mt: 1 }}>
                        ${variation.price.toFixed(2)}
                      </Typography>
                    )}
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        )}
      </CardContent>
    </Card>
  );
}

