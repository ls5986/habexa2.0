import React, { createContext, useContext, useState, useEffect, useMemo } from 'react';
import { ThemeProvider as MUIThemeProvider } from '@mui/material/styles';
import { CssBaseline } from '@mui/material';
import { createTheme } from '@mui/material/styles';
import { habexa } from '../theme';

const ThemeContext = createContext();

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};

export const ThemeProvider = ({ children }) => {
  // Get initial mode from localStorage or default to 'dark'
  const [mode, setMode] = useState(() => {
    const saved = localStorage.getItem('habexa-theme-mode');
    return saved === 'light' ? 'light' : 'dark';
  });

  // Toggle between light and dark mode
  const toggleMode = () => {
    setMode((prevMode) => {
      const newMode = prevMode === 'light' ? 'dark' : 'light';
      localStorage.setItem('habexa-theme-mode', newMode);
      return newMode;
    });
  };

  // Create theme based on mode
  const theme = useMemo(() => {
    return createTheme({
      palette: {
        mode,
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
        info: {
          main: habexa.info.main,
        },
        background: {
          default: mode === 'dark' ? habexa.navy.dark : '#FFFFFF',
          paper: mode === 'dark' ? habexa.navy.main : '#F9FAFB',
        },
        text: {
          primary: mode === 'dark' ? habexa.gray[600] : '#1A1A1A',
          secondary: mode === 'dark' ? habexa.gray[500] : '#6B7280',
        },
        divider: mode === 'dark' ? habexa.gray[300] : '#E5E7EB',
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
              backgroundColor: mode === 'dark' ? habexa.navy.main : '#FFFFFF',
              border: `1px solid ${mode === 'dark' ? habexa.gray[300] : '#E5E7EB'}`,
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
                borderColor: mode === 'dark' ? habexa.gray[300] : '#E5E7EB',
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
  }, [mode]);

  // Update CSS variables when mode changes
  useEffect(() => {
    const root = document.documentElement;
    if (mode === 'dark') {
      root.style.setProperty('--habexa-purple-main', habexa.purple.main);
      root.style.setProperty('--habexa-navy-main', habexa.navy.main);
      root.style.setProperty('--habexa-navy-light', habexa.navy.light);
      root.style.setProperty('--habexa-navy-dark', habexa.navy.dark);
      root.style.setProperty('--habexa-gray-300', habexa.gray[300]);
      root.style.setProperty('--habexa-gray-400', habexa.gray[400]);
      root.style.setProperty('--habexa-gray-500', habexa.gray[500]);
      root.style.setProperty('--habexa-gray-600', habexa.gray[600]);
    } else {
      root.style.setProperty('--habexa-purple-main', habexa.purple.main);
      root.style.setProperty('--habexa-navy-main', '#FFFFFF');
      root.style.setProperty('--habexa-navy-light', '#F9FAFB');
      root.style.setProperty('--habexa-navy-dark', '#FFFFFF');
      root.style.setProperty('--habexa-gray-300', '#E5E7EB');
      root.style.setProperty('--habexa-gray-400', '#9CA3AF');
      root.style.setProperty('--habexa-gray-500', '#6B7280');
      root.style.setProperty('--habexa-gray-600', '#1A1A1A');
    }
  }, [mode]);

  const value = {
    mode,
    toggleMode,
    theme,
  };

  return (
    <ThemeContext.Provider value={value}>
      <MUIThemeProvider theme={theme}>
        <CssBaseline />
        {children}
      </MUIThemeProvider>
    </ThemeContext.Provider>
  );
};

