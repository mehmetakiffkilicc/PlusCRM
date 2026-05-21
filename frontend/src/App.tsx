import { lazy, Suspense, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate } from 'react-router-dom'
import useAuthStore from './stores/authStore'
import InlineSpinner from './components/InlineSpinner'
import DashboardLayout from './layouts/DashboardLayout'
import ErrorBoundary from './components/ErrorBoundary'
import './App.css'

// Lazy load components
const DashboardHome = lazy(() => import('./pages/DashboardHome'))
const Login = lazy(() => import('./pages/Login'))
const Register = lazy(() => import('./pages/Register'))

// Lazy load CRM pages
const RFMAnalysis = lazy(() => import('./pages/RFMAnalysis'))
const ChurnAnalysis = lazy(() => import('./pages/ChurnAnalysis'))
const Segmentation = lazy(() => import('./pages/Segmentation'))
const Campaigns = lazy(() => import('./pages/Campaigns'))
const Products = lazy(() => import('./pages/Products'))
const CategoryReport = lazy(() => import('./pages/CategoryReport'))
const Settings = lazy(() => import('./pages/Settings'))
const CustomerPortal = lazy(() => import('./pages/CustomerPortal'))
const CampaignSuggestions = lazy(() => import('./components/CampaignSuggestions'))

// 404 Not Found component
const NotFoundPage = () => {
  const navigate = useNavigate()
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100vh', background: '#f9fafb', gap: '16px' }}>
      <div style={{ fontSize: '80px', fontWeight: 800, color: '#e5e7eb' }}>404</div>
      <div style={{ fontSize: '20px', fontWeight: 600, color: '#374151' }}>Sayfa Bulunamadı</div>
      <div style={{ fontSize: '14px', color: '#6b7280' }}>Aradığınız sayfa mevcut değil veya taşınmış olabilir.</div>
      <button
        onClick={() => navigate('/')}
        style={{ marginTop: '8px', padding: '10px 24px', background: '#4f46e5', color: 'white', border: 'none', borderRadius: '8px', cursor: 'pointer', fontSize: '14px', fontWeight: 600 }}
      >
        Ana Sayfaya Dön
      </button>
    </div>
  )
}

// Loading fallback component
const PageLoader = () => (
  <div style={{
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100vh',
    background: '#f9fafb'
  }}>
    <div style={{
      textAlign: 'center',
      padding: '40px'
    }}>
      <InlineSpinner size={48} thickness={4} />
    </div>
  </div>
)

const InlineRouteLoader = () => (
  <div style={{
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: '60vh',
    background: '#f9fafb'
  }}>
    <InlineSpinner size={32} thickness={4} />
  </div>
)

export default function App() {
  const { isAuthenticated } = useAuthStore()

  // Ensure demo-token is set in localStorage for the demo environment
  useEffect(() => {
    if (!localStorage.getItem('auth_token')) {
      localStorage.setItem('auth_token', 'demo-token')
    }
  }, [])

  // PERF: Avoid long first navigation waits on cold cache / high latency.
  // Preload the initial authenticated route chunk as soon as auth is known.
  useEffect(() => {
    if (isAuthenticated) {
      void import('./pages/DashboardHome')
    } else {
      void import('./pages/Login')
    }
  }, [isAuthenticated])

  return (
    <ErrorBoundary>
      <Router>
        <Routes>
          {/* Redirect Auth Pages in Demo Mode */}
          <Route path="/giris" element={<Navigate to="/" />} />
          <Route path="/kayit" element={<Navigate to="/" />} />
          
          {/* Dashboard Routes */}
          <Route element={<DashboardLayout />}>
            <Route path="/" element={<Suspense fallback={<InlineRouteLoader />}><DashboardHome /></Suspense>} />
            <Route path="/urunler" element={<Suspense fallback={<InlineRouteLoader />}><Products /></Suspense>} />
            <Route path="/rfm-analizi" element={<Suspense fallback={<InlineRouteLoader />}><RFMAnalysis /></Suspense>} />
            <Route path="/churn-analizi" element={<Suspense fallback={<InlineRouteLoader />}><ChurnAnalysis /></Suspense>} />
            <Route path="/segmentasyon" element={<Suspense fallback={<InlineRouteLoader />}><Segmentation /></Suspense>} />
            <Route path="/kampanyalar" element={<Suspense fallback={<InlineRouteLoader />}><Campaigns /></Suspense>} />
            <Route path="/kategori-raporu" element={<Suspense fallback={<InlineRouteLoader />}><CategoryReport /></Suspense>} />
            <Route path="/musteri-portali" element={<Suspense fallback={<InlineRouteLoader />}><CustomerPortal /></Suspense>} />
            <Route path="/ayarlar" element={<Suspense fallback={<InlineRouteLoader />}><Settings /></Suspense>} />
            <Route path="/kampanya-onerileri" element={<Suspense fallback={<InlineRouteLoader />}><CampaignSuggestions /></Suspense>} />
            
            {/* Fallback for unknown routes */}
            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Routes>
      </Router>
    </ErrorBoundary>
  )
}
