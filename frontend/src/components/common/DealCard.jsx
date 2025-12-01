import { Card, CardContent, Box, Typography, Chip, IconButton } from '@mui/material';
import { Package, Star, ExternalLink, TrendingUp } from 'lucide-react';
import { formatCurrency, formatROI } from '../../utils/formatters';
import GatingBadge from './GatingBadge';

const DealCard = ({ deal, onView, onMessage, onSave, onDismiss }) => {
  const isProfitable = deal.roi >= 30;

  return (
    <Card
      sx={{
        p: 0,
        overflow: 'hidden',
        transition: 'all 0.2s ease',
        cursor: 'pointer',
        '&:hover': {
          transform: 'translateY(-2px)',
          boxShadow: '0 8px 24px rgba(0, 0, 0, 0.3)',
          borderColor: '#7C3AED',
        },
      }}
      onClick={() => onView && onView(deal)}
    >
      <Box sx={{ display: 'flex' }}>
        {/* Product Image */}
        <Box
          sx={{
            width: 120,
            minHeight: 120,
            bgcolor: '#252540',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}
        >
          {deal.image_url ? (
            <img 
              src={deal.image_url} 
              alt={deal.title || deal.asin} 
              style={{ width: '100%', height: '100%', objectFit: 'cover' }} 
            />
          ) : (
            <Package size={40} style={{ color: '#6B6B7B' }} />
          )}
        </Box>

        {/* Content */}
        <Box sx={{ flex: 1, p: 2 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
            <Typography variant="body2" color="text.secondary" fontFamily="monospace">
              {deal.asin}
            </Typography>
            
            {/* Gating Badge */}
            <GatingBadge status={deal.gating_status} />
          </Box>

          <Typography variant="body1" fontWeight="600" color="white" noWrap mb={1}>
            {deal.title || 'Untitled Product'}
          </Typography>

          {/* Stats Row */}
          <Box sx={{ display: 'flex', gap: 3 }}>
            <Box>
              <Typography variant="caption" color="text.secondary">Buy</Typography>
              <Typography variant="body2" fontWeight="600" color="white">
                {formatCurrency(deal.buy_cost)}
              </Typography>
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary">Sell</Typography>
              <Typography variant="body2" fontWeight="600" color="white">
                {formatCurrency(deal.sell_price)}
              </Typography>
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary">Profit</Typography>
              <Typography variant="body2" fontWeight="600" color="success.main">
                {formatCurrency(deal.net_profit)}
              </Typography>
            </Box>
            <Box>
              <Typography variant="caption" color="text.secondary">ROI</Typography>
              <Typography 
                variant="body2" 
                fontWeight="700" 
                sx={{ 
                  color: isProfitable ? '#10B981' : '#F59E0B',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 0.5
                }}
              >
                {isProfitable && <TrendingUp size={14} />}
                {formatROI(deal.roi)}
              </Typography>
            </Box>
          </Box>
        </Box>

        {/* Actions */}
        <Box sx={{ p: 2, display: 'flex', flexDirection: 'column', gap: 1, borderLeft: '1px solid #2D2D3D' }}>
          <IconButton 
            size="small" 
            sx={{ color: '#A0A0B0', '&:hover': { color: '#7C3AED' } }}
            onClick={(e) => {
              e.stopPropagation();
              window.open(`https://www.amazon.com/dp/${deal.asin}`, '_blank');
            }}
          >
            <ExternalLink size={18} />
          </IconButton>
          {onSave && (
            <IconButton 
              size="small" 
              sx={{ color: '#A0A0B0', '&:hover': { color: '#7C3AED' } }}
              onClick={(e) => {
                e.stopPropagation();
                onSave(deal);
              }}
            >
              <Star size={18} />
            </IconButton>
          )}
        </Box>
      </Box>
    </Card>
  );
};

export default DealCard;

