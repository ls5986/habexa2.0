import { Box, Typography, Tooltip } from '@mui/material';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { habexa } from '../../../theme';

const SalesEstimate = ({ drops30, drops90, rank, category }) => {
  // Estimate velocity category
  const getVelocity = () => {
    if (!drops30) return 'unknown';
    if (drops30 >= 100) return 'high';
    if (drops30 >= 30) return 'medium';
    if (drops30 >= 10) return 'low';
    return 'very_low';
  };

  const velocity = getVelocity();
  
  const velocityConfig = {
    high: { color: habexa.success.main, icon: TrendingUp, label: 'High Velocity' },
    medium: { color: habexa.primary.main, icon: TrendingUp, label: 'Medium Velocity' },
    low: { color: habexa.warning.main, icon: Minus, label: 'Low Velocity' },
    very_low: { color: habexa.error.main, icon: TrendingDown, label: 'Very Low' },
    unknown: { color: habexa.gray[500], icon: Minus, label: 'Unknown' },
  };

  const config = velocityConfig[velocity];
  const Icon = config.icon;

  // Calculate trend (90d vs 30d extrapolated)
  const trend = drops90 && drops30 
    ? ((drops30 * 3) / drops90 - 1) * 100 
    : null;

  return (
    <Box>
      <Box display="flex" alignItems="center" gap={1} mb={1}>
        <Icon size={20} style={{ color: config.color }} />
        <Typography variant="subtitle2" sx={{ color: config.color }} fontWeight={600}>
          {config.label}
        </Typography>
      </Box>

      <Box display="flex" gap={3}>
        <Tooltip title="Estimated sales based on BSR drops in last 30 days">
          <Box>
            <Typography variant="caption" color="text.secondary">
              Monthly Sales
            </Typography>
            <Typography variant="h6">
              ~{drops30 || '?'}
            </Typography>
          </Box>
        </Tooltip>

        <Tooltip title="Current Best Sellers Rank">
          <Box>
            <Typography variant="caption" color="text.secondary">
              BSR
            </Typography>
            <Typography variant="h6">
              {rank?.toLocaleString() || '?'}
            </Typography>
          </Box>
        </Tooltip>

        {trend !== null && (
          <Tooltip title="Sales trend (30d vs 90d average)">
            <Box>
              <Typography variant="caption" color="text.secondary">
                Trend
              </Typography>
              <Typography 
                variant="h6"
                sx={{ 
                  color: trend > 0 ? habexa.success.main : trend < 0 ? habexa.error.main : 'text.primary' 
                }}
              >
                {trend > 0 ? '+' : ''}{trend.toFixed(0)}%
              </Typography>
            </Box>
          </Tooltip>
        )}
      </Box>

      {category && (
        <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
          in {category}
        </Typography>
      )}
    </Box>
  );
};

export default SalesEstimate;

