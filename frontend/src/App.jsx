import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider } from '@mui/material/styles';
import { CssBaseline } from '@mui/material';
import { AuthProvider, useAuth } from './context/AuthContext';
import { NotificationProvider } from './context/NotificationContext';
import { ToastProvider } from './context/ToastContext';
import { StripeProvider } from './context/StripeContext';
import theme from './theme';
import './index.css';
import AppLayout from './components/layout/AppLayout';
import Dashboard from './pages/Dashboard';
import Deals from './pages/Deals';
import Suppliers from './pages/Suppliers';
import Products from './pages/Products';
import Analyze from './pages/Analyze';
import Settings from './pages/Settings';
import Pricing from './pages/Pricing';
import BillingSuccess from './pages/BillingSuccess';
import BillingCancel from './pages/BillingCancel';
import Login from './pages/Login';
import Register from './pages/Register';

const ProtectedRoute = ({ children }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return <div>Loading...</div>;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return children;
};

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <AuthProvider>
        <NotificationProvider>
          <ToastProvider>
            <StripeProvider>
              <BrowserRouter>
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />
              <Route path="/billing/success" element={<BillingSuccess />} />
              <Route path="/billing/cancel" element={<BillingCancel />} />
              <Route
                path="/*"
                element={
                  <ProtectedRoute>
                    <AppLayout>
                      <Routes>
                        <Route path="/" element={<Navigate to="/dashboard" replace />} />
                        <Route path="/dashboard" element={<Dashboard />} />
                        <Route path="/deals" element={<Deals />} />
                        <Route path="/suppliers" element={<Suppliers />} />
                        <Route path="/products" element={<Products />} />
                        <Route path="/analyze" element={<Analyze />} />
                        <Route path="/settings" element={<Settings />} />
                        <Route path="/pricing" element={<Pricing />} />
                      </Routes>
                    </AppLayout>
                  </ProtectedRoute>
                }
              />
            </Routes>
          </BrowserRouter>
            </StripeProvider>
          </ToastProvider>
        </NotificationProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;

