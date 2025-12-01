import { useState } from 'react';
import { Box, Typography, TextField, Button, Card, CardContent, RadioGroup, FormControlLabel, Radio, Select, MenuItem, FormControl, InputLabel } from '@mui/material';
import { Zap } from 'lucide-react';
import { useAnalysis } from '../hooks/useAnalysis';
import { useSuppliers } from '../hooks/useSuppliers';

const Analyze = () => {
  const [mode, setMode] = useState('single');
  const [asin, setAsin] = useState('');
  const [buyCost, setBuyCost] = useState('');
  const [moq, setMoq] = useState(1);
  const [supplierId, setSupplierId] = useState('');
  const { analyzeSingle, loading } = useAnalysis();
  const { suppliers } = useSuppliers();

  const handleAnalyze = async () => {
    if (!asin || !buyCost) return;
    try {
      const result = await analyzeSingle(asin, parseFloat(buyCost), moq, supplierId || null);
      console.log('Analysis result:', result);
      // TODO: Show result or navigate to deal
    } catch (error) {
      console.error('Analysis failed:', error);
    }
  };

  return (
    <Box>
      <Typography variant="h4" fontWeight={700} mb={1}>
        Analyze Products
      </Typography>
      <Typography variant="body1" color="text.secondary" mb={4}>
        Enter an ASIN to get instant profitability analysis
      </Typography>

      <Card sx={{ mb: 4 }}>
        <CardContent>
          <Box display="flex" flexDirection="column" gap={3}>
            <RadioGroup value={mode} onChange={(e) => setMode(e.target.value)} row>
              <FormControlLabel value="single" control={<Radio />} label="Single ASIN" />
              <FormControlLabel value="bulk" control={<Radio />} label="Bulk Analysis" />
            </RadioGroup>

            <Box display="flex" gap={2}>
              <TextField
                fullWidth
                label="ASIN"
                placeholder="B08XYZ1234"
                value={asin}
                onChange={(e) => setAsin(e.target.value.toUpperCase())}
                sx={{ fontFamily: 'monospace' }}
              />
              <Button
                variant="contained"
                startIcon={<Zap size={16} />}
                onClick={handleAnalyze}
                disabled={loading || !asin || !buyCost}
                sx={{
                  backgroundColor: '#7C6AFA',
                  '&:hover': { backgroundColor: '#5B4AD4' },
                  minWidth: 150,
                }}
              >
                {loading ? 'Analyzing...' : 'Analyze'}
              </Button>
            </Box>

            <Box display="flex" gap={2}>
              <TextField
                label="Your Cost"
                type="number"
                value={buyCost}
                onChange={(e) => setBuyCost(e.target.value)}
                InputProps={{ startAdornment: '$' }}
                sx={{ flex: 1 }}
              />
              <TextField
                label="MOQ"
                type="number"
                value={moq}
                onChange={(e) => setMoq(parseInt(e.target.value) || 1)}
                sx={{ flex: 1 }}
              />
              <FormControl sx={{ flex: 1 }}>
                <InputLabel>Supplier</InputLabel>
                <Select
                  value={supplierId}
                  label="Supplier"
                  onChange={(e) => setSupplierId(e.target.value)}
                >
                  <MenuItem value="">None</MenuItem>
                  {suppliers.map((s) => (
                    <MenuItem key={s.id} value={s.id}>
                      {s.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Box>
          </Box>
        </CardContent>
      </Card>

      <Typography variant="h6" fontWeight={600} mb={2}>
        📋 Recent Analyses
      </Typography>
      <Typography color="text.secondary">No recent analyses</Typography>
    </Box>
  );
};

export default Analyze;

