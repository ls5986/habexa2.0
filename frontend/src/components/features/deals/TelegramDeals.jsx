import React, { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  Button,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Chip,
  CircularProgress,
  IconButton,
  Tooltip,
  Alert,
  Divider,
} from '@mui/material';
import { MessageCircle, Refresh, Play, ExternalLink } from 'lucide-react';
import api from '../../../services/api';
import { useToast } from '../../../context/ToastContext';
// Simple time formatter
const formatTimeAgo = (dateString) => {
  if (!dateString) return 'Unknown';
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);
  
  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`;
  if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
  return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
};

const TelegramDeals = ({ onAnalyze }) => {
  const [deals, setDeals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState({});
  const { showToast } = useToast();

  useEffect(() => {
    fetchDeals();
    
    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchDeals, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchDeals = async () => {
    try {
      const response = await api.get('/integrations/telegram/deals/pending');
      setDeals(response.data.deals || []);
    } catch (error) {
      console.error('Failed to fetch deals:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyze = async (deal) => {
    if (!deal.buy_cost) {
      showToast('No price found for this deal', 'warning');
      return;
    }

    setAnalyzing(prev => ({ ...prev, [deal.id]: true }));
    
    try {
      // Use the onAnalyze callback if provided, otherwise call API directly
      if (onAnalyze) {
        await onAnalyze({
          asin: deal.asin,
          buy_cost: deal.buy_cost,
          moq: deal.moq || 1
        });
      } else {
        await api.post('/analyze/single', {
          asin: deal.asin,
          buy_cost: deal.buy_cost,
          moq: deal.moq || 1
        });
      }
      
      showToast(`Analyzed ${deal.asin}`, 'success');
      
      // Remove from pending list
      setDeals(prev => prev.filter(d => d.id !== deal.id));
    } catch (error) {
      showToast(error.response?.data?.detail || 'Analysis failed', 'error');
    } finally {
      setAnalyzing(prev => ({ ...prev, [deal.id]: false }));
    }
  };

  const handleAnalyzeAll = async () => {
    const dealsWithPrice = deals.filter(d => d.buy_cost);
    
    if (dealsWithPrice.length === 0) {
      showToast('No deals with prices to analyze', 'warning');
      return;
    }

    showToast(`Analyzing ${dealsWithPrice.length} deals...`, 'info');
    
    for (const deal of dealsWithPrice) {
      await handleAnalyze(deal);
      // Small delay to avoid rate limiting
      await new Promise(r => setTimeout(r, 500));
    }
  };

  if (loading) {
    return (
      <Card>
        <CardContent sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
          <CircularProgress />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent>
        <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
          <Box display="flex" alignItems="center" gap={1}>
            <MessageCircle size={20} style={{ color: '#0088cc' }} />
            <Typography variant="h6" fontWeight={600}>
              Telegram Deals
            </Typography>
            <Chip label={deals.length} size="small" color="primary" />
          </Box>
          
          <Box display="flex" gap={1}>
            <Tooltip title="Refresh">
              <IconButton onClick={fetchDeals} size="small">
                <Refresh size={18} />
              </IconButton>
            </Tooltip>
            {deals.length > 0 && (
              <Button
                size="small"
                variant="contained"
                startIcon={<Play size={18} />}
                onClick={handleAnalyzeAll}
              >
                Analyze All
              </Button>
            )}
          </Box>
        </Box>

        {deals.length > 0 ? (
          <List dense>
            {deals.map((deal) => (
              <React.Fragment key={deal.id}>
                <ListItem>
                  <ListItemText
                    primary={
                      <Box display="flex" alignItems="center" gap={1}>
                        <Typography variant="body2" fontWeight="bold" fontFamily="monospace">
                          {deal.asin}
                        </Typography>
                        {deal.buy_cost && (
                          <Chip 
                            label={`$${deal.buy_cost}`} 
                            size="small" 
                            color="success"
                          />
                        )}
                        {deal.moq > 1 && (
                          <Chip 
                            label={`MOQ: ${deal.moq}`} 
                            size="small" 
                            variant="outlined"
                          />
                        )}
                      </Box>
                    }
                    secondary={
                      <Box>
                        {deal.product_title && (
                          <Typography variant="caption" display="block" noWrap>
                            {deal.product_title}
                          </Typography>
                        )}
                        <Typography variant="caption" color="text.secondary">
                          {deal.telegram_channels?.channel_name} • {formatTimeAgo(deal.extracted_at)}
                        </Typography>
                      </Box>
                    }
                  />
                  <ListItemSecondaryAction>
                    <Box display="flex" gap={0.5}>
                      <Tooltip title="View on Amazon">
                        <IconButton
                          size="small"
                          href={`https://amazon.com/dp/${deal.asin}`}
                          target="_blank"
                        >
                          <ExternalLink size={18} />
                        </IconButton>
                      </Tooltip>
                      <Button
                        size="small"
                        variant="contained"
                        onClick={() => handleAnalyze(deal)}
                        disabled={analyzing[deal.id] || !deal.buy_cost}
                        startIcon={analyzing[deal.id] ? <CircularProgress size={14} /> : <Play size={18} />}
                      >
                        {analyzing[deal.id] ? 'Analyzing...' : 'Analyze'}
                      </Button>
                    </Box>
                  </ListItemSecondaryAction>
                </ListItem>
                <Divider />
              </React.Fragment>
            ))}
          </List>
        ) : (
          <Alert severity="info">
            No pending deals. Deals will appear here when extracted from your monitored channels.
          </Alert>
        )}
      </CardContent>
    </Card>
  );
};

export default TelegramDeals;

