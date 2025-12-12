import React, { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { CircularProgress, Box } from '@mui/material';
import { AuthProvider, useAuth } from './context/AuthContext';
import { SuppliersProvider } from './context/SuppliersContext';
import { NotificationProvider } from './context/NotificationContext';
import { ToastProvider } from './context/ToastContext';
import { StripeProvider } from './context/StripeContext';
import { ThemeProvider } from './context/ThemeContext';
import ErrorBoundary from './components/ErrorBoundary';
import './index.css';
import AppLayout from './components/layout/AppLayout';

// Lazy load pages for better performance
const LandingPage = lazy(() => import('./pages/LandingPage'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Deals = lazy(() => import('./pages/Deals'));
const DealDetail = lazy(() => import('./pages/DealDetail'));
const Suppliers = lazy(() => import('./pages/Suppliers'));
const Products = lazy(() => import('./pages/Products'));
const Analyze = lazy(() => import('./pages/Analyze'));
const Settings = lazy(() => import('./pages/Settings'));
const Pricing = lazy(() => import('./pages/Pricing'));
const BillingSuccess = lazy(() => import('./pages/BillingSuccess'));
const BillingCancel = lazy(() => import('./pages/BillingCancel'));
const Login = lazy(() => import('./pages/Login'));
const Register = lazy(() => import('./pages/Register'));
const Debug = lazy(() => import('./pages/Debug'));
const BuyList = lazy(() => import('./pages/BuyList'));
const BuyLists = lazy(() => import('./pages/BuyLists'));
const BuyListDetail = lazy(() => import('./pages/BuyListDetail'));
const Orders = lazy(() => import('./pages/Orders'));
const SupplierOrderDetail = lazy(() => import('./pages/SupplierOrderDetail'));
const TPLInboundDetail = lazy(() => import('./pages/TPLInboundDetail'));
const FBAShipmentDetail = lazy(() => import('./pages/FBAShipmentDetail'));
const FinancialDashboard = lazy(() => import('./pages/FinancialDashboard'));
const OrderDetails = lazy(() => import('./pages/OrderDetails'));
const Jobs = lazy(() => import('./pages/Jobs'));
const Favorites = lazy(() => import('./pages/Favorites'));
const Analyzer = lazy(() => import('./pages/Analyzer'));
const NotFound = lazy(() => import('./pages/NotFound'));

const Loading = () => (
  <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>
    <CircularProgress />
  </Box>
);

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
    <ErrorBoundary>
      <ThemeProvider>
        <AuthProvider>
          <SuppliersProvider>
            <NotificationProvider>
              <ToastProvider>
                <StripeProvider>
                <BrowserRouter>
            <Routes>
              {/* Public routes */}
              <Route path="/" element={<Suspense fallback={<Loading />}><LandingPage /></Suspense>} />
              <Route path="/login" element={<Suspense fallback={<Loading />}><Login /></Suspense>} />
              <Route path="/register" element={<Suspense fallback={<Loading />}><Register /></Suspense>} />
              <Route path="/billing/success" element={<Suspense fallback={<Loading />}><BillingSuccess /></Suspense>} />
              <Route path="/billing/cancel" element={<Suspense fallback={<Loading />}><BillingCancel /></Suspense>} />
              {/* Protected routes */}
              <Route
                path="/*"
                element={
                  <ProtectedRoute>
                    <AppLayout>
                      <Routes>
                        <Route path="/dashboard" element={<Suspense fallback={<Loading />}><Dashboard /></Suspense>} />
                        <Route path="/deals" element={<Navigate to="/analyzer" replace />} />
                        <Route path="/deals/:dealId" element={<Suspense fallback={<Loading />}><DealDetail /></Suspense>} />
                        <Route path="/suppliers" element={<Suspense fallback={<Loading />}><Suppliers /></Suspense>} />
                        <Route path="/products" element={<Navigate to="/analyzer" replace />} />
                        <Route path="/jobs" element={<Suspense fallback={<Loading />}><Jobs /></Suspense>} />
                        <Route path="/buy-list" element={<Suspense fallback={<Loading />}><BuyList /></Suspense>} />
                        <Route path="/buy-lists" element={<Suspense fallback={<Loading />}><BuyLists /></Suspense>} />
                        <Route path="/buy-lists/:id" element={<Suspense fallback={<Loading />}><BuyListDetail /></Suspense>} />
                        <Route path="/orders" element={<Suspense fallback={<Loading />}><Orders /></Suspense>} />
                        <Route path="/supplier-orders/:id" element={<Suspense fallback={<Loading />}><SupplierOrderDetail /></Suspense>} />
                        <Route path="/tpl/inbounds/:id" element={<Suspense fallback={<Loading />}><TPLInboundDetail /></Suspense>} />
                        <Route path="/fba-shipments/:id" element={<Suspense fallback={<Loading />}><FBAShipmentDetail /></Suspense>} />
                        <Route path="/orders/:id" element={<Suspense fallback={<Loading />}><OrderDetails /></Suspense>} />
                        <Route path="/analyze" element={<Suspense fallback={<Loading />}><Analyze /></Suspense>} />
                        <Route path="/analyzer" element={<Suspense fallback={<Loading />}><Analyzer /></Suspense>} />
                        <Route path="/settings" element={<Suspense fallback={<Loading />}><Settings /></Suspense>} />
                        <Route path="/pricing" element={<Suspense fallback={<Loading />}><Pricing /></Suspense>} />
                        <Route path="/favorites" element={<Suspense fallback={<Loading />}><Favorites /></Suspense>} />
                        {import.meta.env.DEV && (
                          <Route path="/debug" element={<Suspense fallback={<Loading />}><Debug /></Suspense>} />
                        )}
                      </Routes>
                    </AppLayout>
                  </ProtectedRoute>
                }
              />
              {/* 404 - Must be last */}
              <Route path="*" element={<Suspense fallback={<Loading />}><NotFound /></Suspense>} />
            </Routes>
                </BrowserRouter>
                </StripeProvider>
              </ToastProvider>
            </NotificationProvider>
          </SuppliersProvider>
        </AuthProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}

export default App;

