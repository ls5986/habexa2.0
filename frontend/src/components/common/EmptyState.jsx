import { Box, Typography, Button } from '@mui/material';
import { Inbox } from 'lucide-react';

const EmptyState = ({ icon: Icon = Inbox, title, message, actionLabel, onAction }) => {
  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        py: 10,
        px: 4,
        borderRadius: 3,
        bgcolor: '#1A1A2E',
        border: '1px dashed #2D2D3D',
      }}
    >
      <Box
        sx={{
          width: 80,
          height: 80,
          borderRadius: '50%',
          bgcolor: 'rgba(124, 58, 237, 0.1)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          mb: 3,
        }}
      >
        <Icon size={40} style={{ color: '#7C3AED' }} />
      </Box>
      
      <Typography variant="h6" fontWeight="600" color="white" gutterBottom>
        {title}
      </Typography>
      
      <Typography variant="body2" color="text.secondary" textAlign="center" maxWidth={400} mb={3}>
        {message}
      </Typography>
      
      {actionLabel && onAction && (
        <Button
          variant="contained"
          onClick={onAction}
          sx={{ background: 'linear-gradient(135deg, #7C3AED 0%, #5B21B6 100%)' }}
        >
          {actionLabel}
        </Button>
      )}
    </Box>
  );
};

export default EmptyState;

