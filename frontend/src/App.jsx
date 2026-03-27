import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import Navbar from './components/Navbar';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import RequestLeave from './pages/RequestLeave';
import MyLeaves from './pages/MyLeaves';
import Approvals from './pages/Approvals';
import TeamCalendar from './pages/TeamCalendar';
import Balances from './pages/Balances';

function PrivateRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="flex items-center justify-center min-h-screen"><div className="skeleton w-32 h-8" /></div>;
  return user ? children : <Navigate to="/login" />;
}

function PublicRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return null;
  return user ? <Navigate to="/dashboard" /> : children;
}

function AppRoutes() {
  return (
    <>
      <Navbar />
      <Routes>
        <Route path="/login" element={<PublicRoute><Login /></PublicRoute>} />
        <Route path="/register" element={<PublicRoute><Register /></PublicRoute>} />
        <Route path="/dashboard" element={<PrivateRoute><Dashboard /></PrivateRoute>} />
        <Route path="/request-leave" element={<PrivateRoute><RequestLeave /></PrivateRoute>} />
        <Route path="/my-leaves" element={<PrivateRoute><MyLeaves /></PrivateRoute>} />
        <Route path="/approvals" element={<PrivateRoute><Approvals /></PrivateRoute>} />
        <Route path="/team-calendar" element={<PrivateRoute><TeamCalendar /></PrivateRoute>} />
        <Route path="/balances" element={<PrivateRoute><Balances /></PrivateRoute>} />
        <Route path="/" element={<Navigate to="/dashboard" />} />
      </Routes>
    </>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}
