import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  ToggleButton,
  ToggleButtonGroup,
  CircularProgress,
  Alert,
  Chip,
  Grid,
  Skeleton,
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
import { useKeepa } from '../../../hooks/useKeepa';
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
  onDataLoaded 
}) => {
  const [chartType, setChartType] = useState('price');
  const [period, setPeriod] = useState(90);
  const [data, setData] = useState(null);
  
  const { getProduct, loading, error } = useKeepa();

  const loadingRef = useRef(false);

  useEffect(() => {
    if (asin && !loadingRef.current) {
      loadData();
    }
  }, [asin, period]);

  const loadData = async () => {
    if (loadingRef.current) return; // Prevent duplicate calls
    loadingRef.current = true;
    
    try {
      const result = await getProduct(asin, period);
      setData(result);
      
      if (onDataLoaded) {
        onDataLoaded(result);
      }
    } catch (err) {
      // Silently handle 404s - Keepa data just isn't available for this ASIN
      if (err.response?.status === 404) {
        console.log(`Keepa data not available for ${asin} (this is normal)`);
      } else {
        console.error('Failed to load Keepa data:', err);
      }
    } finally {
      loadingRef.current = false;
    }
  };

  // Transform data for Recharts
  const getChartData = () => {
    if (!data) return [];

    const history = chartType === 'price' 
      ? data.price_history 
      : data.rank_history;

    if (!history) return [];

    // Combine all series into single data points by timestamp
    const dataMap = new Map();

    Object.entries(history).forEach(([type, points]) => {
      if (!points) return;
      
      points.forEach(point => {
        const date = point.timestamp.split('T')[0]; // Group by date
        
        if (!dataMap.has(date)) {
          dataMap.set(date, { date });
        }
        
        const existing = dataMap.get(date);
        // Take last value for each day
        existing[type] = point.value;
      });
    });

    // Convert to array and sort by date
    return Array.from(dataMap.values())
      .sort((a, b) => new Date(a.date) - new Date(b.date));
  };

  const chartData = getChartData();

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

  // Stats display
  const renderStats = () => {
    if (!data) return null;

    const current = data.current || {};
    const avg = data.averages?.avg_90 || {};
    const drops = data.drops || {};

    return (
      <Grid container spacing={2} sx={{ mb: 2 }}>
        <Grid item xs={6} sm={3}>
          <Box>
            <Typography variant="caption" color="text.secondary">
              Current Price
            </Typography>
            <Typography variant="h6">
              ${current.buy_box_price?.toFixed(2) || current.new_fba_price?.toFixed(2) || 'N/A'}
            </Typography>
          </Box>
        </Grid>
        <Grid item xs={6} sm={3}>
          <Box>
            <Typography variant="caption" color="text.secondary">
              90-Day Avg
            </Typography>
            <Typography variant="h6">
              ${avg.buy_box?.toFixed(2) || avg.new?.toFixed(2) || 'N/A'}
            </Typography>
          </Box>
        </Grid>
        <Grid item xs={6} sm={3}>
          <Box>
            <Typography variant="caption" color="text.secondary">
              Sales Rank
            </Typography>
            <Typography variant="h6">
              {current.sales_rank?.toLocaleString() || 'N/A'}
            </Typography>
          </Box>
        </Grid>
        <Grid item xs={6} sm={3}>
          <Box>
            <Typography variant="caption" color="text.secondary">
              Est. Monthly Sales
            </Typography>
            <Typography variant="h6">
              ~{drops.drops_30 || 'N/A'}
            </Typography>
          </Box>
        </Grid>
      </Grid>
    );
  };

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 2 }}>
        {error}
      </Alert>
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
        {loading ? (
          <Grid container spacing={2} sx={{ mb: 2 }}>
            {[1, 2, 3, 4].map(i => (
              <Grid item xs={6} sm={3} key={i}>
                <Skeleton variant="text" width={60} />
                <Skeleton variant="text" width={80} height={32} />
              </Grid>
            ))}
          </Grid>
        ) : (
          renderStats()
        )}

        {/* Chart */}
        <Box height={300}>
          {loading ? (
            <Box display="flex" justifyContent="center" alignItems="center" height="100%">
              <CircularProgress />
            </Box>
          ) : chartData.length > 0 ? (
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
                      name="Buy Box"
                      stroke={COLORS.buy_box}
                      dot={false}
                      strokeWidth={2}
                    />
                    <Line
                      type="monotone"
                      dataKey="new_fba"
                      name="FBA"
                      stroke={COLORS.new_fba}
                      dot={false}
                      strokeWidth={1.5}
                    />
                    <Line
                      type="monotone"
                      dataKey="amazon"
                      name="Amazon"
                      stroke={COLORS.amazon}
                      dot={false}
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
                    dot={false}
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
          {data?.drops?.drops_30 && (
            <Chip 
              size="small" 
              label={`~${data.drops.drops_30} sales/month`}
              color="primary"
              variant="outlined"
            />
          )}
          {data?.oos?.oos_30 > 0 && (
            <Chip 
              size="small" 
              label={`${data.oos.oos_30}% OOS (30d)`}
              color="warning"
              variant="outlined"
            />
          )}
          {data?.current?.offer_count_new && (
            <Chip 
              size="small" 
              label={`${data.current.offer_count_new} sellers`}
              variant="outlined"
            />
          )}
        </Box>
      </CardContent>
    </Card>
  );
};

export default PriceHistoryChart;

