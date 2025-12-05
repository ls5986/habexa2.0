import React from 'react';
import {
  Box, Typography, LinearProgress, Stepper, Step, StepLabel, StepContent,
  Card, CardContent, Chip, Grid, Alert, Table, TableBody, TableRow, TableCell
} from '@mui/material';
import {
  CheckCircle, AlertTriangle, Clock, TrendingUp, Package, Search, DollarSign, BarChart2
} from 'lucide-react';
import { habexa } from '../../../theme';

const STAGES = [
  { id: 'parse', label: 'Parse Excel', icon: Package, color: habexa.purple.main },
  { id: 'convert', label: 'UPC → ASIN', icon: Search, color: habexa.info.main },
  { id: 'pricing', label: 'SP-API Pricing', icon: DollarSign, color: habexa.warning.main },
  { id: 'keepa', label: 'Keepa Analysis', icon: BarChart2, color: habexa.success.main },
];

export default function PipelineProgressTracker({ job, parsedData, conversionData, pricingData, keepaData }) {
  const getStageStatus = (stageId) => {
    if (!job) return 'pending';
    
    // Map job status to stages
    if (job.status === 'completed') {
      return 'completed';
    }
    
    if (job.status === 'failed') {
      return 'error';
    }
    
    // Determine current stage from job metadata or progress
    const currentStage = job.metadata?.current_stage || job.stage || 'parse';
    
    if (stageId === 'parse') {
      return currentStage === 'parse' ? 'active' : 'completed';
    }
    if (stageId === 'convert') {
      if (currentStage === 'parse') return 'pending';
      if (currentStage === 'convert') return 'active';
      return 'completed';
    }
    if (stageId === 'pricing') {
      if (['parse', 'convert'].includes(currentStage)) return 'pending';
      if (currentStage === 'pricing' || currentStage === 'analyzing') return 'active';
      return 'completed';
    }
    if (stageId === 'keepa') {
      if (['parse', 'convert', 'pricing', 'analyzing'].includes(currentStage)) return 'pending';
      if (currentStage === 'keepa') return 'active';
      return 'completed';
    }
    
    return 'pending';
  };

  const getStageIcon = (status) => {
    switch (status) {
      case 'completed':
        return <CheckCircle size={20} color={habexa.success.main} />;
      case 'active':
        return <Clock size={20} color={habexa.warning.main} />;
      case 'error':
        return <AlertTriangle size={20} color={habexa.error.main} />;
      default:
        return <Clock size={20} color={habexa.gray[400]} />;
    }
  };

  return (
    <Box sx={{ mt: 2 }}>
      <Stepper orientation="vertical">
        {/* STAGE 0: PARSE */}
        <Step active={getStageStatus('parse') === 'active'} completed={getStageStatus('parse') === 'completed'}>
          <StepLabel
            StepIconComponent={() => getStageIcon(getStageStatus('parse'))}
            error={getStageStatus('parse') === 'error'}
          >
            <Typography variant="subtitle1" fontWeight={600}>
              Stage 0: Parse Excel
            </Typography>
          </StepLabel>
          <StepContent>
            {parsedData ? (
              <Card variant="outlined" sx={{ mt: 1, bgcolor: 'background.paper' }}>
                <CardContent>
                  <Grid container spacing={2}>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">Total Rows</Typography>
                      <Typography variant="h6">{parsedData.total_rows || 0}</Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">Valid UPCs</Typography>
                      <Typography variant="h6">{parsedData.valid_upcs || 0}</Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">Products with Promo</Typography>
                      <Typography variant="h6">{parsedData.products_with_promo || 0}</Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">Format Detected</Typography>
                      <Chip label={parsedData.format || 'Standard'} size="small" />
                    </Grid>
                    {parsedData.pack_distribution && (
                      <Grid item xs={12}>
                        <Typography variant="caption" color="text.secondary">Pack Sizes</Typography>
                        <Typography variant="body2">{parsedData.pack_distribution}</Typography>
                      </Grid>
                    )}
                  </Grid>
                  
                  {parsedData.preview && parsedData.preview.length > 0 && (
                    <Box sx={{ mt: 2 }}>
                      <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
                        Preview (First {Math.min(5, parsedData.preview.length)} rows):
                      </Typography>
                      <Table size="small">
                        <TableBody>
                          <TableRow>
                            <TableCell><strong>UPC</strong></TableCell>
                            <TableCell><strong>Brand</strong></TableCell>
                            <TableCell><strong>Pack</strong></TableCell>
                            <TableCell><strong>Buy Cost</strong></TableCell>
                            <TableCell><strong>Promo</strong></TableCell>
                            <TableCell><strong>Promo Qty</strong></TableCell>
                            <TableCell><strong>Promo %</strong></TableCell>
                          </TableRow>
                          {parsedData.preview.slice(0, 5).map((row, i) => (
                            <TableRow key={i}>
                              <TableCell>{row.upc?.slice(0, 12)}</TableCell>
                              <TableCell>{row.brand?.slice(0, 15)}</TableCell>
                              <TableCell>{row.pack_size}</TableCell>
                              <TableCell>${row.buy_cost?.toFixed(4) || 'N/A'}</TableCell>
                              <TableCell>{row.has_promo ? '✓' : '—'}</TableCell>
                              <TableCell>{row.promo_qty || '—'}</TableCell>
                              <TableCell>{row.promo_percent ? `${row.promo_percent}%` : '—'}</TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </Box>
                  )}
                </CardContent>
              </Card>
            ) : (
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                Parsing file...
              </Typography>
            )}
          </StepContent>
        </Step>

        {/* STAGE 1: UPC → ASIN */}
        <Step active={getStageStatus('convert') === 'active'} completed={getStageStatus('convert') === 'completed'}>
          <StepLabel
            StepIconComponent={() => getStageIcon(getStageStatus('convert'))}
            error={getStageStatus('convert') === 'error'}
          >
            <Typography variant="subtitle1" fontWeight={600}>
              Stage 1: UPC → ASIN Conversion
            </Typography>
          </StepLabel>
          <StepContent>
            {conversionData ? (
              <Card variant="outlined" sx={{ mt: 1, bgcolor: 'background.paper' }}>
                <CardContent>
                  <Grid container spacing={2}>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">Total UPCs</Typography>
                      <Typography variant="h6">{conversionData.total_upcs || 0}</Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">ASINs Found</Typography>
                      <Typography variant="h6" color="success.main">
                        {conversionData.asins_found || 0} ✅
                      </Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">Not Found</Typography>
                      <Typography variant="h6" color="warning.main">
                        {conversionData.not_found || 0} ⚠️
                      </Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">Conversion Rate</Typography>
                      <Typography variant="h6">
                        {conversionData.conversion_rate?.toFixed(1) || 0}%
                      </Typography>
                    </Grid>
                  </Grid>
                  
                  {conversionData.not_found > 0 && (
                    <Alert severity="warning" sx={{ mt: 2 }}>
                      {conversionData.not_found} products need manual ASIN entry
                    </Alert>
                  )}
                </CardContent>
              </Card>
            ) : (
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                Converting UPCs to ASINs...
              </Typography>
            )}
          </StepContent>
        </Step>

        {/* STAGE 2: SP-API PRICING */}
        <Step active={getStageStatus('pricing') === 'active'} completed={getStageStatus('pricing') === 'completed'}>
          <StepLabel
            StepIconComponent={() => getStageIcon(getStageStatus('pricing'))}
            error={getStageStatus('pricing') === 'error'}
          >
            <Typography variant="subtitle1" fontWeight={600}>
              Stage 2: SP-API Pricing & Fees
            </Typography>
          </StepLabel>
          <StepContent>
            {pricingData ? (
              <Card variant="outlined" sx={{ mt: 1, bgcolor: 'background.paper' }}>
                <CardContent>
                  <Grid container spacing={2}>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">Products Analyzed</Typography>
                      <Typography variant="h6">{pricingData.analyzed || 0}</Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">Profitable (ROI ≥ 30%)</Typography>
                      <Typography variant="h6" color="success.main">
                        {pricingData.profitable || 0} ✅
                      </Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">Not Profitable</Typography>
                      <Typography variant="h6" color="error.main">
                        {pricingData.not_profitable || 0} ✗
                      </Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">Average ROI</Typography>
                      <Typography variant="h6">
                        {pricingData.avg_roi?.toFixed(1) || 0}%
                      </Typography>
                    </Grid>
                    {pricingData.best_roi && (
                      <Grid item xs={12}>
                        <Typography variant="caption" color="text.secondary">Best ROI</Typography>
                        <Typography variant="body2">
                          {pricingData.best_roi.value?.toFixed(1)}% (ASIN: {pricingData.best_roi.asin})
                        </Typography>
                      </Grid>
                    )}
                  </Grid>
                </CardContent>
              </Card>
            ) : (
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                Fetching pricing and fees...
              </Typography>
            )}
          </StepContent>
        </Step>

        {/* STAGE 3: KEEPA */}
        <Step active={getStageStatus('keepa') === 'active'} completed={getStageStatus('keepa') === 'completed'}>
          <StepLabel
            StepIconComponent={() => getStageIcon(getStageStatus('keepa'))}
            error={getStageStatus('keepa') === 'error'}
          >
            <Typography variant="subtitle1" fontWeight={600}>
              Stage 3: Keepa Deep Analysis
            </Typography>
          </StepLabel>
          <StepContent>
            {keepaData ? (
              <Card variant="outlined" sx={{ mt: 1, bgcolor: 'background.paper' }}>
                <CardContent>
                  <Grid container spacing={2}>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">Products Analyzed</Typography>
                      <Typography variant="h6">{keepaData.analyzed || 0}</Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">Still Profitable at Worst</Typography>
                      <Typography variant="h6" color="success.main">
                        {keepaData.still_profitable || 0} ✅
                      </Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">Risky</Typography>
                      <Typography variant="h6" color="warning.main">
                        {keepaData.risky || 0} ⚠️
                      </Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">Amazon is Seller</Typography>
                      <Typography variant="h6" color="warning.main">
                        {keepaData.amazon_seller || 0} ⚠️
                      </Typography>
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>
            ) : (
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                Fetching Keepa data for profitable products...
              </Typography>
            )}
          </StepContent>
        </Step>
      </Stepper>

      {/* Overall Progress */}
      {job && job.progress !== undefined && (
        <Box sx={{ mt: 3 }}>
          <LinearProgress
            variant="determinate"
            value={job.progress || 0}
            sx={{ height: 8, borderRadius: 1 }}
          />
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
            {job.processed_items || 0} / {job.total_items || '?'} items processed
          </Typography>
        </Box>
      )}
    </Box>
  );
}

