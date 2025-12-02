import React from 'react';
import { Box, Typography, Chip, LinearProgress, Tooltip } from '@mui/material';
import { 
  TrendingUp, TrendingDown, Package, Star, Users, 
  AlertTriangle, ShoppingCart, Award, Zap
} from 'lucide-react';

export default function MarketIntelligence({ deal, analysis, spApiOffers, spApiSalesEstimate }) {
  // Real data from SP-API
  const sellerCount = spApiOffers?.total_sellers || spApiOffers?.seller_count || 0;
  const fbaCount = spApiOffers?.fba_count || 0;
  const fbmCount = spApiOffers?.fbm_count || 0;
  const amazonSells = spApiOffers?.amazon_selling || false;
  const buyBoxPrice = spApiOffers?.buy_box_winner?.price || spApiOffers?.buy_box_price;
  const priceRange = {
    min: spApiOffers?.lowest_price,
    max: spApiOffers?.highest_price
  };
  
  // Sales estimate from SP-API
  const estimatedMonthlySales = spApiSalesEstimate?.est_monthly_sales || spApiSalesEstimate?.estimated_monthly_sales || 0;
  const salesRank = spApiSalesEstimate?.sales_rank || analysis?.sales_rank;
  
  // Fallback to analysis data
  const reviewCount = analysis?.review_count || 0;
  const rating = analysis?.rating || 0;
  const roi = analysis?.roi || deal?.roi || 0;
  const category = analysis?.category || spApiSalesEstimate?.category || 'Unknown';

  // Competition Level - Based on REAL seller count from SP-API
  const getCompetitionLevel = () => {
    if (amazonSells) return { level: 'Very High', color: '#EF4444', score: 95 };
    if (sellerCount === 0) return { level: 'Unknown', color: '#6B7280', score: 50 };
    if (sellerCount <= 3) return { level: 'Low', color: '#10B981', score: 20 };
    if (sellerCount <= 7) return { level: 'Medium', color: '#F59E0B', score: 50 };
    if (sellerCount <= 15) return { level: 'High', color: '#F97316', score: 75 };
    return { level: 'Very High', color: '#EF4444', score: 90 };
  };

  // Demand Score - Based on BSR and sales estimate
  const getDemandScore = () => {
    if (!salesRank) return 50;
    if (salesRank < 1000) return 100;
    if (salesRank < 5000) return 90;
    if (salesRank < 10000) return 80;
    if (salesRank < 25000) return 70;
    if (salesRank < 50000) return 60;
    if (salesRank < 100000) return 45;
    if (salesRank < 250000) return 30;
    return 15;
  };

  // Sales Velocity
  const getSalesVelocity = () => {
    if (estimatedMonthlySales >= 300) return { label: 'Very High', color: '#10B981' };
    if (estimatedMonthlySales >= 100) return { label: 'High', color: '#22C55E' };
    if (estimatedMonthlySales >= 30) return { label: 'Medium', color: '#F59E0B' };
    if (estimatedMonthlySales > 0) return { label: 'Low', color: '#EF4444' };
    return { label: 'Unknown', color: '#6B7280' };
  };

  // Opportunity Score - Combines ROI, demand, and competition
  const getOpportunityScore = () => {
    const demandScore = getDemandScore();
    const competition = getCompetitionLevel();
    const roiScore = Math.min(roi * 2, 100); // ROI of 50% = 100 score
    
    // Weight: ROI 40%, Demand 35%, Low Competition 25%
    const competitionBonus = 100 - competition.score;
    return Math.round((roiScore * 0.4) + (demandScore * 0.35) + (competitionBonus * 0.25));
  };

  const competition = getCompetitionLevel();
  const demandScore = getDemandScore();
  const opportunityScore = getOpportunityScore();
  const salesVelocity = getSalesVelocity();

  // Generate insights based on real data
  const getInsights = () => {
    const insights = [];
    
    if (amazonSells) {
      insights.push({
        type: 'danger',
        icon: AlertTriangle,
        text: 'Amazon is selling this product - difficult to win Buy Box'
      });
    }
    
    if (sellerCount > 0 && sellerCount <= 3 && !amazonSells) {
      insights.push({
        type: 'success',
        icon: Award,
        text: `Low competition - Only ${sellerCount} seller${sellerCount > 1 ? 's' : ''} on listing`
      });
    }
    
    if (fbaCount === 0 && sellerCount > 0) {
      insights.push({
        type: 'success',
        icon: Package,
        text: 'No FBA sellers - FBA advantage opportunity!'
      });
    }
    
    if (roi >= 30 && demandScore >= 70) {
      insights.push({
        type: 'success',
        icon: TrendingUp,
        text: 'Strong opportunity - High ROI with good demand'
      });
    }
    
    if (sellerCount > 10) {
      insights.push({
        type: 'warning',
        icon: Users,
        text: `Crowded listing - ${sellerCount} sellers competing`
      });
    }
    
    if (salesRank && salesRank > 100000) {
      insights.push({
        type: 'warning',
        icon: TrendingDown,
        text: 'Low demand - BSR over 100,000'
      });
    }
    
    if (estimatedMonthlySales >= 100) {
      insights.push({
        type: 'info',
        icon: Zap,
        text: `High velocity - Est. ${estimatedMonthlySales} units/month`
      });
    }
    
    return insights;
  };

  const insights = getInsights();

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h6" sx={{ mb: 3, display: 'flex', alignItems: 'center', gap: 1 }}>
        <TrendingUp size={20} />
        Market Intelligence
      </Typography>

      {/* Score Cards */}
      <Box sx={{ display: 'flex', gap: 3, mb: 4, flexWrap: 'wrap' }}>
        {/* Demand Score */}
        <Box sx={{ flex: 1, minWidth: 150 }}>
          <Typography variant="caption" color="text.secondary">Demand Score</Typography>
          <Typography variant="h5" fontWeight="700">{demandScore}/100</Typography>
          <LinearProgress 
            variant="determinate" 
            value={demandScore} 
            sx={{ 
              mt: 1, 
              height: 6, 
              borderRadius: 3,
              bgcolor: '#1a1a2e',
              '& .MuiLinearProgress-bar': { 
                bgcolor: demandScore >= 70 ? '#10B981' : demandScore >= 40 ? '#F59E0B' : '#EF4444' 
              }
            }} 
          />
        </Box>

        {/* Opportunity Score */}
        <Box sx={{ flex: 1, minWidth: 150 }}>
          <Typography variant="caption" color="text.secondary">Opportunity Score</Typography>
          <Typography variant="h5" fontWeight="700">{opportunityScore}/100</Typography>
          <LinearProgress 
            variant="determinate" 
            value={opportunityScore} 
            sx={{ 
              mt: 1, 
              height: 6, 
              borderRadius: 3,
              bgcolor: '#1a1a2e',
              '& .MuiLinearProgress-bar': { 
                bgcolor: opportunityScore >= 70 ? '#10B981' : opportunityScore >= 40 ? '#F59E0B' : '#EF4444' 
              }
            }} 
          />
        </Box>

        {/* Competition Level */}
        <Box sx={{ flex: 1, minWidth: 150 }}>
          <Typography variant="caption" color="text.secondary">Competition Level</Typography>
          <Chip 
            label={competition.level}
            sx={{ 
              mt: 0.5,
              bgcolor: `${competition.color}20`,
              color: competition.color,
              fontWeight: 600
            }}
          />
          {sellerCount > 0 && (
            <Typography variant="caption" display="block" color="text.secondary" sx={{ mt: 0.5 }}>
              {sellerCount} sellers ({fbaCount} FBA, {fbmCount} FBM)
            </Typography>
          )}
        </Box>
      </Box>

      {/* Key Metrics Grid */}
      <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 2 }}>
        KEY METRICS
      </Typography>
      
      <Box sx={{ 
        display: 'grid', 
        gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', 
        gap: 2,
        mb: 4
      }}>
        {/* Est. Monthly Sales */}
        <Box sx={{ 
          p: 2, 
          bgcolor: '#1a1a2e', 
          borderRadius: 2,
          textAlign: 'center'
        }}>
          <Package size={20} color="#8B5CF6" />
          <Typography variant="caption" display="block" color="text.secondary">
            Est. Monthly Sales
          </Typography>
          <Typography variant="h6" fontWeight="600">
            {estimatedMonthlySales > 0 ? estimatedMonthlySales.toLocaleString() : 'N/A'}
          </Typography>
          <Typography variant="caption" color="text.secondary">units/month</Typography>
        </Box>

        {/* Sales Velocity */}
        <Box sx={{ 
          p: 2, 
          bgcolor: '#1a1a2e', 
          borderRadius: 2,
          textAlign: 'center'
        }}>
          <TrendingUp size={20} color="#F59E0B" />
          <Typography variant="caption" display="block" color="text.secondary">
            Sales Velocity
          </Typography>
          <Typography variant="h6" fontWeight="600" color={salesVelocity.color}>
            {salesVelocity.label}
          </Typography>
        </Box>

        {/* Seller Count */}
        <Box sx={{ 
          p: 2, 
          bgcolor: '#1a1a2e', 
          borderRadius: 2,
          textAlign: 'center'
        }}>
          <Users size={20} color="#3B82F6" />
          <Typography variant="caption" display="block" color="text.secondary">
            Total Sellers
          </Typography>
          <Typography variant="h6" fontWeight="600">
            {sellerCount > 0 ? sellerCount : 'N/A'}
          </Typography>
          {sellerCount > 0 && (
            <Typography variant="caption" color="text.secondary">
              {fbaCount} FBA / {fbmCount} FBM
            </Typography>
          )}
        </Box>

        {/* Rating */}
        <Box sx={{ 
          p: 2, 
          bgcolor: '#1a1a2e', 
          borderRadius: 2,
          textAlign: 'center'
        }}>
          <Star size={20} color="#FBBF24" />
          <Typography variant="caption" display="block" color="text.secondary">
            Rating
          </Typography>
          <Typography variant="h6" fontWeight="600">
            {rating > 0 ? `${rating.toFixed(1)} ⭐` : 'N/A'}
          </Typography>
          {reviewCount > 0 && (
            <Typography variant="caption" color="text.secondary">
              {reviewCount.toLocaleString()} reviews
            </Typography>
          )}
        </Box>

        {/* BSR */}
        <Box sx={{ 
          p: 2, 
          bgcolor: '#1a1a2e', 
          borderRadius: 2,
          textAlign: 'center'
        }}>
          <Award size={20} color="#10B981" />
          <Typography variant="caption" display="block" color="text.secondary">
            BSR
          </Typography>
          <Typography variant="h6" fontWeight="600">
            {salesRank ? `#${salesRank.toLocaleString()}` : 'N/A'}
          </Typography>
          <Typography variant="caption" color="text.secondary" noWrap>
            {category}
          </Typography>
        </Box>

        {/* Buy Box Price */}
        <Box sx={{ 
          p: 2, 
          bgcolor: '#1a1a2e', 
          borderRadius: 2,
          textAlign: 'center'
        }}>
          <ShoppingCart size={20} color="#EC4899" />
          <Typography variant="caption" display="block" color="text.secondary">
            Buy Box Price
          </Typography>
          <Typography variant="h6" fontWeight="600">
            {buyBoxPrice ? `$${buyBoxPrice.toFixed(2)}` : 'N/A'}
          </Typography>
          {priceRange.min && priceRange.max && (
            <Typography variant="caption" color="text.secondary">
              ${priceRange.min.toFixed(2)} - ${priceRange.max.toFixed(2)}
            </Typography>
          )}
        </Box>
      </Box>

      {/* Amazon Warning */}
      {amazonSells && (
        <Box sx={{ 
          p: 2, 
          bgcolor: '#7F1D1D20', 
          border: '1px solid #EF4444',
          borderRadius: 2,
          mb: 3,
          display: 'flex',
          alignItems: 'center',
          gap: 2
        }}>
          <AlertTriangle size={24} color="#EF4444" />
          <Box>
            <Typography fontWeight="600" color="error.main">
              ⚠️ Amazon is Selling This Product
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Competing with Amazon makes it very difficult to win the Buy Box. Consider other products.
            </Typography>
          </Box>
        </Box>
      )}

      {/* Insights */}
      {insights.length > 0 && (
        <>
          <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 2 }}>
            INSIGHTS
          </Typography>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            {insights.map((insight, idx) => (
              <Box
                key={idx}
                sx={{
                  p: 1.5,
                  borderRadius: 2,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 1.5,
                  bgcolor: insight.type === 'success' ? '#10B98120' :
                           insight.type === 'warning' ? '#F59E0B20' :
                           insight.type === 'danger' ? '#EF444420' : '#3B82F620',
                  borderLeft: '3px solid',
                  borderColor: insight.type === 'success' ? '#10B981' :
                               insight.type === 'warning' ? '#F59E0B' :
                               insight.type === 'danger' ? '#EF4444' : '#3B82F6'
                }}
              >
                <insight.icon 
                  size={18} 
                  color={
                    insight.type === 'success' ? '#10B981' :
                    insight.type === 'warning' ? '#F59E0B' :
                    insight.type === 'danger' ? '#EF4444' : '#3B82F6'
                  } 
                />
                <Typography variant="body2">{insight.text}</Typography>
              </Box>
            ))}
          </Box>
        </>
      )}
    </Box>
  );
}
