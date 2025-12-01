import { Chip } from '@mui/material';
import { CheckCircle, AlertCircle, XCircle } from 'lucide-react';
import { habexa } from '../../theme';

const StatusBadge = ({ status, roi, minRoi = 20 }) => {
  const getStatusConfig = () => {
    if (status === 'dismissed' || (roi !== null && roi < 0)) {
      return {
        label: 'Unprofitable',
        color: habexa.error.main,
        bgColor: habexa.error.light,
        icon: <XCircle size={14} />,
      };
    }
    
    if (status === 'saved') {
      return {
        label: 'Saved',
        color: habexa.purple.main,
        bgColor: habexa.purple.lighter,
        icon: null,
      };
    }
    
    if (status === 'ordered') {
      return {
        label: 'Ordered',
        color: habexa.success.main,
        bgColor: habexa.success.light,
        icon: <CheckCircle size={14} />,
      };
    }
    
    if (roi !== null && roi >= minRoi) {
      return {
        label: 'Profitable',
        color: habexa.success.main,
        bgColor: habexa.success.light,
        icon: <CheckCircle size={14} />,
      };
    }
    
    return {
      label: 'Review',
      color: habexa.warning.main,
      bgColor: habexa.warning.light,
      icon: <AlertCircle size={14} />,
    };
  };

  const config = getStatusConfig();

  return (
    <Chip
      label={config.label}
      icon={config.icon}
      size="small"
      sx={{
        backgroundColor: config.bgColor,
        color: config.color,
        fontWeight: 600,
        '& .MuiChip-icon': {
          color: config.color,
        },
      }}
    />
  );
};

export default StatusBadge;

