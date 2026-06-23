import { Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import Layout from './components/Layout';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import MyPlans from './pages/MyPlans';
import Community from './pages/Community';
import Search from './pages/Search';
import Profile from './pages/Profile';
import HashtagPage from './pages/HashtagPage';
import UserProfile from './pages/UserProfile';
import PlanDetail from './pages/PlanDetail';
import PostDetail from './pages/PostDetail';
import ChangePassword from './pages/ChangePassword';
import Notifications from './pages/Notifications';
import MyPosts from './pages/MyPosts';
import Activities from './pages/Activities';
import ChatBot from './pages/ChatBot';
import Assistant from './pages/Assistant';
import SystemConfig from './pages/SystemConfig';
import LangGraphTest from './pages/LangGraphTest';

const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const { user, isLoading } = useAuth();
  
  if (isLoading) {
    return <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>加载中...</div>;
  }
  
  return user ? children : <Navigate to="/login" />;
};

const PublicRoute = ({ children }: { children: React.ReactNode }) => {
  const { user, isLoading } = useAuth();
  
  if (isLoading) {
    return <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>加载中...</div>;
  }
  
  return user ? <Navigate to="/dashboard" /> : children;
};

const AppContent = () => {
  return (
    <Routes>
      <Route path="/login" element={
        <PublicRoute>
          <Login />
        </PublicRoute>
      } />
      <Route path="/register" element={
        <PublicRoute>
          <Register />
        </PublicRoute>
      } />
      <Route path="/dashboard" element={
        <ProtectedRoute>
          <Layout>
            <Dashboard />
          </Layout>
        </ProtectedRoute>
      } />
      <Route path="/my-plans" element={
        <ProtectedRoute>
          <Layout>
            <MyPlans />
          </Layout>
        </ProtectedRoute>
      } />
      <Route path="/community" element={
        <ProtectedRoute>
          <Layout>
            <Community />
          </Layout>
        </ProtectedRoute>
      } />
      <Route path="/search" element={
        <ProtectedRoute>
          <Layout>
            <Search />
          </Layout>
        </ProtectedRoute>
      } />
      <Route path="/hashtag/:hashtag" element={
        <ProtectedRoute>
          <Layout>
            <HashtagPage />
          </Layout>
        </ProtectedRoute>
      } />
      <Route path="/change-password" element={
        <ProtectedRoute>
          <ChangePassword />
        </ProtectedRoute>
      } />
      <Route path="/profile" element={
        <ProtectedRoute>
          <Layout>
            <Profile />
          </Layout>
        </ProtectedRoute>
      } />
      <Route path="/notifications" element={
        <ProtectedRoute>
          <Layout>
            <Notifications />
          </Layout>
        </ProtectedRoute>
      } />
      <Route path="/my-posts" element={
        <ProtectedRoute>
          <Layout>
            <MyPosts />
          </Layout>
        </ProtectedRoute>
      } />
      <Route path="/activities" element={
        <ProtectedRoute>
          <Activities />
        </ProtectedRoute>
      } />
      <Route path="/user/:userId" element={
        <ProtectedRoute>
          <Layout>
            <UserProfile />
          </Layout>
        </ProtectedRoute>
      } />
      <Route path="/plan/:planId" element={
        <ProtectedRoute>
          <Layout>
            <PlanDetail />
          </Layout>
        </ProtectedRoute>
      } />
      <Route path="/post/:postId" element={
        <ProtectedRoute>
          <Layout>
            <PostDetail />
          </Layout>
        </ProtectedRoute>
      } />
      <Route path="/chatbot" element={
        <ProtectedRoute>
          <ChatBot />
        </ProtectedRoute>
      } />
      <Route path="/assistant" element={
        <ProtectedRoute>
          <Assistant />
        </ProtectedRoute>
      } />
      <Route path="/langgraph" element={
        <ProtectedRoute>
          <LangGraphTest />
        </ProtectedRoute>
      } />
      <Route path="/system-config" element={
        <ProtectedRoute>
          <SystemConfig />
        </ProtectedRoute>
      } />
      <Route path="/" element={<Navigate to="/dashboard" />} />
    </Routes>
  );
};

const App = () => {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
};

export default App;
