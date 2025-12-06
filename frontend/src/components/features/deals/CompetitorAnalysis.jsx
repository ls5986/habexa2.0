import React, { useState, useEffect } from 'react';
import {
  Box, Typography, Card, CardContent, Grid, Chip, Table,
  TableBody, TableCell, TableHead, TableRow, CircularProgress
} from '@mui/material';
import { Users, TrendingUp, Shield, AlertTriangle } from 'lucide-react';
import api from '../../../services/api';
import { habexa } from '../../../theme';

export default function CompetitorAnalysis({ asin, deal, analysis }) {
  // Use data from database (deal/analysis) instead of spOffers
  const sellerCount = deal?.seller_count || analysis?.total_seller_count || 0;
  const fbaCount = deal?.fba_seller_count || analysis?.fba_seller_count || 0;
  const fbmCount = analysis?.fbm_seller_count || 0;
  const hasCompetitorData = sellerCount > 0 || fbaCount > 0 || fbmCount > 0;

  if (!hasCompetitorData) {
    return (
      <Card sx={{ bgcolor: '#ffffff' }}>
        <CardContent>
          <Box sx={{ textAlign: 'center', py: 6 }}>
            <Users size={48} color="#666666" style={{ marginBottom: 16 }} />
            <Typography variant="h6" gutterBottom>No Competitor Data</Typography>
            <Typography color="text.secondary">
              No competitor data available. Re-analyze the product to get fresh seller information.
            </Typography>
          </Box>
        </CardContent>
      </Card>
    );
  }

  const buyBoxPrice = deal?.sell_price || analysis?.sell_price;
  const salesRank = deal?.bsr || analysis?.bsr;
  const amazonSells = deal?.amazon_was_seller || analysis?.amazon_was_seller;

  return (
    <Card sx={{ bgcolor: '#ffffff' }}>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
          <Users size={20} />
          <Typography variant="h6" fontWeight="600">Competitor Analysis</Typography>
        </Box>

        {/* Summary */}
        <Grid container spacing={2} sx={{ mb: 3 }}>
          <Grid item xs={6} sm={3}>
            <Box sx={{ 
              textAlign: 'center', 
              p: 2, 
              bgcolor: '#ffffff',
              border: '2px solid #7c3aed',
              borderRadius: 1
            }}>
              <Typography variant="caption" sx={{ color: '#666666', fontSize: '0.75rem' }}>Total Sellers</Typography>
              <Typography variant="h5" fontWeight="700" color="#1a1a2e" sx={{ fontSize: '1.25rem' }}>
                {sellerCount || '—'}
              </Typography>
            </Box>
          </Grid>
          <Grid item xs={6} sm={3}>
            <Box sx={{ 
              textAlign: 'center', 
              p: 2, 
              bgcolor: '#ffffff',
              border: '2px solid #7c3aed',
              borderRadius: 1
            }}>
              <Typography variant="caption" sx={{ color: '#666666', fontSize: '0.75rem' }}>FBA Sellers</Typography>
              <Typography variant="h5" fontWeight="700" color="#1a1a2e" sx={{ fontSize: '1.25rem' }}>
                {fbaCount || '—'}
              </Typography>
            </Box>
          </Grid>
          <Grid item xs={6} sm={3}>
            <Box sx={{ 
              textAlign: 'center', 
              p: 2, 
              bgcolor: '#ffffff',
              border: '2px solid #7c3aed',
              borderRadius: 1
            }}>
              <Typography variant="caption" sx={{ color: '#666666', fontSize: '0.75rem' }}>FBM Sellers</Typography>
              <Typography variant="h5" fontWeight="700" color="#1a1a2e" sx={{ fontSize: '1.25rem' }}>
                {fbmCount || '—'}
              </Typography>
            </Box>
          </Grid>
          {buyBoxPrice && (
            <Grid item xs={6} sm={3}>
              <Box sx={{ 
                textAlign: 'center', 
                p: 2, 
                bgcolor: '#ffffff',
                border: '2px solid #7c3aed',
                borderRadius: 1
              }}>
                <Typography variant="caption" sx={{ color: '#666666', fontSize: '0.75rem' }}>Current Price</Typography>
                <Typography variant="h5" fontWeight="700" color="#1a1a2e" sx={{ fontSize: '1.25rem' }}>
                  ${buyBoxPrice.toFixed(2)}
                </Typography>
              </Box>
            </Grid>
          )}
        </Grid>

        {amazonSells && (
          <Box sx={{ p: 2, bgcolor: 'warning.50', borderRadius: 1, mb: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <AlertTriangle size={16} color={habexa.warning.main} />
              <Typography variant="body2" color="warning.main">
                Amazon is currently selling this product
              </Typography>
            </Box>
          </Box>
        )}

        {salesRank && (
          <Box sx={{ mb: 2 }}>
            <Typography variant="body2" color="text.secondary">
              Sales Rank: #{salesRank.toLocaleString()}
            </Typography>
          </Box>
        )}

        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Data from last analysis. Click "Re-analyze" to refresh competitor data.
        </Typography>
      </CardContent>
    </Card>
  );
}

