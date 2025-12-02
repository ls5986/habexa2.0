import { Box, Typography, Button } from '@mui/material';
import { Home, Inbox, Users, Package, Search, Settings, ChevronLeft, ChevronRight } from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';
import { habexa } from '../../theme';
import { useNotifications } from '../../context/NotificationContext';
// import { useSubscription } from '../../hooks/useSubscription';

const menuItems = [
  { id: 'dashboard', label: 'Dashboard', icon: Home, path: '/dashboard' },
  { id: 'products', label: 'Products', icon: Package, path: '/products', badge: true },
  { id: 'suppliers', label: 'Suppliers', icon: Users, path: '/suppliers' },
  { id: 'analyze', label: 'Analyze', icon: Search, path: '/analyze' },
];

const NavItem = ({ icon: Icon, label, path, active, badge, collapsed }) => {
  const navigate = useNavigate();
  const { unreadCount } = useNotifications();

  return (
    <Box
      component="button"
      onClick={() => navigate(path)}
      sx={{
        display: 'flex',
        alignItems: 'center',
        gap: 1.5,
        px: 3,
        py: 1.5,
        mx: 1.5,
        borderRadius: 1.5,
        textDecoration: 'none',
        border: 'none',
        cursor: 'pointer',
        width: collapsed ? 'auto' : 'calc(100% - 24px)',
        justifyContent: collapsed ? 'center' : 'flex-start',
        color: active ? '#FFFFFF' : '#A0A0B0',
        background: active 
          ? 'linear-gradient(135deg, #7C3AED 0%, #5B21B6 100%)'
          : 'transparent',
        transition: 'all 0.2s ease',
        '&:hover': {
          background: active 
            ? 'linear-gradient(135deg, #7C3AED 0%, #5B21B6 100%)'
            : 'rgba(124, 58, 237, 0.1)',
          color: '#FFFFFF',
        },
      }}
    >
      {badge && unreadCount > 0 ? (
        <Box sx={{ position: 'relative' }}>
          <Icon size={20} />
          <Box
            sx={{
              position: 'absolute',
              top: -4,
              right: -4,
              width: 8,
              height: 8,
              borderRadius: '50%',
              bgcolor: '#EF4444',
              border: '2px solid #0F0F1A',
            }}
          />
        </Box>
      ) : (
        <Icon size={20} />
      )}
      {!collapsed && (
        <Typography variant="body2" fontWeight={active ? 600 : 400}>
          {label}
        </Typography>
      )}
    </Box>
  );
};

const Sidebar = ({ collapsed, onToggle }) => {
  const location = useLocation();
  // const { subscription } = useSubscription();
  const subscription = { tier: 'free' }; // Fallback until hook is available
  const isActive = (path) => location.pathname === path;

  // Check for logo files
  const logoExists = false; // Will be true if logo files are found

  return (
    <Box
      sx={{
        width: collapsed ? 72 : 260,
        height: '100vh',
        background: 'linear-gradient(180deg, #0F0F1A 0%, #1A1A2E 100%)',
        borderRight: '1px solid #2D2D3D',
        display: 'flex',
        flexDirection: 'column',
        transition: 'width 0.3s ease',
      }}
    >
      {/* Logo Section */}
      <Box sx={{ p: 3, borderBottom: '1px solid #2D2D3D' }}>
        {collapsed ? (
          <Box
            sx={{
              width: 32,
              height: 32,
              borderRadius: 2,
              bgcolor: '#7C3AED',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'white',
              fontWeight: 700,
              fontSize: '0.875rem',
              mx: 'auto',
            }}
          >
            H
          </Box>
        ) : logoExists ? (
          <img src="/logo.svg" alt="Habexa" style={{ height: 32 }} />
        ) : (
          <Typography 
            variant="h5" 
            sx={{ 
              fontWeight: 800, 
              background: 'linear-gradient(135deg, #7C3AED 0%, #A78BFA 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              letterSpacing: '-0.5px'
            }}
          >
            Habexa
          </Typography>
        )}
      </Box>

      {/* Navigation */}
      <Box sx={{ flex: 1, py: 2 }}>
        {menuItems.map((item) => (
          <NavItem
            key={item.id}
            icon={item.icon}
            label={item.label}
            path={item.path}
            active={isActive(item.path)}
            badge={item.badge}
            collapsed={collapsed}
          />
        ))}
      </Box>

      {/* Settings */}
      <Box sx={{ px: 1.5, pb: 1 }}>
        <NavItem
          icon={Settings}
          label="Settings"
          path="/settings"
          active={isActive('/settings')}
          collapsed={collapsed}
        />
      </Box>

      {/* Bottom Section - Plan/Settings */}
      {!collapsed && (
        <Box sx={{ p: 2, borderTop: '1px solid #2D2D3D' }}>
          <Box
            sx={{
              p: 2,
              borderRadius: 2,
              background: 'rgba(124, 58, 237, 0.1)',
              border: '1px solid rgba(124, 58, 237, 0.2)',
            }}
          >
            <Typography variant="caption" color="text.secondary">
              Current Plan
            </Typography>
            <Typography variant="body2" fontWeight="600" color="primary.main" mb={1}>
              {subscription?.tier || 'Free'} {subscription?.tier === 'free' ? 'Trial' : ''}
            </Typography>
            <Button
              size="small"
              variant="contained"
              fullWidth
              component="a"
              href="/pricing"
              sx={{
                background: 'linear-gradient(135deg, #7C3AED 0%, #5B21B6 100%)',
                '&:hover': {
                  background: 'linear-gradient(135deg, #8B5CF6 0%, #6D28D9 100%)',
                },
              }}
            >
              Upgrade
            </Button>
          </Box>
        </Box>
      )}

      {/* Collapse Button */}
      <Box
        sx={{
          height: 48,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          borderTop: '1px solid #2D2D3D',
        }}
      >
        <Box
          component="button"
          onClick={onToggle}
          sx={{
            border: 'none',
            background: 'transparent',
            color: '#A0A0B0',
            cursor: 'pointer',
            p: 1,
            borderRadius: 1,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            '&:hover': {
              color: '#FFFFFF',
              backgroundColor: 'rgba(255, 255, 255, 0.1)',
            },
          }}
        >
          {collapsed ? <ChevronRight size={20} /> : <ChevronLeft size={20} />}
        </Box>
      </Box>
    </Box>
  );
};

export default Sidebar;

