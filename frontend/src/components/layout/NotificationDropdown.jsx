import { Popover, Box, Typography, List, ListItem, ListItemText, Button, Divider } from '@mui/material';
import { useNotifications } from '../../context/NotificationContext';
import { formatTimeAgo } from '../../utils/formatters';
import { useNavigate } from 'react-router-dom';

const NotificationDropdown = ({ anchorEl, open, onClose }) => {
  const { notifications, markAsRead, markAllAsRead } = useNotifications();
  const navigate = useNavigate();

  const handleNotificationClick = (notification) => {
    if (!notification.is_read) {
      markAsRead(notification.id);
    }
    if (notification.deal_id) {
      navigate(`/deals/${notification.deal_id}`);
    }
    onClose();
  };

  return (
    <Popover
      open={open}
      anchorEl={anchorEl}
      onClose={onClose}
      anchorOrigin={{
        vertical: 'bottom',
        horizontal: 'right',
      }}
      transformOrigin={{
        vertical: 'top',
        horizontal: 'right',
      }}
      PaperProps={{
        sx: {
          width: 360,
          maxHeight: 500,
          mt: 1,
        },
      }}
    >
      <Box p={2}>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Typography variant="h6" fontWeight={600}>
            Notifications
          </Typography>
          {notifications.length > 0 && (
            <Button size="small" onClick={markAllAsRead}>
              Mark all read
            </Button>
          )}
        </Box>

        <Divider />

        {notifications.length === 0 ? (
          <Box py={4} textAlign="center">
            <Typography variant="body2" color="text.secondary">
              No notifications
            </Typography>
          </Box>
        ) : (
          <List sx={{ maxHeight: 400, overflow: 'auto' }}>
            {notifications.slice(0, 10).map((notification) => (
              <ListItem
                key={notification.id}
                button
                onClick={() => handleNotificationClick(notification)}
                sx={{
                  backgroundColor: notification.is_read ? 'transparent' : '#F3F4F6',
                  '&:hover': {
                    backgroundColor: '#E5E7EB',
                  },
                  mb: 0.5,
                  borderRadius: 1,
                }}
              >
                <ListItemText
                  primary={
                    <Typography variant="body2" fontWeight={notification.is_read ? 400 : 600}>
                      {notification.title}
                    </Typography>
                  }
                  secondary={
                    <Box>
                      <Typography variant="caption" color="text.secondary">
                        {notification.message}
                      </Typography>
                      <Typography variant="caption" color="text.secondary" display="block" mt={0.5}>
                        {formatTimeAgo(notification.created_at)}
                      </Typography>
                    </Box>
                  }
                />
              </ListItem>
            ))}
          </List>
        )}
      </Box>
    </Popover>
  );
};

export default NotificationDropdown;

