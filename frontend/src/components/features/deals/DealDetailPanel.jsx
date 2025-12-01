import { useState, useEffect } from 'react';
import { Drawer, Box, Typography, IconButton, Grid, Card, CardContent, Chip, Button, Divider, Tabs, Tab, TextField, Table, TableBody, TableRow, TableCell } from '@mui/material';
import { X, MessageCircle, Bookmark, ShoppingCart, TrendingUp, Users, History, Calculator, FileText } from 'lucide-react';
import { formatCurrency, formatROI, formatRank } from '../../../utils/formatters';
import StatusBadge from '../../common/StatusBadge';
import GatingBadge from '../../common/GatingBadge';
import PriceHistoryChart from './PriceHistoryChart';
import SalesEstimate from './SalesEstimate';
import { habexa } from '../../../theme';
import api from '../../../services/api';
import { useToast } from '../../../context/ToastContext';

const DealDetailPanel = ({ deal, open, onClose, onSave, onOrder, onMessage }) => {
  const [tab, setTab] = useState(0);
  const [notes, setNotes] = useState(deal?.notes || '');
  const [calculatorValues, setCalculatorValues] = useState({
    buyCost: deal?.buy_cost || 0,
    prepCost: deal?.prep_cost || 0.50,
    inboundShipping: deal?.inbound_shipping || 0.50,
    sellPrice: deal?.sell_price || 0,
  });
  const { showToast } = useToast();

  if (!deal) return null;

  // Update calculator values when deal changes
  useEffect(() => {
    if (deal) {
      setNotes(deal.notes || '');
      setCalculatorValues({
        buyCost: deal.buy_cost || 0,
        prepCost: deal.prep_cost || 0.50,
        inboundShipping: deal.inbound_shipping || 0.50,
        sellPrice: deal.sell_price || 0,
      });
    }
  }, [deal]);

  const calculateProfit = (values) => {
    const totalCost = values.buyCost + values.prepCost + values.inboundShipping;
    const referralFee = values.sellPrice * 0.15; // Simplified
    const fbaFee = values.sellPrice < 10 ? 3.00 : values.sellPrice < 25 ? 4.50 : values.sellPrice < 50 ? 5.50 : values.sellPrice < 100 ? 7.00 : 8.50;
    const netPayout = values.sellPrice - referralFee - fbaFee - values.inboundShipping;
    const netProfit = netPayout - totalCost;
    const roi = totalCost > 0 ? (netProfit / totalCost) * 100 : 0;
    const margin = values.sellPrice > 0 ? (netProfit / values.sellPrice) * 100 : 0;
    return { netProfit, roi, margin, totalCost, netPayout, referralFee, fbaFee };
  };

  const calculatorResult = calculateProfit(calculatorValues);

  const handleSaveNotes = async () => {
    try {
      await api.put(`/deals/${deal.id}`, { notes });
      showToast('Notes saved', 'success');
    } catch (error) {
      showToast('Failed to save notes', 'error');
    }
  };

  const profitBreakdown = {
    buyCost: deal.buy_cost || 0,
    shipping: deal.inbound_shipping || 0.50,
    prep: deal.prep_cost || 0.50,
    totalCost: (deal.buy_cost || 0) + (deal.inbound_shipping || 0.50) + (deal.prep_cost || 0.50),
    sellPrice: deal.sell_price || 0,
    referralFee: deal.referral_fee || (deal.sell_price * 0.15 || 0),
    fbaFee: deal.fba_fee || 0,
    inboundShipping: deal.inbound_shipping || 0.50,
    netPayout: (deal.sell_price || 0) - (deal.referral_fee || 0) - (deal.fba_fee || 0) - (deal.inbound_shipping || 0.50),
    netProfit: deal.net_profit || 0,
    roi: deal.roi || 0,
  };

  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={onClose}
      PaperProps={{
        sx: {
          width: { xs: '100%', sm: 700 },
          maxWidth: '90vw',
        },
      }}
    >
      <Box sx={{ p: 3, height: '100%', overflow: 'auto' }}>
        {/* Header */}
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Typography variant="h5" fontWeight={700}>
            Product Analysis
          </Typography>
          <IconButton onClick={onClose}>
            <X size={20} />
          </IconButton>
        </Box>

        {/* Product Info */}
        <Box display="flex" gap={2} mb={2}>
          <Box
            sx={{
              width: 80,
              height: 80,
              borderRadius: 2,
              backgroundColor: habexa.gray[100],
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}
          >
            {deal.image_url ? (
              <img
                src={deal.image_url}
                alt={deal.title}
                style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: 8 }}
              />
            ) : (
              <Typography variant="h4">📦</Typography>
            )}
          </Box>
          <Box flex={1}>
            <Typography variant="h6" fontWeight={600} mb={0.5}>
              {deal.title || 'Unknown Product'}
            </Typography>
            <Typography variant="body2" fontFamily="monospace" color="text.secondary" mb={1}>
              {deal.asin}
            </Typography>
            <Box display="flex" gap={1} flexWrap="wrap">
              <StatusBadge status={deal.status} roi={deal.roi} />
              <GatingBadge status={deal.gating_status} />
              {deal.amazon_is_seller && (
                <Chip
                  label="⚠️ Amazon Selling"
                  size="small"
                  sx={{
                    backgroundColor: habexa.warning.light,
                    color: habexa.warning.main,
                  }}
                />
              )}
            </Box>
          </Box>
        </Box>

        {/* Metrics Grid */}
        <Grid container spacing={2} mb={2}>
          <Grid item xs={6} sm={3}>
            <Card>
              <CardContent sx={{ textAlign: 'center', py: 2 }}>
                <Typography variant="h4" fontWeight={700} color="success.main">
                  {formatCurrency(profitBreakdown.netProfit)}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Profit
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={6} sm={3}>
            <Card>
              <CardContent sx={{ textAlign: 'center', py: 2 }}>
                <Typography variant="h4" fontWeight={700} color={deal.roi > 0 ? 'success.main' : 'error.main'}>
                  {formatROI(deal.roi)}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  ROI
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={6} sm={3}>
            <Card>
              <CardContent sx={{ textAlign: 'center', py: 2 }}>
                <Typography variant="h4" fontWeight={700}>
                  {formatRank(deal.sales_rank)}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Rank
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={6} sm={3}>
            <Card>
              <CardContent sx={{ textAlign: 'center', py: 2 }}>
                <Typography variant="h4" fontWeight={700}>
                  ~{deal.estimated_monthly_sales || 0}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Est/Mo
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {/* Tabs */}
        <Tabs value={tab} onChange={(e, v) => setTab(v)} sx={{ mb: 3, borderBottom: 1, borderColor: 'divider' }}>
          <Tab icon={<TrendingUp size={16} />} iconPosition="start" label="Overview" />
          <Tab icon={<Users size={16} />} iconPosition="start" label="Competition" />
          <Tab icon={<History size={16} />} iconPosition="start" label="History" />
          <Tab icon={<Calculator size={16} />} iconPosition="start" label="Calculator" />
          <Tab icon={<FileText size={16} />} iconPosition="start" label="Notes" />
        </Tabs>

        {/* Overview Tab */}
        {tab === 0 && (
          <>
            {/* Profit Breakdown */}
            <Card sx={{ mb: 3 }}>
              <CardContent>
                <Typography variant="h6" fontWeight={600} mb={2}>
                  💰 Profit Breakdown
                </Typography>
                <Box display="flex" flexDirection="column" gap={1}>
                  <Box display="flex" justifyContent="space-between">
                    <Typography variant="body2" color="text.secondary">
                      Your Cost
                    </Typography>
                    <Typography variant="body2" fontWeight={600}>
                      {formatCurrency(profitBreakdown.buyCost)}
                    </Typography>
                  </Box>
                  <Box display="flex" justifyContent="space-between">
                    <Typography variant="body2" color="text.secondary">
                      + Shipping Est.
                    </Typography>
                    <Typography variant="body2" fontWeight={600}>
                      {formatCurrency(profitBreakdown.shipping)}
                    </Typography>
                  </Box>
                  <Box display="flex" justifyContent="space-between">
                    <Typography variant="body2" color="text.secondary">
                      + Prep Fee
                    </Typography>
                    <Typography variant="body2" fontWeight={600}>
                      {formatCurrency(profitBreakdown.prep)}
                    </Typography>
                  </Box>
                  <Divider sx={{ my: 1 }} />
                  <Box display="flex" justifyContent="space-between">
                    <Typography variant="body2" fontWeight={600}>
                      Total Cost
                    </Typography>
                    <Typography variant="body2" fontWeight={600}>
                      {formatCurrency(profitBreakdown.totalCost)}
                    </Typography>
                  </Box>
                  <Box mt={2} />
                  <Box display="flex" justifyContent="space-between">
                    <Typography variant="body2" color="text.secondary">
                      Sell Price
                    </Typography>
                    <Typography variant="body2" fontWeight={600}>
                      {formatCurrency(profitBreakdown.sellPrice)}
                    </Typography>
                  </Box>
                  <Box display="flex" justifyContent="space-between">
                    <Typography variant="body2" color="text.secondary">
                      - Amazon Referral (15%)
                    </Typography>
                    <Typography variant="body2" color="error.main">
                      -{formatCurrency(profitBreakdown.referralFee)}
                    </Typography>
                  </Box>
                  <Box display="flex" justifyContent="space-between">
                    <Typography variant="body2" color="text.secondary">
                      - FBA Fee
                    </Typography>
                    <Typography variant="body2" color="error.main">
                      -{formatCurrency(profitBreakdown.fbaFee)}
                    </Typography>
                  </Box>
                  <Box display="flex" justifyContent="space-between">
                    <Typography variant="body2" color="text.secondary">
                      - Inbound Shipping
                    </Typography>
                    <Typography variant="body2" color="error.main">
                      -{formatCurrency(profitBreakdown.inboundShipping)}
                    </Typography>
                  </Box>
                  <Divider sx={{ my: 1 }} />
                  <Box display="flex" justifyContent="space-between">
                    <Typography variant="body1" fontWeight={700} color="success.main">
                      💵 Net Profit
                    </Typography>
                    <Typography variant="body1" fontWeight={700} color="success.main">
                      {formatCurrency(profitBreakdown.netProfit)}
                    </Typography>
                  </Box>
                  <Box display="flex" justifyContent="space-between" mt={1}>
                    <Typography variant="body2" fontWeight={600} color="success.main">
                      📊 ROI
                    </Typography>
                    <Typography variant="body2" fontWeight={600} color="success.main">
                      {formatROI(profitBreakdown.roi)}
                    </Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>

            {/* Supplier Info */}
            {deal.supplier_name && (
              <Card sx={{ mb: 3 }}>
                <CardContent>
                  <Typography variant="h6" fontWeight={600} mb={2}>
                    👥 Supplier Info
                  </Typography>
                  <Typography variant="body1" fontWeight={600} mb={0.5}>
                    {deal.supplier_name}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" mb={2}>
                    ★★★★☆ (4.2) • Avg Lead Time: 5-7 days
                  </Typography>
                  <Box display="flex" gap={1}>
                    <Button size="small" variant="outlined" startIcon={<MessageCircle size={14} />}>
                      Telegram
                    </Button>
                    <Button size="small" variant="outlined">
                      WhatsApp
                    </Button>
                    <Button size="small" variant="outlined">
                      Email
                    </Button>
                  </Box>
                </CardContent>
              </Card>
            )}
          </>
        )}

        {/* Competition Tab */}
        {tab === 1 && (
          <Box>
            <Typography variant="h6" fontWeight={600} mb={2}>
              Buy Box Analysis
            </Typography>
            <Grid container spacing={2} mb={3}>
              <Grid item xs={6}>
                <Card>
                  <CardContent sx={{ textAlign: 'center', py: 2 }}>
                    <Typography variant="h4" fontWeight={700}>
                      {deal.num_fba_sellers || 0}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      FBA Sellers
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={6}>
                <Card>
                  <CardContent sx={{ textAlign: 'center', py: 2 }}>
                    <Typography variant="h4" fontWeight={700}>
                      {deal.num_fbm_sellers || 0}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      FBM Sellers
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>

            <Box sx={{ mb: 3 }}>
              <Typography variant="subtitle2" fontWeight={600} mb={1}>
                Buy Box Winner
              </Typography>
              <Chip
                label={deal.amazon_is_seller ? "Amazon" : deal.buy_box_winner || "Unknown"}
                color={deal.amazon_is_seller ? "warning" : "default"}
                sx={{ mb: 2 }}
              />
            </Box>

            <Card>
              <CardContent>
                <Typography variant="subtitle2" fontWeight={600} mb={2}>
                  Price Comparison
                </Typography>
                <Table size="small">
                  <TableBody>
                    <TableRow>
                      <TableCell>Your Cost</TableCell>
                      <TableCell align="right" fontWeight={600}>
                        {formatCurrency(deal.buy_cost || 0)}
                      </TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>Lowest FBA</TableCell>
                      <TableCell align="right">
                        {deal.lowest_fba_price ? formatCurrency(deal.lowest_fba_price) : 'N/A'}
                      </TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>Lowest FBM</TableCell>
                      <TableCell align="right">
                        {deal.lowest_fbm_price ? formatCurrency(deal.lowest_fbm_price) : 'N/A'}
                      </TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>Buy Box</TableCell>
                      <TableCell align="right" fontWeight={600}>
                        {formatCurrency(deal.sell_price || 0)}
                      </TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </Box>
        )}

        {/* History Tab */}
        {tab === 2 && (
          <Box>
            {/* Price History Chart */}
            <Box mb={3}>
              <PriceHistoryChart
                asin={deal.asin}
                buyCost={deal.buy_cost}
              />
            </Box>
            
            {/* Sales Estimate */}
            {deal.keepa_data && (
              <Card sx={{ mb: 3 }}>
                <CardContent>
                  <Typography variant="h6" fontWeight={600} mb={2}>
                    📊 Sales Estimate
                  </Typography>
                  <SalesEstimate
                    drops30={deal.keepa_data?.drops?.drops_30}
                    drops90={deal.keepa_data?.drops?.drops_90}
                    rank={deal.sales_rank}
                    category={deal.sales_rank_category}
                  />
                </CardContent>
              </Card>
            )}
            
            {/* Historical Stats */}
            <Card>
              <CardContent>
                <Typography variant="h6" fontWeight={600} mb={2}>
                  Historical Data
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={6} sm={3}>
                    <Typography variant="caption" color="text.secondary">
                      90-Day Avg Price
                    </Typography>
                    <Typography variant="h6">
                      {deal.avg_price_90d ? formatCurrency(deal.avg_price_90d) : 'N/A'}
                    </Typography>
                  </Grid>
                  <Grid item xs={6} sm={3}>
                    <Typography variant="caption" color="text.secondary">
                      90-Day Avg Rank
                    </Typography>
                    <Typography variant="h6">
                      {deal.avg_rank_90d ? formatRank(deal.avg_rank_90d) : 'N/A'}
                    </Typography>
                  </Grid>
                  <Grid item xs={6} sm={3}>
                    <Typography variant="caption" color="text.secondary">
                      Est. Monthly Sales
                    </Typography>
                    <Typography variant="h6">
                      {deal.estimated_monthly_sales || 'N/A'}
                    </Typography>
                  </Grid>
                  <Grid item xs={6} sm={3}>
                    <Typography variant="caption" color="text.secondary">
                      Price Trend
                    </Typography>
                    <Typography variant="h6">
                      {deal.price_trend || 'Stable'}
                    </Typography>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </Box>
        )}
        
        {/* Old History Tab - keeping for reference */}
        {false && tab === 2 && (
          <Box>
            <Typography variant="h6" fontWeight={600} mb={2}>
              Price & Rank History
            </Typography>
            <Card>
              <CardContent>
                <Typography variant="body2" color="text.secondary" mb={2}>
                  Historical data will appear here when Keepa integration is enabled.
                </Typography>
                {deal.avg_price_90d && (
                  <Box mb={2}>
                    <Typography variant="body2" color="text.secondary">
                      90-Day Average Price
                    </Typography>
                    <Typography variant="h6" fontWeight={600}>
                      {formatCurrency(deal.avg_price_90d)}
                    </Typography>
                  </Box>
                )}
                {deal.avg_rank_90d && (
                  <Box>
                    <Typography variant="body2" color="text.secondary">
                      90-Day Average Rank
                    </Typography>
                    <Typography variant="h6" fontWeight={600}>
                      {formatRank(deal.avg_rank_90d)}
                    </Typography>
                  </Box>
                )}
              </CardContent>
            </Card>
          </Box>
        )}

        {/* Calculator Tab */}
        {tab === 3 && (
          <Box>
            <Typography variant="h6" fontWeight={600} mb={2}>
              Profit Calculator
            </Typography>
            <Card sx={{ mb: 3 }}>
              <CardContent>
                <Box display="flex" flexDirection="column" gap={2}>
                  <TextField
                    label="Buy Cost"
                    type="number"
                    value={calculatorValues.buyCost}
                    onChange={(e) => setCalculatorValues({ ...calculatorValues, buyCost: parseFloat(e.target.value) || 0 })}
                    InputProps={{ startAdornment: '$' }}
                    fullWidth
                  />
                  <TextField
                    label="Prep Cost"
                    type="number"
                    value={calculatorValues.prepCost}
                    onChange={(e) => setCalculatorValues({ ...calculatorValues, prepCost: parseFloat(e.target.value) || 0 })}
                    InputProps={{ startAdornment: '$' }}
                    fullWidth
                  />
                  <TextField
                    label="Inbound Shipping"
                    type="number"
                    value={calculatorValues.inboundShipping}
                    onChange={(e) => setCalculatorValues({ ...calculatorValues, inboundShipping: parseFloat(e.target.value) || 0 })}
                    InputProps={{ startAdornment: '$' }}
                    fullWidth
                  />
                  <TextField
                    label="Sell Price"
                    type="number"
                    value={calculatorValues.sellPrice}
                    onChange={(e) => setCalculatorValues({ ...calculatorValues, sellPrice: parseFloat(e.target.value) || 0 })}
                    InputProps={{ startAdornment: '$' }}
                    fullWidth
                  />
                </Box>
              </CardContent>
            </Card>

            <Card>
              <CardContent>
                <Typography variant="h6" fontWeight={600} mb={2}>
                  Results
                </Typography>
                <Box display="flex" flexDirection="column" gap={1}>
                  <Box display="flex" justifyContent="space-between">
                    <Typography variant="body2" color="text.secondary">
                      Total Cost
                    </Typography>
                    <Typography variant="body2" fontWeight={600}>
                      {formatCurrency(calculatorResult.totalCost)}
                    </Typography>
                  </Box>
                  <Box display="flex" justifyContent="space-between">
                    <Typography variant="body2" color="text.secondary">
                      Net Payout
                    </Typography>
                    <Typography variant="body2" fontWeight={600}>
                      {formatCurrency(calculatorResult.netPayout)}
                    </Typography>
                  </Box>
                  <Divider sx={{ my: 1 }} />
                  <Box display="flex" justifyContent="space-between">
                    <Typography variant="body1" fontWeight={700} color={calculatorResult.netProfit > 0 ? 'success.main' : 'error.main'}>
                      Net Profit
                    </Typography>
                    <Typography variant="body1" fontWeight={700} color={calculatorResult.netProfit > 0 ? 'success.main' : 'error.main'}>
                      {formatCurrency(calculatorResult.netProfit)}
                    </Typography>
                  </Box>
                  <Box display="flex" justifyContent="space-between" mt={1}>
                    <Typography variant="body2" fontWeight={600}>
                      ROI
                    </Typography>
                    <Typography variant="body2" fontWeight={600} color={calculatorResult.roi > 0 ? 'success.main' : 'error.main'}>
                      {formatROI(calculatorResult.roi)}
                    </Typography>
                  </Box>
                  <Box display="flex" justifyContent="space-between">
                    <Typography variant="body2" fontWeight={600}>
                      Margin
                    </Typography>
                    <Typography variant="body2" fontWeight={600} color={calculatorResult.margin > 0 ? 'success.main' : 'error.main'}>
                      {formatROI(calculatorResult.margin)}
                    </Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Box>
        )}

        {/* Notes Tab */}
        {tab === 4 && (
          <Box>
            <Typography variant="h6" fontWeight={600} mb={2}>
              Notes
            </Typography>
            <Card>
              <CardContent>
                <TextField
                  multiline
                  rows={8}
                  fullWidth
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Add your notes about this deal..."
                  sx={{ mb: 2 }}
                />
                <Button
                  variant="contained"
                  onClick={handleSaveNotes}
                  sx={{
                    backgroundColor: habexa.purple.main,
                    '&:hover': { backgroundColor: habexa.purple.dark },
                  }}
                >
                  Save Notes
                </Button>
              </CardContent>
            </Card>
          </Box>
        )}

        {/* Actions */}
        <Box display="flex" gap={2} mt={3}>
          <Button
            fullWidth
            variant="outlined"
            startIcon={<Bookmark size={18} />}
            onClick={onSave}
            sx={{ borderColor: habexa.purple.main, color: habexa.purple.main }}
          >
            Save to Watchlist
          </Button>
          <Button
            fullWidth
            variant="contained"
            startIcon={<ShoppingCart size={18} />}
            onClick={onOrder}
            sx={{
              backgroundColor: habexa.purple.main,
              '&:hover': { backgroundColor: habexa.purple.dark },
            }}
          >
            Add to Order
          </Button>
        </Box>
      </Box>
    </Drawer>
  );
};

export default DealDetailPanel;
