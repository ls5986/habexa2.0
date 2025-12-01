import { Box, Drawer } from '@mui/material';
import { useState } from 'react';
import Sidebar from './Sidebar';
import TopBar from './TopBar';
import QuickAnalyzeModal from '../features/analyze/QuickAnalyzeModal';
import { useDeals } from '../../hooks/useDeals';

const AppLayout = ({ children }) => {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [quickAnalyzeOpen, setQuickAnalyzeOpen] = useState(false);
  const [selectedDealFromQuick, setSelectedDealFromQuick] = useState(null);
  const { deals } = useDeals({ limit: 1 });

  const handleQuickAnalyze = () => {
    setQuickAnalyzeOpen(true);
  };

  const handleViewDeal = (analysisResult) => {
    // Find the deal in the deals list or use the analysis result
    const deal = deals.find(d => d.asin === analysisResult.asin) || analysisResult;
    setSelectedDealFromQuick(deal);
    // This will be handled by the page that renders DealDetailPanel
  };

  return (
    <Box sx={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
      />
      <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <TopBar onQuickAnalyze={handleQuickAnalyze} />
        <Box
          component="main"
          sx={{
            flex: 1,
            overflow: 'auto',
            backgroundColor: '#0F0F1A',
            p: 3,
          }}
        >
          {children}
        </Box>
      </Box>
      <QuickAnalyzeModal
        open={quickAnalyzeOpen}
        onClose={() => setQuickAnalyzeOpen(false)}
        onViewDeal={handleViewDeal}
      />
    </Box>
  );
};

export default AppLayout;

