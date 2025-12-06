import React, { useState, useMemo } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  ToggleButton,
  ToggleButtonGroup,
  Alert,
  Chip,
  Grid,
} from '@mui/material';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import { habexa } from '../../../theme';

// Chart colors
const COLORS = {
  amazon: '#FF9900',
  new: '#7C6AFA',
  new_fba: '#10B981',
  buy_box: '#3B82F6',
  sales_rank: '#EF4444',
};

const TIME_PERIODS = [
  { value: 30, label: '30D' },
  { value: 90, label: '90D' },
  { value: 180, label: '180D' },
  { value: 365, label: '1Y' },
];

// Simple date formatter
const formatDate = (dateString) => {
  if (!dateString) return '';
  const date = new Date(dateString);
  const month = date.toLocaleString('default', { month: 'short' });
  const day = date.getDate();
  return `${month} ${day}`;
};

const PriceHistoryChart = ({ 
  asin, 
  buyCost,
  deal,
  analysis,
}) => {
  const [chartType, setChartType] = useState('price');
  
  // Use data from database (analysis object) - no API calls needed!
  // All Keepa data is stored in analysis table after analysis runs
  const hasData = analysis && (analysis.bsr || analysis.sell_price || analysis.fba_lowest_365d);

  // Create simple chart data from analysis database fields
  // Note: Full historical price data requires Keepa API calls during analysis
  // For now, show current values and key metrics from database
  const chartData = useMemo(() => {
    if (!analysis) return [];
    
    // If we have price history data stored in analysis, use it
    // Otherwise, create a simple data point from current values
    if (analysis.price_history && Array.isArray(analysis.price_history)) {
      return analysis.price_history.slice(-90); // Last 90 days if available
    }
    
    // Fallback: Show current price point
    const now = new Date().toISOString().split('T')[0];
    return [{
      date: now,
      buy_box: analysis.sell_price,
      current_price: analysis.sell_price,
      sales_rank: analysis.bsr
    }];
  }, [analysis]);

  // Custom tooltip
  const CustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload || !payload.length) return null;

    return (
      <Box
        sx={{
          bgcolor: 'background.paper',
          p: 1.5,
          border: '1px solid',
          borderColor: 'divider',
          borderRadius: 1,
          boxShadow: 2,
        }}
      >
        <Typography variant="caption" color="text.secondary">
          {formatDate(label)}
        </Typography>
        {payload.map((entry, index) => (
          <Box key={index} display="flex" alignItems="center" gap={1} mt={0.5}>
            <Box
              sx={{
                width: 8,
                height: 8,
                borderRadius: '50%',
                bgcolor: entry.color,
              }}
            />
            <Typography variant="body2">
              {entry.name}: {chartType === 'price' ? `$${entry.value?.toFixed(2)}` : entry.value?.toLocaleString()}
            </Typography>
          </Box>
        ))}
      </Box>
    );
  };

  // Stats display from database
  const renderStats = () => {
    if (!analysis) return null;

    return (
      <Grid container spacing={2} sx={{ mb: 2 }}>
        <Grid item xs={6} sm={3}>
          <Box>
            <Typography variant="caption" color="text.secondary">
              Current Price
            </Typography>
            <Typography variant="h6">
              ${analysis.sell_price?.toFixed(2) || 'N/A'}
            </Typography>
          </Box>
        </Grid>
        <Grid item xs={6} sm={3}>
          <Box>
            <Typography variant="caption" color="text.secondary">
              365-Day Low
            </Typography>
            <Typography variant="h6">
              ${analysis.fba_lowest_365d?.toFixed(2) || 'N/A'}
            </Typography>
          </Box>
        </Grid>
        <Grid item xs={6} sm={3}>
          <Box>
            <Typography variant="caption" color="text.secondary">
              Sales Rank
            </Typography>
            <Typography variant="h6">
              {analysis.bsr?.toLocaleString() || 'N/A'}
            </Typography>
          </Box>
        </Grid>
        <Grid item xs={6} sm={3}>
          <Box>
            <Typography variant="caption" color="text.secondary">
              Est. Monthly Sales
            </Typography>
            <Typography variant="h6">
              ~{analysis.sales_drops_30?.toLocaleString() || analysis.estimated_monthly_sales?.toLocaleString() || 'N/A'}
            </Typography>
          </Box>
        </Grid>
      </Grid>
    );
  };

  // Handle no data state
  if (!hasData) {
    return (
      <Card>
        <CardContent>
          <Alert severity="info">
            <Typography variant="body2" fontWeight={600} gutterBottom>
              Price History Data Not Available
            </Typography>
            <Typography variant="body2" color="text.secondary">
              This product hasn't been fully analyzed yet, or price history data wasn't captured.
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
              Click "Re-analyze" to fetch fresh data from Keepa and SP-API.
            </Typography>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent>
        {/* Header */}
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Typography variant="h6" fontWeight={600}>Price History</Typography>
          
          <Box display="flex" gap={1}>
            {/* Chart type toggle */}
            <ToggleButtonGroup
              value={chartType}
              exclusive
              onChange={(e, v) => v && setChartType(v)}
              size="small"
            >
              <ToggleButton value="price">Price</ToggleButton>
              <ToggleButton value="rank">Rank</ToggleButton>
            </ToggleButtonGroup>
            
            {/* Time period toggle */}
            <ToggleButtonGroup
              value={period}
              exclusive
              onChange={(e, v) => v && setPeriod(v)}
              size="small"
            >
              {TIME_PERIODS.map(p => (
                <ToggleButton key={p.value} value={p.value}>
                  {p.label}
                </ToggleButton>
              ))}
            </ToggleButtonGroup>
          </Box>
        </Box>

        {/* Stats */}
        {renderStats()}

        {/* Chart */}
        <Box height={300}>
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis 
                  dataKey="date" 
                  tickFormatter={formatDate}
                  tick={{ fontSize: 12 }}
                />
                <YAxis 
                  tickFormatter={(v) => chartType === 'price' ? `$${v}` : v.toLocaleString()}
                  tick={{ fontSize: 12 }}
                  domain={chartType === 'rank' ? ['auto', 'auto'] : [0, 'auto']}
                  reversed={chartType === 'rank'} // Lower rank is better
                />
                <Tooltip content={<CustomTooltip />} />
                <Legend />
                
                {chartType === 'price' ? (
                  <>
                    <Line
                      type="monotone"
                      dataKey="buy_box"
                      name="Buy Box Price"
                      stroke={COLORS.buy_box}
                      dot={true}
                      strokeWidth={2}
                    />
                    <Line
                      type="monotone"
                      dataKey="current_price"
                      name="Current Price"
                      stroke={COLORS.new_fba}
                      dot={true}
                      strokeWidth={1.5}
                    />
                    {buyCost && (
                      <ReferenceLine
                        y={buyCost}
                        stroke="#EF4444"
                        strokeDasharray="5 5"
                        label={{ value: `Buy: $${buyCost}`, position: 'right' }}
                      />
                    )}
                  </>
                ) : (
                  <Line
                    type="monotone"
                    dataKey="sales_rank"
                    name="Sales Rank"
                    stroke={COLORS.sales_rank}
                    dot={true}
                    strokeWidth={2}
                  />
                )}
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <Box display="flex" justifyContent="center" alignItems="center" height="100%">
              <Typography color="text.secondary">
                No history data available
              </Typography>
            </Box>
          )}
        </Box>

        {/* Legend / Notes */}
        <Box mt={2} display="flex" gap={2} flexWrap="wrap">
          {analysis.sales_drops_30 && (
            <Chip 
              size="small" 
              label={`~${analysis.sales_drops_30} sales/month (est)`}
              color="primary"
              variant="outlined"
            />
          )}
          {analysis.fba_lowest_365d && (
            <Chip 
              size="small" 
              label={`365d Low: $${analysis.fba_lowest_365d.toFixed(2)}`}
              color="warning"
              variant="outlined"
            />
          )}
          {(analysis.total_seller_count || analysis.fba_seller_count) && (
            <Chip 
              size="small" 
              label={`${analysis.total_seller_count || analysis.fba_seller_count} sellers`}
              variant="outlined"
            />
          )}
        </Box>
      </CardContent>
    </Card>
  );
};

export default PriceHistoryChart;

