import React from 'react';
import {
  Card,
  CardContent,
  CardHeader,
  FormControl,
  FormControlLabel,
  Radio,
  RadioGroup,
  Typography,
  Box,
  Alert,
  Button,
  Divider
} from '@mui/material';
import InfoIcon from '@mui/icons-material/Info';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';

export default function PricingModeToggle({ value, onChange }) {
  const handleModeChange = (event) => {
    onChange(event.target.value);
  };

  return (
    <Card sx={{ mb: 2 }}>
      <CardHeader
        title={
          <Box display="flex" alignItems="center" gap={1}>
            <TrendingUpIcon color="primary" />
            <Typography variant="h6">Pricing Analysis Mode</Typography>
          </Box>
        }
      />
      <CardContent>
        <Alert severity="info" icon={<InfoIcon />} sx={{ mb: 2 }}>
          <Typography variant="body2">
            Choose how to calculate profitability. Using averages provides more realistic 
            long-term projections and helps avoid price spike traps.
          </Typography>
        </Alert>

        <FormControl component="fieldset" fullWidth>
          <RadioGroup 
            value={value} 
            onChange={handleModeChange}
          >
            <FormControlLabel 
              value="current" 
              control={<Radio />} 
              label={
                <Box>
                  <Typography variant="body1" fontWeight="medium">
                    Current Buy Box Price
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Real-time price (may include temporary spikes/dips)
                  </Typography>
                </Box>
              }
              sx={{ mb: 1, py: 1 }}
            />
            
            <FormControlLabel 
              value="30d_avg" 
              control={<Radio />} 
              label={
                <Box>
                  <Typography variant="body1" fontWeight="medium">
                    30-Day Average
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Short-term average (good for trending products)
                  </Typography>
                </Box>
              }
              sx={{ mb: 1, py: 1 }}
            />
            
            <FormControlLabel 
              value="90d_avg" 
              control={<Radio />} 
              label={
                <Box>
                  <Typography variant="body1" fontWeight="medium">
                    90-Day Average
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Quarterly average (balanced view)
                  </Typography>
                </Box>
              }
              sx={{ mb: 1, py: 1 }}
            />
            
            <FormControlLabel 
              value="365d_avg" 
              control={<Radio />} 
              label={
                <Box>
                  <Box display="flex" alignItems="center" gap={1}>
                    <Typography variant="body1" fontWeight="bold">
                      365-Day Average
                    </Typography>
                    <Typography 
                      variant="caption" 
                      sx={{ 
                        bgcolor: 'success.main',
                        color: 'white',
                        px: 0.5,
                        py: 0.25,
                        borderRadius: 0.5,
                        fontWeight: 'bold'
                      }}
                    >
                      RECOMMENDED
                    </Typography>
                  </Box>
                  <Typography variant="caption" color="text.secondary">
                    Full year average (most accurate for long-term profitability)
                  </Typography>
                </Box>
              }
              sx={{ mb: 1, py: 1 }}
            />
          </RadioGroup>
        </FormControl>

        <Divider sx={{ my: 2 }} />

        <Box display="flex" gap={2}>
          <Button 
            variant="outlined" 
            onClick={() => onChange('current')}
            size="small"
          >
            Quick Scan (Current)
          </Button>
          <Button 
            variant="contained" 
            onClick={() => onChange('365d_avg')}
            size="small"
            color="success"
          >
            Conservative Analysis (365d) ⭐
          </Button>
        </Box>
      </CardContent>
    </Card>
  );
}

