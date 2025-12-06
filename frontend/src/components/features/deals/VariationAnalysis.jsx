import React from 'react';
import {
  Box, Typography, Card, CardContent, Alert, Chip
} from '@mui/material';
import { Layers, Info } from 'lucide-react';
import { habexa } from '../../../theme';

export default function VariationAnalysis({ asin, deal, analysis }) {
  // Use data from database - no API calls needed!
  // Variation info is stored in deal object after analysis
  const hasVariations = deal?.is_variation && deal?.variation_count > 1;
  const variationCount = deal?.variation_count || 0;
  const parentAsin = deal?.parent_asin;

  return (
    <Card sx={{ bgcolor: '#ffffff' }}>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
          <Layers size={20} />
          <Typography variant="h6" fontWeight="600">Product Variations</Typography>
        </Box>

        {hasVariations ? (
          <Box>
            <Alert severity="info" sx={{ mb: 3 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <Info size={16} />
                <Typography variant="body2" fontWeight={600}>
                  This product is part of a {variationCount}-variation family
                </Typography>
              </Box>
              {parentAsin && (
                <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                  Parent ASIN: <code style={{ fontFamily: 'monospace', background: '#f5f5f5', padding: '2px 6px', borderRadius: 2 }}>{parentAsin}</code>
                </Typography>
              )}
            </Alert>

            <Box sx={{ p: 2, bgcolor: 'grey.50', borderRadius: 2 }}>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Variation Information
              </Typography>
              <Box sx={{ display: 'flex', gap: 2, mt: 2 }}>
                <Box>
                  <Typography variant="caption" color="text.secondary">Total Variations</Typography>
                  <Typography variant="h6">{variationCount}</Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary">This ASIN</Typography>
                  <Typography variant="body2" fontFamily="monospace">{asin}</Typography>
                </Box>
              </Box>
            </Box>

            <Alert severity="warning" sx={{ mt: 3 }}>
              <Typography variant="body2">
                Detailed variation breakdown is coming soon. The backend endpoint to fetch individual variation data is being developed.
              </Typography>
              <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                For now, you can see this product is part of a variation family with {variationCount} total variations.
              </Typography>
            </Alert>
          </Box>
        ) : (
          <Box sx={{ textAlign: 'center', py: 6 }}>
            <Layers size={48} color="#666666" style={{ marginBottom: 16 }} />
            <Typography variant="h6" gutterBottom>No Variations</Typography>
            <Typography color="text.secondary">
              This product does not have variations. It's a standalone product.
            </Typography>
          </Box>
        )}
      </CardContent>
    </Card>
  );
}

