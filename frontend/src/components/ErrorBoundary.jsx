import React from 'react';
import { Box, Typography, Button } from '@mui/material';
import { AlertTriangle, Home } from 'lucide-react';
import { habexa } from '../theme';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Error caught by boundary:', error, errorInfo);
    this.setState({
      error,
      errorInfo,
    });
    // Optional: send to error tracking service
  }

  resetError = () => {
    // Reset error state - this will cause React to re-render children
    // React will attempt to render the component tree again
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <Box
          sx={{
            minHeight: '100vh',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            bgcolor: 'background.default',
            p: 3,
          }}
        >
          <Box sx={{ textAlign: 'center', maxWidth: 500 }}>
            <AlertTriangle size={48} style={{ color: habexa.error.main, margin: '0 auto 16px' }} />
            <Typography variant="h4" fontWeight={700} mb={2}>
              Something went wrong
            </Typography>
            <Typography variant="body1" color="text.secondary" mb={4}>
              We're sorry, an unexpected error occurred. You can try again or go to the dashboard.
            </Typography>
            {process.env.NODE_ENV === 'development' && this.state.error && (
              <Box
                sx={{
                  bgcolor: 'background.paper',
                  p: 2,
                  borderRadius: 2,
                  mb: 3,
                  textAlign: 'left',
                  maxHeight: 200,
                  overflow: 'auto',
                }}
              >
                <Typography variant="caption" fontFamily="monospace" color="error">
                  {this.state.error.toString()}
                  {this.state.errorInfo && (
                    <pre style={{ fontSize: '0.75rem', marginTop: 8 }}>
                      {this.state.errorInfo.componentStack}
                    </pre>
                  )}
                </Typography>
              </Box>
            )}
            <Box display="flex" gap={2} justifyContent="center">
              <Button
                variant="contained"
                onClick={this.resetError}
                startIcon={<Home size={16} />}
                sx={{
                  backgroundColor: habexa.purple.main,
                  '&:hover': { backgroundColor: habexa.purple.dark },
                  px: 4,
                  py: 1.5,
                }}
              >
                Try Again
              </Button>
              <Button
                variant="outlined"
                onClick={() => {
                  this.resetError();
                  window.location.href = '/dashboard';
                }}
                sx={{
                  px: 4,
                  py: 1.5,
                }}
              >
                Go to Dashboard
              </Button>
            </Box>
          </Box>
        </Box>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
