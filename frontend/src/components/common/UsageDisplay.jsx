import { Box, Typography, LinearProgress, Chip, Tooltip } from '@mui/material';
import { Infinity as InfinityIcon } from 'lucide-react';
import { habexa } from '../../theme';

const UsageDisplay = ({ 
  label, 
  used, 
  limit, 
  showBar = true,
  size = 'medium',
  onLimitClick
}) => {
  const isUnlimited = limit === -1;
  const percentage = isUnlimited ? 0 : Math.min(100, (used / limit) * 100);
  const remaining = isUnlimited ? Infinity : Math.max(0, limit - used);
  
  const getColor = () => {
    if (isUnlimited) return 'success';
    if (percentage >= 100) return 'error';
    if (percentage >= 80) return 'warning';
    return 'primary';
  };

  const sizeStyles = {
    small: { fontSize: '0.75rem', barHeight: 4 },
    medium: { fontSize: '0.875rem', barHeight: 6 },
    large: { fontSize: '1rem', barHeight: 8 },
  };

  const styles = sizeStyles[size];

  return (
    <Box sx={{ width: '100%' }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={0.5}>
        <Typography variant="body2" sx={{ fontSize: styles.fontSize }}>
          {label}
        </Typography>
        
        <Tooltip title={isUnlimited ? 'Unlimited' : `${remaining} remaining`}>
          <Box display="flex" alignItems="center" gap={0.5}>
            {isUnlimited ? (
              <Chip 
                icon={<InfinityIcon size={14} />}
                label="Unlimited"
                size="small"
                sx={{ 
                  height: 20, 
                  fontSize: '0.7rem',
                  backgroundColor: habexa.success.light,
                  color: habexa.success.main,
                }}
              />
            ) : (
              <Typography 
                variant="body2" 
                fontWeight={600}
                color={getColor() === 'error' ? habexa.error.main : getColor() === 'warning' ? habexa.warning.main : habexa.purple.main}
                sx={{ fontSize: styles.fontSize, cursor: onLimitClick ? 'pointer' : 'default' }}
                onClick={onLimitClick}
              >
                {used} / {limit}
              </Typography>
            )}
          </Box>
        </Tooltip>
      </Box>

      {showBar && !isUnlimited && (
        <LinearProgress
          variant="determinate"
          value={percentage}
          sx={{ 
            height: styles.barHeight, 
            borderRadius: styles.barHeight / 2,
            bgcolor: habexa.gray[200],
            '& .MuiLinearProgress-bar': {
              backgroundColor: getColor() === 'error' ? habexa.error.main : getColor() === 'warning' ? habexa.warning.main : habexa.purple.main,
            }
          }}
        />
      )}
    </Box>
  );
};

export default UsageDisplay;

