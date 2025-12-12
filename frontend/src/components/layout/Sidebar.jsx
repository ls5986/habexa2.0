import { Box, Typography, Button } from '@mui/material';
import { Home, Inbox, Users, Package, Search, Settings, ChevronLeft, ChevronRight, CreditCard, ShoppingCart, Receipt, FileText, Star, BarChart3, DollarSign, Sparkles } from 'lucide-react';
import { useNavigate, useLocation } from 'react-router-dom';
import { habexa } from '../../theme';
import { useNotifications } from '../../context/NotificationContext';
import { useFeatureGate } from '../../hooks/useFeatureGate';

const menuItems = [
  { id: 'dashboard', label: 'Dashboard', icon: Home, path: '/dashboard' },
  { id: 'products', label: 'Products', icon: Package, path: '/products', badge: true },
  { id: 'analyzer', label: 'Analyzer', icon: BarChart3, path: '/analyzer' },
  { id: 'recommendations', label: 'Recommendations', icon: Sparkles, path: '/recommendations' },
  { id: 'favorites', label: 'Favorites', icon: Star, iconImage: '/logos/favorites-icon.png', path: '/favorites' },
  { id: 'suppliers', label: 'Suppliers', icon: Users, path: '/suppliers' },
  { id: 'jobs', label: 'Upload Jobs', icon: FileText, path: '/jobs' },
  { id: 'buy-list', label: 'Buy List', icon: ShoppingCart, path: '/buy-list' },
  { id: 'buy-lists', label: 'Buy Lists', icon: ShoppingCart, path: '/buy-lists' },
  { id: 'orders', label: 'Orders', icon: Receipt, path: '/orders' },
  { id: 'financial', label: 'Financial', icon: DollarSign, path: '/financial' },
  { id: 'analyze', label: 'Analyze', icon: Search, path: '/analyze' },
  { id: 'pricing', label: 'Pricing', icon: CreditCard, path: '/pricing' },
];

const NavItem = ({ icon: Icon, iconImage, label, path, active, badge, collapsed }) => {
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
        color: active ? '#ffffff' : '#1a1a2e',
        background: active 
          ? `linear-gradient(135deg, ${habexa.purple.main} 0%, ${habexa.purple.dark} 100%)`
          : 'transparent',
        transition: 'all 0.2s ease',
        '&:hover': {
          background: active 
            ? `linear-gradient(135deg, ${habexa.purple.main} 0%, ${habexa.purple.dark} 100%)`
            : '#f5f5f5',
          color: active ? '#ffffff' : '#1a1a2e',
        },
      }}
    >
      {badge && unreadCount > 0 ? (
        <Box sx={{ position: 'relative' }}>
          {iconImage ? (
            <Box
              component="img"
              src={iconImage}
              alt={label}
              sx={{ width: 20, height: 20, objectFit: 'contain' }}
            />
          ) : (
            <Icon size={20} />
          )}
          <Box
            sx={{
              position: 'absolute',
              top: -4,
              right: -4,
              width: 8,
              height: 8,
              borderRadius: '50%',
              bgcolor: habexa.error.main,
              border: (theme) => `2px solid ${theme.palette.background.default}`,
            }}
          />
        </Box>
      ) : iconImage ? (
        <Box
          component="img"
          src={iconImage}
          alt={label}
          sx={{ width: 20, height: 20, objectFit: 'contain' }}
        />
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
  const navigate = useNavigate();
  const { tier, isSuperAdmin, tierDisplay } = useFeatureGate();
  const isActive = (path) => location.pathname === path;
  
  // Determine plan display - check super admin first, then tier
  const planDisplay = isSuperAdmin ? 'Super Admin' : (tierDisplay || tier || 'Free');
  const showUpgrade = !isSuperAdmin && (tier === 'free' || !tier);

  return (
    <Box
      sx={{
        width: collapsed ? 72 : 260,
        height: '100vh',
        backgroundColor: '#FFFFFF',
        borderRight: '1px solid #e0e0e0',
        display: 'flex',
        flexDirection: 'column',
        transition: 'width 0.3s ease',
      }}
    >
      {/* Logo Section */}
      <Box sx={{ p: 3, borderBottom: '1px solid #e0e0e0' }}>
        {collapsed ? (
          <Box
            sx={{
              width: 32,
              height: 32,
              borderRadius: 2,
              bgcolor: habexa.purple.main,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              mx: 'auto',
            }}
          >
            <img 
              src="/logos/Asset 5@300x.png" 
              alt="Habexa" 
              style={{ width: 32, height: 32, objectFit: 'contain' }}
            />
          </Box>
        ) : (
          <img 
            src="/logos/Asset 1@300x.png" 
            alt="Habexa" 
            style={{ height: 32, maxWidth: '100%' }}
          />
        )}
      </Box>

      {/* Navigation */}
      <Box sx={{ flex: 1, py: 2 }}>
        {menuItems.map((item) => (
          <NavItem
            key={item.id}
            icon={item.icon}
            iconImage={item.iconImage}
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
        <Box sx={{ p: 2, borderTop: '1px solid #e0e0e0' }}>
          <Box
            sx={{
              p: 2,
              borderRadius: 2,
              backgroundColor: '#f5f5f5',
              border: '1px solid #e0e0e0',
            }}
          >
            <Typography variant="caption" sx={{ color: '#666666' }}>
              Current Plan
            </Typography>
            <Typography variant="body2" fontWeight="600" sx={{ color: '#1a1a2e' }} mb={1}>
              {planDisplay}
            </Typography>
            {showUpgrade && (
              <Button
                size="small"
                variant="contained"
                fullWidth
                onClick={() => navigate('/pricing')}
                sx={{
                  background: `linear-gradient(135deg, ${habexa.purple.main} 0%, ${habexa.purple.dark} 100%)`,
                  '&:hover': {
                    background: `linear-gradient(135deg, ${habexa.purple.light} 0%, ${habexa.purple.dark} 100%)`,
                  },
                }}
              >
                Upgrade
              </Button>
            )}
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
          borderTop: '1px solid #e0e0e0',
        }}
      >
        <Box
          component="button"
          onClick={onToggle}
          sx={{
            border: 'none',
            background: 'transparent',
            color: '#666666',
            cursor: 'pointer',
            p: 1,
            borderRadius: 1,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            '&:hover': {
              color: '#1a1a2e',
              backgroundColor: '#f5f5f5',
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

