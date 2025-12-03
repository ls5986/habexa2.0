import React from 'react';
import {
  Box, Typography, Card, CardContent, Grid, LinearProgress, Chip
} from '@mui/material';
import { FileText, CheckCircle, AlertTriangle, Star } from 'lucide-react';

export default function ListingScore({ analysis, keepaData }) {
  // Calculate listing quality score
  const calculateScore = () => {
    if (!analysis) return 0;
    
    let score = 0;
    let maxScore = 0;

    // Image quality (20 points)
    maxScore += 20;
    if (analysis.image_url) score += 20;

    // Title quality (20 points)
    maxScore += 20;
    if (analysis.product_title) {
      const titleLength = analysis.product_title.length;
      if (titleLength >= 50 && titleLength <= 200) score += 20;
      else if (titleLength > 0) score += 10;
    }

    // Reviews (20 points)
    maxScore += 20;
    if (analysis.review_count) {
      if (analysis.review_count >= 100) score += 20;
      else if (analysis.review_count >= 50) score += 15;
      else if (analysis.review_count >= 10) score += 10;
      else score += 5;
    }

    // Rating (20 points)
    maxScore += 20;
    if (analysis.rating) {
      if (analysis.rating >= 4.5) score += 20;
      else if (analysis.rating >= 4.0) score += 15;
      else if (analysis.rating >= 3.5) score += 10;
      else score += 5;
    }

    // Sales Rank (20 points)
    maxScore += 20;
    if (analysis.sales_rank) {
      if (analysis.sales_rank < 10000) score += 20;
      else if (analysis.sales_rank < 50000) score += 15;
      else if (analysis.sales_rank < 100000) score += 10;
      else score += 5;
    }

    return Math.round((score / maxScore) * 100);
  };

  const score = calculateScore();
  const getScoreColor = () => {
    if (score >= 80) return '#10B981';
    if (score >= 60) return '#F59E0B';
    return '#EF4444';
  };

  const getScoreLabel = () => {
    if (score >= 80) return 'Excellent';
    if (score >= 60) return 'Good';
    if (score >= 40) return 'Fair';
    return 'Poor';
  };

  if (!analysis) {
    return (
      <Card>
        <CardContent>
          <Box sx={{ textAlign: 'center', py: 6 }}>
            <FileText size={48} color="#8B8B9B" style={{ marginBottom: 16 }} />
            <Typography variant="h6" gutterBottom>No Analysis Data</Typography>
            <Typography color="text.secondary">
              Analyze the product to see listing quality score.
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
          <FileText size={20} />
          <Typography variant="h6" fontWeight="600">Listing Quality Score</Typography>
        </Box>

        {/* Overall Score */}
        <Box sx={{ textAlign: 'center', mb: 4 }}>
          <Typography variant="h2" fontWeight="700" color={getScoreColor()}>
            {score}
          </Typography>
          <Typography variant="h6" color={getScoreColor()}>
            {getScoreLabel()}
          </Typography>
          <LinearProgress 
            variant="determinate" 
            value={score} 
            sx={{ 
              mt: 2, 
              height: 12, 
              borderRadius: 6,
              bgcolor: '#252540',
              '& .MuiLinearProgress-bar': { bgcolor: getScoreColor() }
            }}
          />
        </Box>

        {/* Breakdown */}
        <Typography variant="subtitle2" color="text.secondary" gutterBottom>
          SCORE BREAKDOWN
        </Typography>
        <Grid container spacing={2} sx={{ mt: 1 }}>
          <Grid item xs={6} sm={4}>
            <Box>
              <Typography variant="caption" color="text.secondary">Image</Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.5 }}>
                {analysis.image_url ? (
                  <>
                    <CheckCircle size={16} color="#10B981" />
                    <Typography variant="body2">Present</Typography>
                  </>
                ) : (
                  <>
                    <AlertTriangle size={16} color="#EF4444" />
                    <Typography variant="body2">Missing</Typography>
                  </>
                )}
              </Box>
            </Box>
          </Grid>
          <Grid item xs={6} sm={4}>
            <Box>
              <Typography variant="caption" color="text.secondary">Title</Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.5 }}>
                {analysis.product_title ? (
                  <>
                    <CheckCircle size={16} color="#10B981" />
                    <Typography variant="body2">Good</Typography>
                  </>
                ) : (
                  <>
                    <AlertTriangle size={16} color="#EF4444" />
                    <Typography variant="body2">Missing</Typography>
                  </>
                )}
              </Box>
            </Box>
          </Grid>
          <Grid item xs={6} sm={4}>
            <Box>
              <Typography variant="caption" color="text.secondary">Reviews</Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.5 }}>
                <Star size={16} color="#F59E0B" />
                <Typography variant="body2">
                  {analysis.review_count?.toLocaleString() || 0}
                </Typography>
              </Box>
            </Box>
          </Grid>
          <Grid item xs={6} sm={4}>
            <Box>
              <Typography variant="caption" color="text.secondary">Rating</Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.5 }}>
                <Star size={16} color="#F59E0B" />
                <Typography variant="body2">
                  {analysis.rating?.toFixed(1) || '—'} ⭐
                </Typography>
              </Box>
            </Box>
          </Grid>
          <Grid item xs={6} sm={4}>
            <Box>
              <Typography variant="caption" color="text.secondary">Sales Rank</Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.5 }}>
                {analysis.sales_rank ? (
                  <Typography variant="body2">
                    #{analysis.sales_rank.toLocaleString()}
                  </Typography>
                ) : (
                  <Typography variant="body2" color="text.secondary">—</Typography>
                )}
              </Box>
            </Box>
          </Grid>
          <Grid item xs={6} sm={4}>
            <Box>
              <Typography variant="caption" color="text.secondary">Brand</Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.5 }}>
                {analysis.brand ? (
                  <>
                    <CheckCircle size={16} color="#10B981" />
                    <Typography variant="body2">{analysis.brand}</Typography>
                  </>
                ) : (
                  <>
                    <AlertTriangle size={16} color="#EF4444" />
                    <Typography variant="body2">Unknown</Typography>
                  </>
                )}
              </Box>
            </Box>
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );
}

