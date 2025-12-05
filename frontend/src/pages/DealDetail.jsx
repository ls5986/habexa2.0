import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box, Typography, Card, CardContent, Grid, Chip, Button,
  IconButton, Tabs, Tab, CircularProgress, Tooltip, Divider,
  Table, TableBody, TableRow, TableCell, Accordion, AccordionSummary,
  AccordionDetails, InputAdornment
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import {
  ArrowLeft, ArrowRight, Copy, ExternalLink, RefreshCw, Star,
  TrendingUp, Package, Calculator, BarChart2, Users, Layers,
  FileText, DollarSign, ShoppingCart, Check, CheckCircle, XCircle, AlertTriangle
} from 'lucide-react';
import api from '../services/api';
import { habexa } from '../theme';

// Helper function
const formatPricingReason = (reason) => {
  const reasons = {
    'no_active_offers': 'No active sellers on Amazon',
    'no_response': 'No response from Amazon API',
    'gated': 'Product is gated/restricted',
    'invalid_asin': 'ASIN may be invalid',
    'unknown': 'Unknown reason',
  };
  return reasons[reason] || reason || 'Unknown';
};

// Import tab components
import ProfitCalculator from '../components/features/deals/ProfitCalculator';
import MarketIntelligence from '../components/features/deals/MarketIntelligence';
import PriceHistoryChart from '../components/features/deals/PriceHistoryChart';
import CompetitorAnalysis from '../components/features/deals/CompetitorAnalysis';
import VariationAnalysis from '../components/features/deals/VariationAnalysis';
import ListingScore from '../components/features/deals/ListingScore';

export default function DealDetail() {
  const { dealId } = useParams();
  const navigate = useNavigate();
  const [deal, setDeal] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [spData, setSpData] = useState({
    offers: null,
    fees: null,
    eligibility: null,
    sales: null
  });
  const [keepaData, setKeepaData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState(0);
  const [allDealIds, setAllDealIds] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(-1);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    fetchDeal();
    fetchAllDealIds();
  }, [dealId]);

  const fetchDeal = async () => {
    setLoading(true);
    try {
      const res = await api.get(`/deals/${dealId}`);
      setDeal(res.data);
      
      // Extract analysis data - handle both direct and JSONB structure
      let extractedAnalysis = res.data?.analysis;
      if (extractedAnalysis?.analysis_data) {
        extractedAnalysis = { ...extractedAnalysis, ...extractedAnalysis.analysis_data };
      }
      setAnalysis(extractedAnalysis);
      
      const asin = res.data?.asin;
      const sellPrice = extractedAnalysis?.sell_price || res.data?.buy_cost || 0;
      
      if (asin) {
        // Fetch SP-API data and Keepa in parallel
        const [offersRes, feesRes, eligibilityRes, salesRes, keepaRes] = await Promise.allSettled([
          api.get(`/sp-api/product/${asin}/offers`).catch(() => null),
          sellPrice > 0 ? api.get(`/sp-api/product/${asin}/fees?price=${sellPrice}`).catch(() => null) : Promise.resolve(null),
          api.get(`/sp-api/product/${asin}/eligibility`).catch(() => null),
          api.get(`/sp-api/product/${asin}/sales-estimate`).catch(() => null),
          api.get(`/keepa/product/${asin}?days=90`).catch(() => null)
        ]);
        
        setSpData({
          offers: offersRes.status === 'fulfilled' && offersRes.value?.data ? offersRes.value.data : null,
          fees: feesRes.status === 'fulfilled' && feesRes.value?.data ? feesRes.value.data : null,
          eligibility: eligibilityRes.status === 'fulfilled' && eligibilityRes.value?.data ? eligibilityRes.value.data : null,
          sales: salesRes.status === 'fulfilled' && salesRes.value?.data ? salesRes.value.data : null
        });
        
        if (keepaRes.status === 'fulfilled' && keepaRes.value?.data) {
          setKeepaData(keepaRes.value.data);
        }
      }
    } catch (err) {
      console.error('Failed to fetch deal:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchAllDealIds = async () => {
    try {
      const res = await api.get('/deals?limit=100');
      const ids = (res.data.deals || res.data || []).map(d => d.id);
      setAllDealIds(ids);
      setCurrentIndex(ids.indexOf(dealId));
    } catch (err) {
      console.error('Failed to fetch deal list:', err);
    }
  };

  const copyAsin = () => {
    if (deal?.asin) {
      navigator.clipboard.writeText(deal.asin);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleReanalyze = async () => {
    try {
      await api.post(`/deals/${dealId}/analyze`);
      fetchDeal();
    } catch (err) {
      console.error('Reanalyze failed:', err);
    }
  };

  const handlePrev = () => {
    if (currentIndex > 0) {
      navigate(`/deals/${allDealIds[currentIndex - 1]}`);
    }
  };

  const handleNext = () => {
    if (currentIndex < allDealIds.length - 1) {
      navigate(`/deals/${allDealIds[currentIndex + 1]}`);
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (!deal) {
    return (
      <Box sx={{ p: 3 }}>
        <Typography>Deal not found</Typography>
        <Button onClick={() => navigate('/deals')}>Back to Deal Feed</Button>
      </Box>
    );
  }

  const isProfitable = (analysis?.roi || 0) >= 30;
  const isEligible = spData.eligibility?.canSell !== false;

  // Tab panels
  const tabs = [
    { icon: Calculator, label: 'Calculator' },
    { icon: BarChart2, label: 'Market' },
    { icon: TrendingUp, label: 'History' },
    { icon: Users, label: 'Competitors' },
    { icon: Layers, label: 'Variations' },
    { icon: FileText, label: 'Listing' },
  ];

  return (
    <Box sx={{ p: 3, maxWidth: 1400, mx: 'auto', bgcolor: '#f5f5f5', minHeight: '100vh' }}>
      {/* Header Row */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Button 
          startIcon={<ArrowLeft size={16} />} 
          onClick={() => navigate('/deals')}
          sx={{ color: 'text.secondary' }}
        >
          Back to Deal Feed
        </Button>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Typography variant="body2" color="text.secondary">
            {currentIndex + 1} of {allDealIds.length}
          </Typography>
          <IconButton 
            size="small" 
            onClick={handlePrev}
            disabled={currentIndex <= 0}
          >
            <ArrowLeft size={18} />
          </IconButton>
          <IconButton 
            size="small" 
            onClick={handleNext}
            disabled={currentIndex >= allDealIds.length - 1}
          >
            <ArrowRight size={18} />
          </IconButton>
        </Box>
      </Box>

      {/* Main Content - Two Column Layout */}
      <Grid container spacing={3}>
        {/* Left Column - Product Info (Fixed) */}
        <Grid item xs={12} md={4}>
          <Card sx={{ position: 'sticky', top: 20, bgcolor: '#ffffff' }}>
            <CardContent>
              {/* Product Image */}
              <Box sx={{ 
                width: '100%', 
                aspectRatio: '1', 
                bgcolor: '#f5f5f5',
                border: '1px solid #e0e0e0',
                borderRadius: 2, 
                mb: 2,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                overflow: 'hidden'
              }}>
                {analysis?.image_url ? (
                  <img 
                    src={analysis.image_url} 
                    alt={analysis.product_title || deal.asin}
                    style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                  />
                ) : (
                  <Package size={64} color="#666666" />
                )}
              </Box>

              {/* ASIN & Links */}
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <Typography variant="h6" fontFamily="monospace" color="primary">
                  {deal.asin}
                </Typography>
                <Tooltip title={copied ? 'Copied!' : 'Copy ASIN'}>
                  <IconButton size="small" onClick={copyAsin}>
                    {copied ? <Check size={14} /> : <Copy size={14} />}
                  </IconButton>
                </Tooltip>
                <IconButton 
                  size="small" 
                  component="a" 
                  href={`https://amazon.com/dp/${deal.asin}`}
                  target="_blank"
                >
                  <ExternalLink size={14} />
                </IconButton>
              </Box>

              {/* Title */}
              <Typography variant="body2" sx={{ mb: 2, lineHeight: 1.4 }}>
                {analysis?.product_title || deal.product_title || 'Unknown Product'}
              </Typography>

              {/* Eligibility Badge */}
              {spData.eligibility && (
                <Box sx={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  gap: 1, 
                  p: 1.5, 
                  bgcolor: isEligible ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)',
                  borderRadius: 1,
                  mb: 2
                }}>
                  {isEligible ? (
                    <>
                      <CheckCircle size={16} color={habexa.success.main} />
                      <Typography variant="body2" color={habexa.success.main}>Eligible to Sell</Typography>
                    </>
                  ) : (
                    <>
                      <XCircle size={16} color={habexa.error.main} />
                      <Typography variant="body2" color={habexa.error.main}>Restricted / Gated</Typography>
                    </>
                  )}
                </Box>
              )}

              {/* Brand & Category */}
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
                {analysis?.brand && (
                  <Chip label={analysis.brand} size="small" variant="outlined" />
                )}
                {analysis?.category && (
                  <Chip label={analysis.category} size="small" variant="outlined" />
                )}
                {deal.status === 'pending' && (
                  <Chip label="Pending" color="warning" size="small" />
                )}
                {deal.status === 'analyzed' && (
                  <Chip label="Analyzed" color="success" size="small" />
                )}
              </Box>

              <Divider sx={{ my: 2 }} />

              {/* Financials */}
              <Typography variant="overline" color="text.secondary">Financials</Typography>
              
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1, mt: 1 }}>
                <Typography variant="body2" color="text.secondary">Buy Cost</Typography>
                <Typography variant="body2" fontWeight="600">${deal?.buy_cost ? deal.buy_cost.toFixed(2) : '—'}</Typography>
              </Box>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                <Typography variant="body2" color="text.secondary">MOQ</Typography>
                <Typography variant="body2" fontWeight="600">{deal?.moq || 1}</Typography>
              </Box>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                <Typography variant="body2" color="text.secondary">Total Investment</Typography>
                <Typography variant="body2" fontWeight="600">
                  ${((deal?.buy_cost || 0) * (deal?.moq || 1)).toFixed(2)}
                </Typography>
              </Box>
              
              {/* No Pricing Alert */}
              {analysis && analysis.pricing_status === 'no_pricing' && (
                <Alert
                  severity="warning"
                  sx={{ mb: 2 }}
                  action={
                    <Button
                      size="small"
                      onClick={() => {
                        // Navigate to manual price entry or show dialog
                        // For now, show alert with instructions
                        window.open(`/products?pricingStatus=no_pricing&asin=${deal.asin}`, '_blank');
                      }}
                    >
                      Enter Price
                    </Button>
                  }
                >
                  <AlertTitle>No Pricing Data Available</AlertTitle>
                  <Typography variant="body2">
                    Reason: {formatPricingReason(analysis?.pricing_status_reason)}
                  </Typography>
                  <Typography variant="body2" sx={{ mt: 1 }}>
                    This usually means:
                    • Product is currently out of stock
                    • No active FBA/FBM sellers
                    • Product may be gated/restricted
                  </Typography>
                  {analysis.fba_lowest_365d && (
                    <Typography variant="body2" sx={{ mt: 1 }}>
                      💡 Keepa shows it sold for ${analysis.fba_lowest_365d?.toFixed(2)} in the past 365 days
                    </Typography>
                  )}
                </Alert>
              )}

              {/* Complete Cost Breakdown */}
              {analysis && (
                <Box sx={{ p: 2, bgcolor: 'grey.50', borderRadius: 1, mb: 2, mt: 2 }}>
                  <Typography variant="subtitle2" gutterBottom fontWeight={600}>
                    💰 Complete Cost Breakdown
                  </Typography>
                  
                  <Table size="small">
                    <TableBody>
                      {/* Landed Cost Section */}
                      <TableRow>
                        <TableCell>Buy Cost (per unit)</TableCell>
                        <TableCell align="right">${deal.buy_cost?.toFixed(4) || '—'}</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>+ Inbound Shipping</TableCell>
                        <TableCell align="right">${analysis.inbound_shipping?.toFixed(2) || '—'}</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>+ Prep Cost</TableCell>
                        <TableCell align="right">${analysis.prep_cost?.toFixed(2) || '—'}</TableCell>
                      </TableRow>
                      <TableRow sx={{ bgcolor: 'grey.200' }}>
                        <TableCell><strong>= Total Landed Cost</strong></TableCell>
                        <TableCell align="right">
                          <strong>${analysis.total_landed_cost?.toFixed(2) || '—'}</strong>
                        </TableCell>
                      </TableRow>
                      
                      {/* Divider */}
                      <TableRow><TableCell colSpan={2}><Divider /></TableCell></TableRow>
                      
                      {/* Revenue - Costs = Profit */}
                      <TableRow>
                        <TableCell>Sell Price</TableCell>
                        <TableCell align="right">${analysis.sell_price?.toFixed(2) || '—'}</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>- Amazon Fees</TableCell>
                        <TableCell align="right">-${analysis.fees_total?.toFixed(2) || '—'}</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>- Landed Cost</TableCell>
                        <TableCell align="right">-${analysis.total_landed_cost?.toFixed(2) || '—'}</TableCell>
                      </TableRow>
                      <TableRow sx={{ bgcolor: (analysis.net_profit > 0 ? 'success.50' : 'error.50') }}>
                        <TableCell><strong>= Net Profit</strong></TableCell>
                        <TableCell align="right">
                          <strong style={{ color: analysis.net_profit > 0 ? 'green' : 'red' }}>
                            ${analysis.net_profit?.toFixed(2) || '—'}
                          </strong>
                        </TableCell>
                      </TableRow>
                    </TableBody>
                  </Table>
                  
                  <Box sx={{ textAlign: 'center', mt: 2 }}>
                    <Typography 
                      variant="h4" 
                      color={analysis.roi >= 30 ? 'success.main' : 'warning.main'}
                    >
                      {analysis.roi?.toFixed(1) || '—'}% ROI
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {analysis.profit_margin?.toFixed(1) || '—'}% Margin
                    </Typography>
                  </Box>
                </Box>
              )}
              
              {/* Fee Breakdown (expandable) */}
              {analysis && analysis.fees_total && (
                <Accordion sx={{ mb: 2 }}>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Typography>
                      Fee Breakdown (${analysis.fees_total?.toFixed(2)} total)
                    </Typography>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Typography>
                      Referral Fee: ${analysis.referral_fee?.toFixed(2) || '—'} 
                      {analysis.referral_fee_percent && ` (${analysis.referral_fee_percent}%)`}
                    </Typography>
                    <Typography>
                      FBA Fee: ${analysis.fba_fee?.toFixed(2) || '—'}
                    </Typography>
                    {analysis.variable_closing_fee > 0 && (
                      <Typography>
                        Closing Fee: ${analysis.variable_closing_fee?.toFixed(2)}
                      </Typography>
                    )}
                  </AccordionDetails>
                </Accordion>
              )}
              
              {/* Product Dimensions (if available) */}
              {analysis && analysis.item_weight_lb && (
                <Box sx={{ p: 2, bgcolor: 'grey.50', borderRadius: 1, mb: 2 }}>
                  <Typography variant="subtitle2" gutterBottom>📦 Dimensions</Typography>
                  <Typography variant="body2">
                    Weight: {analysis.item_weight_lb} lb | 
                    {analysis.item_length_in && analysis.item_width_in && analysis.item_height_in && (
                      <> {analysis.item_length_in}" × {analysis.item_width_in}" × {analysis.item_height_in}"</>
                    )}
                  </Typography>
                  {analysis.size_tier && (
                    <Chip label={analysis.size_tier} size="small" sx={{ mt: 1 }} />
                  )}
                </Box>
              )}
              
              {/* Promo Comparison Section */}
              {deal.has_promo && deal.promo_percent && (
                <Box sx={{ 
                  p: 2, 
                  bgcolor: 'success.50', 
                  border: '1px solid',
                  borderColor: 'success.main',
                  borderRadius: 1, 
                  mb: 2
                }}>
                  <Typography variant="subtitle1" fontWeight="bold" color="success.dark" gutterBottom>
                    🎉 PROMO: {deal.promo_percent}% OFF
                    {deal.promo_qty > 0 && ` (Min ${deal.promo_qty} cases)`}
                    {deal.promo_qty === 0 && ' (No minimum)'}
                  </Typography>
                  
                  <Grid container spacing={2} sx={{ mt: 1 }}>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">Regular Pricing</Typography>
                      <Typography variant="body2">Buy: ${deal.buy_cost?.toFixed(4) || '—'}/unit</Typography>
                      <Typography variant="body2">Landed: ${analysis?.total_landed_cost?.toFixed(2) || '—'}/unit</Typography>
                      <Typography variant="body2" fontWeight="bold">
                        ROI: {analysis?.roi?.toFixed(1) || '—'}%
                      </Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="success.dark" fontWeight="bold">With Promo</Typography>
                      <Typography variant="body2" color="success.dark">
                        Buy: ${deal.promo_buy_cost?.toFixed(4) || '—'}/unit
                      </Typography>
                      <Typography variant="body2" color="success.dark">
                        Landed: ${analysis?.promo_landed_cost?.toFixed(2) || '—'}/unit
                      </Typography>
                      <Typography variant="body2" color="success.dark" fontWeight="bold">
                        ROI: {analysis?.promo_roi?.toFixed(1) || '—'}% 🚀
                      </Typography>
                    </Grid>
                  </Grid>
                  
                  {deal.promo_qty > 0 && (
                    <>
                      <Divider sx={{ my: 1 }} />
                      <Typography variant="body2">
                        Min Order: {deal.promo_qty} cases × {deal.pack_size || 1} units = {deal.promo_qty * (deal.pack_size || 1)} units
                      </Typography>
                      <Typography variant="body2">
                        Min Investment: {deal.promo_qty} × ${deal.promo_wholesale_cost?.toFixed(2) || '—'} = 
                        <strong> ${((deal.promo_qty || 0) * (deal.promo_wholesale_cost || 0))?.toFixed(2)}</strong>
                      </Typography>
                    </>
                  )}
                </Box>
              )}
              
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                <Typography variant="body2" color="text.secondary">Sell Price</Typography>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography variant="body2" fontWeight="600">
                    ${(spData.offers?.buy_box_price || analysis?.sell_price)?.toFixed(2) || '—'}
                  </Typography>
                  {analysis?.price_source && analysis.price_source.startsWith('sp_api') && (
                    <Chip 
                      label="SP-API" 
                      size="small" 
                      sx={{ 
                        height: 18, 
                        fontSize: 10, 
                        bgcolor: habexa.success.light,
                        color: habexa.success.main
                      }} 
                    />
                  )}
                  {analysis?.price_source && analysis.price_source.startsWith('keepa') && (
                    <Chip 
                      label="Keepa" 
                      size="small" 
                      sx={{ 
                        height: 18, 
                        fontSize: 10, 
                        bgcolor: habexa.warning.light,
                        color: habexa.warning.main
                      }} 
                    />
                  )}
                </Box>
              </Box>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                <Typography variant="body2" color="text.secondary">Referral Fee</Typography>
                <Typography variant="body2">
                  ${(spData.fees?.referralFee || analysis?.referral_fee)?.toFixed(2) || '—'}
                </Typography>
              </Box>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                <Typography variant="body2" color="text.secondary">FBA Fee</Typography>
                <Typography variant="body2">
                  ${(spData.fees?.fbaFee || analysis?.fba_fee)?.toFixed(2) || '—'}
                </Typography>
              </Box>
              <Divider sx={{ my: 1 }} />
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                <Typography variant="body2" fontWeight="600">Profit</Typography>
                <Typography variant="body2" fontWeight="700" color={isProfitable ? 'success.main' : 'error.main'}>
                  ${(analysis?.profit || analysis?.net_profit)?.toFixed(2) || '—'}
                </Typography>
              </Box>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
                <Typography variant="body2" fontWeight="600">ROI</Typography>
                <Typography variant="h6" fontWeight="700" color={isProfitable ? 'success.main' : 'warning.main'}>
                  {analysis?.roi?.toFixed(1) || 0}%
                </Typography>
              </Box>

              {/* Competition Summary */}
              {spData.offers && (
                <>
                  <Divider sx={{ my: 2 }} />
                  <Typography variant="overline" color="text.secondary">Competition</Typography>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1, mt: 1 }}>
                    <Typography variant="body2" color="text.secondary">Buy Box Price</Typography>
                    <Typography variant="body2" fontWeight="600">
                      ${spData.offers.buy_box_price?.toFixed(2) || '—'}
                    </Typography>
                  </Box>
                </>
              )}

              {/* Sales Estimate */}
              {spData.sales && (
                <>
                  <Divider sx={{ my: 2 }} />
                  <Typography variant="overline" color="text.secondary">Sales</Typography>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1, mt: 1 }}>
                    <Typography variant="body2" color="text.secondary">BSR</Typography>
                    <Typography variant="body2" fontWeight="600">
                      #{spData.sales.sales_rank?.toLocaleString() || '—'}
                    </Typography>
                  </Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="body2" color="text.secondary">Est. Monthly</Typography>
                    <Typography variant="body2" fontWeight="600">
                      {spData.sales.est_monthly_sales || '—'} units
                    </Typography>
                  </Box>
                </>
              )}

              {/* 365-Day Analysis - only if data exists */}
              {analysis && analysis.fba_lowest_365d && (
                <Box sx={{ p: 2, bgcolor: 'orange.50', borderRadius: 1, mb: 2, mt: 2 }}>
                  <Typography variant="subtitle2" gutterBottom fontWeight={600}>
                    📊 365-Day Price Analysis
                  </Typography>
                  <Grid container spacing={2}>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">FBA Lowest (365d)</Typography>
                      <Typography variant="body2">${analysis.fba_lowest_365d?.toFixed(2) || '—'}</Typography>
                      {analysis.fba_lowest_date && (
                        <Typography variant="caption" color="text.secondary">
                          on {new Date(analysis.fba_lowest_date).toLocaleDateString()}
                        </Typography>
                      )}
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">Worst Case Profit</Typography>
                      <Typography 
                        variant="body2" 
                        color={analysis.still_profitable_at_worst ? 'success.main' : 'error.main'}
                        fontWeight="bold"
                      >
                        ${analysis.worst_case_profit?.toFixed(2) || '—'}
                      </Typography>
                      {analysis.still_profitable_at_worst ? (
                        <Chip label="✓ Still Profitable" color="success" size="small" sx={{ mt: 0.5 }} />
                      ) : (
                        <Chip label="⚠️ Would Lose Money" color="error" size="small" sx={{ mt: 0.5 }} />
                      )}
                    </Grid>
                  </Grid>
                </Box>
              )}
              
              {/* Competition Section */}
              {analysis && (analysis.fba_seller_count !== undefined || analysis.fbm_seller_count !== undefined) && (
                <Box sx={{ p: 2, bgcolor: 'grey.50', borderRadius: 1, mb: 2 }}>
                  <Typography variant="subtitle2" gutterBottom fontWeight={600}>
                    👥 Competition
                  </Typography>
                  <Typography variant="body2">
                    FBA Sellers: {analysis.fba_seller_count || 0}
                  </Typography>
                  <Typography variant="body2">
                    FBM Sellers: {analysis.fbm_seller_count || 0}
                  </Typography>
                  {analysis.bsr && (
                    <Typography variant="body2">
                      Sales Rank: #{analysis.bsr?.toLocaleString()}
                    </Typography>
                  )}
                  {analysis.sales_drops_30 !== undefined && (
                    <Typography variant="body2">
                      Sales/month (est): {analysis.sales_drops_30} drops in 30d
                    </Typography>
                  )}
                  {analysis.amazon_was_seller && (
                    <Chip label="⚠️ Amazon was seller" color="warning" size="small" sx={{ mt: 1 }} />
                  )}
                </Box>
              )}

              {/* Profitability Badge */}
              <Box sx={{ 
                p: 2, 
                bgcolor: isProfitable ? 'rgba(16,185,129,0.1)' : 'rgba(245,158,11,0.1)', 
                borderRadius: 2,
                textAlign: 'center',
                mb: 2,
                mt: 2
              }}>
                <Typography 
                  variant="h6" 
                  fontWeight="700" 
                  color={isProfitable ? 'success.main' : 'warning.main'}
                  sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 1 }}
                >
                  <TrendingUp size={20} />
                  {isProfitable ? 'Profitable!' : 'Low ROI'}
                </Typography>
              </Box>

              {/* Actions */}
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                <Button 
                  variant="contained" 
                  fullWidth
                  startIcon={<ShoppingCart size={16} />}
                  component="a"
                  href={`https://amazon.com/dp/${deal.asin}`}
                  target="_blank"
                >
                  View on Amazon
                </Button>
                <Button 
                  variant="outlined" 
                  fullWidth
                  startIcon={<RefreshCw size={16} />}
                  onClick={handleReanalyze}
                >
                  Re-analyze
                </Button>
                <Button 
                  variant="outlined" 
                  fullWidth
                  startIcon={<Star size={16} />}
                >
                  Save to Favorites
                </Button>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Right Column - Tabbed Content */}
        <Grid item xs={12} md={8}>
          {/* Tabs */}
          <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
            <Tabs 
              value={activeTab} 
              onChange={(e, v) => setActiveTab(v)}
              variant="scrollable"
              scrollButtons="auto"
            >
              {tabs.map((tab, i) => (
                <Tab 
                  key={i}
                  icon={<tab.icon size={16} />} 
                  iconPosition="start" 
                  label={tab.label}
                  sx={{ minHeight: 48, textTransform: 'none' }}
                />
              ))}
            </Tabs>
          </Box>

          {/* Tab Content */}
          <Box sx={{ minHeight: 500 }}>
            {/* Calculator Tab */}
            {activeTab === 0 && (
              <ProfitCalculator
                initialBuyCost={deal.buy_cost || 0}
                sellPrice={spData.offers?.buy_box_price || analysis?.sell_price || 0}
                referralFee={spData.fees?.referralFee || analysis?.referral_fee || 0}
                fbaFee={spData.fees?.fbaFee || analysis?.fba_fee || 0}
                initialQuantity={deal.moq || 1}
              />
            )}

            {/* Market Intelligence Tab */}
            {activeTab === 1 && (
              <MarketIntelligence 
                deal={deal}
                analysis={analysis}
                spApiOffers={spData.offers}
                spApiSalesEstimate={spData.sales}
              />
            )}

            {/* Price History Tab */}
            {activeTab === 2 && (
              <PriceHistoryChart asin={deal.asin} buyCost={deal.buy_cost} />
            )}

            {/* Competitors Tab */}
            {activeTab === 3 && (
              <CompetitorAnalysis asin={deal.asin} spOffers={spData.offers} />
            )}

            {/* Variations Tab */}
            {activeTab === 4 && (
              <VariationAnalysis asin={deal.asin} keepaData={keepaData} />
            )}

            {/* Listing Quality Tab */}
            {activeTab === 5 && (
              <ListingScore analysis={analysis} keepaData={keepaData} />
            )}
          </Box>
        </Grid>
      </Grid>
    </Box>
  );
}
