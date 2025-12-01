import { Card, CardContent, Typography, Box } from '@mui/material';
import { TrendingUp, TrendingDown } from 'lucide-react';

const StatCard = ({ icon, label, value, subtext, trend, trendUp }) => {
  return (
    <Card sx={{ height: '100%' }}>
      <CardContent>
        <Box display="flex" alignItems="center" gap={1} mb={2}>
          {icon}
          <Typography variant="body2" color="text.secondary">
            {label}
          </Typography>
        </Box>
        <Typography variant="h3" fontWeight={700} color="text.primary" mb={1}>
          {value}
        </Typography>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Typography variant="body2" color="text.secondary">
            {subtext}
          </Typography>
          {trend && (
            <Box
              display="flex"
              alignItems="center"
              gap={0.5}
              color={trendUp ? 'success.main' : 'error.main'}
            >
              {trendUp ? (
                <TrendingUp size={14} />
              ) : (
                <TrendingDown size={14} />
              )}
              <Typography variant="body2" fontWeight={600}>
                {trend}
              </Typography>
            </Box>
          )}
        </Box>
      </CardContent>
    </Card>
  );
};

export default StatCard;

