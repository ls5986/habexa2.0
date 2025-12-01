import { Box, IconButton, Badge, Avatar, Button } from '@mui/material';
import { Bell, Zap } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useNotifications } from '../../context/NotificationContext';
import { getInitials } from '../../utils/formatters';
import { useState } from 'react';
import NotificationDropdown from './NotificationDropdown';

const TopBar = ({ onQuickAnalyze }) => {
  const { user } = useAuth();
  const { unreadCount } = useNotifications();
  const [notificationAnchor, setNotificationAnchor] = useState(null);

  const handleNotificationClick = (event) => {
    setNotificationAnchor(event.currentTarget);
  };

  const handleNotificationClose = () => {
    setNotificationAnchor(null);
  };

  return (
    <Box
      sx={{
        height: 64,
        px: 3,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'flex-end',
        borderBottom: '1px solid #2D2D3D',
        bgcolor: '#0F0F1A',
      }}
    >
      {/* Quick Analyze Button */}
      <Button
        variant="contained"
        startIcon={<Zap size={18} />}
        onClick={onQuickAnalyze}
        sx={{
          mr: 2,
          background: 'linear-gradient(135deg, #7C3AED 0%, #5B21B6 100%)',
          '&:hover': {
            background: 'linear-gradient(135deg, #8B5CF6 0%, #6D28D9 100%)',
          },
        }}
      >
        Quick Analyze
      </Button>

      {/* Notifications */}
      <IconButton 
        sx={{ color: '#A0A0B0', mr: 1, '&:hover': { bgcolor: 'rgba(255, 255, 255, 0.1)' } }}
        onClick={handleNotificationClick}
      >
        <Badge badgeContent={unreadCount} sx={{ 
          '& .MuiBadge-badge': { 
            bgcolor: '#EF4444',
            color: '#FFFFFF',
          } 
        }}>
          <Bell size={20} />
        </Badge>
      </IconButton>

      <NotificationDropdown
        anchorEl={notificationAnchor}
        open={Boolean(notificationAnchor)}
        onClose={handleNotificationClose}
      />

      {/* Profile */}
      <IconButton sx={{ p: 0, ml: 1 }}>
        <Avatar
          sx={{
            width: 36,
            height: 36,
            bgcolor: '#7C3AED',
            fontSize: 14,
            fontWeight: 600,
          }}
        >
          {user?.user_metadata?.full_name
            ? getInitials(user.user_metadata.full_name)
            : user?.email?.[0]?.toUpperCase() || 'U'}
        </Avatar>
      </IconButton>
    </Box>
  );
};

export default TopBar;

