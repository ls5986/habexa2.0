import { Box, Typography, Button } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { habexa } from '../theme';

const NotFound = () => {
  const navigate = useNavigate();

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        bgcolor: 'background.default',
      }}
    >
      <Box sx={{ textAlign: 'center' }}>
        <Typography
          variant="h1"
          sx={{
            fontSize: { xs: '4rem', md: '6rem' },
            fontWeight: 800,
            color: habexa.purple.main,
            mb: 2,
          }}
        >
          404
        </Typography>
        <Typography variant="h4" fontWeight={600} mb={2}>
          Page Not Found
        </Typography>
        <Typography variant="body1" color="text.secondary" mb={4}>
          The page you're looking for doesn't exist or has been moved.
        </Typography>
        <Button
          variant="contained"
          onClick={() => navigate('/dashboard')}
          sx={{
            backgroundColor: habexa.purple.main,
            '&:hover': { backgroundColor: habexa.purple.dark },
            px: 4,
            py: 1.5,
          }}
        >
          Back to Dashboard
        </Button>
      </Box>
    </Box>
  );
};

export default NotFound;

