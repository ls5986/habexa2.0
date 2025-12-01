// Calculation utilities

export const calculateProfit = (buyCost, sellPrice, fees = {}) => {
  const {
    fbaFee = 0,
    referralFee = 0,
    prepCost = 0.50,
    inboundShipping = 0.50,
  } = fees;

  const totalCost = buyCost + prepCost + inboundShipping;
  const totalFees = fbaFee + referralFee;
  const netPayout = sellPrice - totalFees;
  const netProfit = netPayout - totalCost;
  const roi = totalCost > 0 ? (netProfit / totalCost) * 100 : 0;
  const margin = sellPrice > 0 ? (netProfit / sellPrice) * 100 : 0;

  return {
    totalCost,
    totalFees,
    netPayout,
    netProfit,
    roi,
    margin,
    isProfitable: netProfit > 0,
  };
};

export const getStatusColor = (status, roi, minRoi = 20) => {
  if (status === 'dismissed') return 'error';
  if (status === 'saved') return 'info';
  if (status === 'ordered') return 'success';
  
  if (roi === null || roi === undefined) return 'warning';
  if (roi < 0) return 'error';
  if (roi >= minRoi) return 'success';
  return 'warning';
};

export const getStatusLabel = (status) => {
  const labels = {
    pending: 'Pending',
    analyzed: 'Analyzed',
    saved: 'Saved',
    ordered: 'Ordered',
    dismissed: 'Dismissed',
  };
  return labels[status] || status;
};

