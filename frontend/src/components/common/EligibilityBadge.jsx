import { Chip, Tooltip, CircularProgress } from '@mui/material';
import { CheckCircle, X, HelpCircle, AlertTriangle } from 'lucide-react';
import { habexa } from '../../theme';

const STATUS_CONFIG = {
  ELIGIBLE: {
    label: 'Ungated',
    color: 'success',
    icon: <CheckCircle size={16} />,
    tooltip: 'You can list this product',
  },
  NOT_ELIGIBLE: {
    label: 'Gated',
    color: 'error',
    icon: <X size={16} />,
    tooltip: 'You cannot list this product',
  },
  APPROVAL_REQUIRED: {
    label: 'Approval Needed',
    color: 'warning',
    icon: <AlertTriangle size={16} />,
    tooltip: 'You need to apply for approval to list this product',
  },
  UNKNOWN: {
    label: 'Unknown',
    color: 'default',
    icon: <HelpCircle size={16} />,
    tooltip: 'Could not determine eligibility',
  },
  CHECKING: {
    label: 'Checking...',
    color: 'default',
    icon: <CircularProgress size={14} />,
    tooltip: 'Checking eligibility with Amazon',
  },
  NOT_CONNECTED: {
    label: 'Connect Amazon',
    color: 'default',
    icon: <HelpCircle size={16} />,
    tooltip: 'Connect your Amazon account to check eligibility',
  },
};

const EligibilityBadge = ({ 
  status, 
  size = 'small',
  showIcon = true,
  onClick 
}) => {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.UNKNOWN;
  
  return (
    <Tooltip title={config.tooltip}>
      <Chip
        label={config.label}
        color={config.color}
        size={size}
        icon={showIcon ? config.icon : undefined}
        onClick={onClick}
        sx={{ 
          cursor: onClick ? 'pointer' : 'default',
          '& .MuiChip-icon': { ml: 0.5 }
        }}
      />
    </Tooltip>
  );
};

export default EligibilityBadge;

