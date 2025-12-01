import { Chip } from '@mui/material';
import { Unlock, Lock, AlertTriangle } from 'lucide-react';
import { habexa } from '../../theme';

const GatingBadge = ({ status }) => {
  const getConfig = () => {
    switch (status) {
      case 'ungated':
        return {
          label: 'Ungated',
          icon: <Unlock size={12} />,
          color: habexa.success.main,
          bgColor: habexa.success.light,
        };
      case 'gated':
        return {
          label: 'Gated',
          icon: <Lock size={12} />,
          color: habexa.error.main,
          bgColor: habexa.error.light,
        };
      case 'approval_required':
        return {
          label: 'Approval Needed',
          icon: <AlertTriangle size={12} />,
          color: habexa.warning.main,
          bgColor: habexa.warning.light,
        };
      case 'amazon_restricted':
        return {
          label: 'Amazon Selling',
          icon: <AlertTriangle size={12} />,
          color: habexa.warning.main,
          bgColor: habexa.warning.light,
        };
      default:
        return {
          label: 'Unknown',
          icon: null,
          color: habexa.gray[500],
          bgColor: habexa.gray[100],
        };
    }
  };

  const config = getConfig();

  return (
    <Chip
      label={config.label}
      icon={config.icon}
      size="small"
      sx={{
        backgroundColor: config.bgColor,
        color: config.color,
        fontWeight: 500,
        fontSize: '0.75rem',
        '& .MuiChip-icon': {
          color: config.color,
        },
      }}
    />
  );
};

export default GatingBadge;

