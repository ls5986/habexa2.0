import { Box, Grid, Typography, Card, CardContent } from '@mui/material';
import { Inbox, CheckCircle, Clock, DollarSign, TrendingUp } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useDeals } from '../hooks/useDeals';
import StatCard from '../components/common/StatCard';
import DealCard from '../components/common/DealCard';
import UsageWidget from '../components/features/dashboard/UsageWidget';
import { useState } from 'react';
import { formatCurrency } from '../utils/formatters';

const Dashboard = () => {
  const { user } = useAuth();
  const { deals, loading } = useDeals({ limit: 50 });
  const [selectedDeal, setSelectedDeal] = useState(null);

  // Ensure deals is always an array
  const dealsArray = Array.isArray(deals) ? deals : 
                     Array.isArray(deals?.deals) ? deals.deals :
                     Array.isArray(deals?.data) ? deals.data :
                     [];

  // Calculate stats
  const newDeals = dealsArray.filter(d => d.status === 'pending' || d.status === 'analyzed').length;
  const profitable = dealsArray.filter(d => d.is_profitable && d.roi >= 20).length;
  const pending = dealsArray.filter(d => d.status === 'pending').length;
  const potentialProfit = dealsArray
    .filter(d => d.is_profitable && d.net_profit > 0)
    .reduce((sum, d) => sum + (d.net_profit * (d.moq || 1)), 0);

  const hotDeals = dealsArray
    .filter(d => d.is_profitable && d.roi >= 30)
    .sort((a, b) => (b.roi || 0) - (a.roi || 0))
    .slice(0, 3);

  const greeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 18) return 'Good afternoon';
    return 'Good evening';
  };

  const userName = user?.user_metadata?.full_name || user?.email?.split('@')[0] || 'there';

  return (
    <Box>
      <Box mb={4}>
        <Typography variant="h4" fontWeight={700} mb={1} sx={{ color: '#1a1a2e' }}>
          {greeting()}, {userName}! 👋
        </Typography>
        <Typography variant="body1" sx={{ color: '#666666' }}>
          Here's your deal flow for today.
        </Typography>
      </Box>

      {/* Stat Cards */}
      <Grid container spacing={3} mb={4}>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            icon={<Inbox size={16} />}
            label="NEW DEALS"
            value={newDeals}
            subtext="today"
            trend="23%"
            trendUp={true}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            icon={<CheckCircle size={16} />}
            label="PROFITABLE"
            value={profitable}
            subtext="ready to buy"
            trend="8%"
            trendUp={true}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            icon={<Clock size={16} />}
            label="PENDING"
            value={pending}
            subtext="need review"
            trend="12%"
            trendUp={false}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            icon={<DollarSign size={16} />}
            label="POTENTIAL"
            value={formatCurrency(potentialProfit)}
            subtext="est. profit"
            trend="15%"
            trendUp={true}
          />
        </Grid>
      </Grid>

      {/* Hot Deals and Activity */}
      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
                <Typography variant="h6" fontWeight={600}>
                  🔥 Hot Deals
                </Typography>
              </Box>
              {loading ? (
                <Typography>Loading...</Typography>
              ) : hotDeals.length > 0 ? (
                <Box display="flex" flexDirection="column" gap={2}>
                  {hotDeals.map((deal) => (
                    <DealCard
                      key={deal.id}
                      deal={deal}
                      onView={(deal) => setSelectedDeal(deal)}
                    />
                  ))}
                </Box>
              ) : (
                <Typography color="text.secondary">No hot deals yet</Typography>
              )}
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <UsageWidget />
        </Grid>
      </Grid>
    </Box>
  );
};

export default Dashboard;

