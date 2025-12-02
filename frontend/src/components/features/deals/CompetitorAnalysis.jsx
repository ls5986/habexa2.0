import React, { useState, useEffect } from 'react';
import {
  Box, Typography, Card, CardContent, Grid, Chip, Table,
  TableBody, TableCell, TableHead, TableRow, CircularProgress
} from '@mui/material';
import { Users, TrendingUp, Shield, AlertTriangle } from 'lucide-react';
import api from '../../../services/api';

export default function CompetitorAnalysis({ asin, spOffers }) {
  const [loading, setLoading] = useState(!spOffers);

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

  if (!spOffers) {
    return (
      <Card>
        <CardContent>
          <Box sx={{ textAlign: 'center', py: 6 }}>
            <Users size={48} color="#666" style={{ marginBottom: 16 }} />
            <Typography variant="h6" gutterBottom>No Competitor Data</Typography>
            <Typography color="text.secondary">
              Competitor analysis requires SP-API access. Connect your Amazon Seller account to see live seller data.
            </Typography>
          </Box>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
          <Users size={20} />
          <Typography variant="h6" fontWeight="600">Competitor Analysis</Typography>
          {spOffers.source === 'sp-api' && (
            <Chip label="Live Data" size="small" color="success" sx={{ ml: 'auto' }} />
          )}
        </Box>

        {/* Summary */}
        <Grid container spacing={2} sx={{ mb: 3 }}>
          <Grid item xs={6} sm={3}>
            <Box sx={{ textAlign: 'center', p: 2, bgcolor: '#1A1A2E', borderRadius: 2 }}>
              <Typography variant="caption" color="text.secondary">Buy Box Price</Typography>
              <Typography variant="h5" fontWeight="700" color="warning.main">
                ${spOffers.buy_box_price?.toFixed(2) || '—'}
              </Typography>
            </Box>
          </Grid>
          <Grid item xs={6} sm={3}>
            <Box sx={{ textAlign: 'center', p: 2, bgcolor: '#1A1A2E', borderRadius: 2 }}>
              <Typography variant="caption" color="text.secondary">Sales Rank</Typography>
              <Typography variant="h5" fontWeight="700">
                #{spOffers.sales_rank?.toLocaleString() || '—'}
              </Typography>
            </Box>
          </Grid>
        </Grid>

        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Data source: {spOffers.source === 'sp-api' ? 'SP-API (Live)' : spOffers.source === 'keepa' ? 'Keepa' : 'Estimated'}
        </Typography>
      </CardContent>
    </Card>
  );
}

