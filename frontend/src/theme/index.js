// Habexa Brand Design System - Redesigned
import { createTheme } from '@mui/material/styles';

const habexa = {
  // Primary Brand Colors
  purple: {
    main: '#7C3AED',      // Vibrant Purple
    light: '#A78BFA',     // Primary Light
    dark: '#5B21B6',      // Primary Dark
  },
  navy: {
    main: '#1A1A2E',      // Surface (Card backgrounds)
    light: '#252540',     // Surface Elevated (Hover states)
    dark: '#0F0F1A',      // Background (Dark Navy/Black)
  },
  
  // Semantic Colors
  success: {
    main: '#10B981',      // Success Green
    light: 'rgba(16, 185, 129, 0.1)',
    dark: '#059669',
  },
  warning: {
    main: '#F59E0B',      // Warning/Highlight Orange
    light: 'rgba(245, 158, 11, 0.1)',
    dark: '#D97706',
  },
  error: {
    main: '#EF4444',      // Error Red
    light: 'rgba(239, 68, 68, 0.1)',
    dark: '#DC2626',
  },
  
  // Neutrals (Dark Mode)
  gray: {
    50: '#0F0F1A',        // Background
    100: '#1A1A2E',       // Surface
    200: '#252540',       // Surface Elevated
    300: '#2D2D3D',       // Border
    400: '#6B6B7B',       // Text Muted
    500: '#A0A0B0',       // Text Secondary
    600: '#FFFFFF',       // Text Primary
  },
};

export const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: habexa.purple.main,
      light: habexa.purple.light,
      dark: habexa.purple.dark,
    },
    secondary: {
      main: habexa.success.main,
    },
    success: {
      main: habexa.success.main,
    },
    warning: {
      main: habexa.warning.main,
    },
    error: {
      main: habexa.error.main,
    },
    background: {
      default: habexa.navy.dark,  // #0F0F1A
      paper: habexa.navy.main,    // #1A1A2E
    },
    text: {
      primary: habexa.gray[600],   // #FFFFFF
      secondary: habexa.gray[500],  // #A0A0B0
    },
    divider: habexa.gray[300],     // #2D2D3D
  },
  typography: {
    fontFamily: '"Inter", "Helvetica", "Arial", sans-serif',
    h4: {
      fontWeight: 700,
    },
    h5: {
      fontWeight: 700,
    },
    h6: {
      fontWeight: 600,
    },
  },
  shape: {
    borderRadius: 8,
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 600,
          borderRadius: 8,
        },
        contained: {
          boxShadow: 'none',
          '&:hover': {
            boxShadow: '0 4px 12px rgba(124, 58, 237, 0.4)',
          },
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundColor: habexa.navy.main,
          border: `1px solid ${habexa.gray[300]}`,
          borderRadius: 12,
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 6,
        },
      },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-notchedOutline': {
            borderColor: habexa.gray[300],
          },
          '&:hover .MuiOutlinedInput-notchedOutline': {
            borderColor: habexa.purple.main,
          },
          '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
            borderColor: habexa.purple.main,
          },
        },
      },
    },
  },
});

export { habexa };
export default theme;

