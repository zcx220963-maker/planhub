import React, { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { LayoutDashboard, ClipboardList, Users, Search, User, LogOut, Plus, Bell, Bot, Zap, MessageSquare, Settings } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { notificationApi, chatApi } from '../services/api';

const Sidebar: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { logout, user } = useAuth();
  const [notificationUnreadCount, setNotificationUnreadCount] = useState(0);
  const [chatUnreadCount, setChatUnreadCount] = useState(0);

  useEffect(() => {
    if (user) {
      fetchUnreadCounts();
    }
  }, [user]);

  useEffect(() => {
    if (user) {
      const interval = setInterval(fetchUnreadCounts, 10000);
      return () => clearInterval(interval);
    }
  }, [user]);

  const fetchUnreadCounts = async () => {
    try {
      const notificationCount = await notificationApi.getUnreadCount();
      setNotificationUnreadCount(notificationCount);
    } catch (err) {
      console.error('Failed to fetch notification unread count:', err);
    }
    try {
      const conversations = await chatApi.getConversations();
      const chatCount = conversations.reduce((sum, conv) => sum + (conv.unreadCount || 0), 0);
      setChatUnreadCount(chatCount);
    } catch (err) {
      console.error('Failed to fetch chat unread count:', err);
    }
  };

  const combinedUnreadCount = notificationUnreadCount + chatUnreadCount;

  const navItems = [
    { icon: LayoutDashboard, label: '首页', path: '/dashboard' },
    { icon: ClipboardList, label: '我的计划', path: '/my-plans' },
    { icon: Users, label: '社区', path: '/community' },
    { icon: Search, label: '搜索', path: '/search' },
    { icon: MessageSquare, label: '消息与通知', path: '/notifications', badge: combinedUnreadCount },
    { icon: User, label: '个人资料', path: '/profile' },
  ];

  const aiItems = [
    { icon: () => <img src="/robot-icon.png" alt="Plan 助手" style={{ width: 28, height: 28 }} />, label: 'Plan 助手', path: '/langgraph', color: '#000000' },
  ];

  const systemItems = [
    { icon: Settings, label: '系统配置', path: '/system-config', color: '#333333' },
  ];

  const isActive = (path: string) => location.pathname === path;

  return (
    <aside style={styles.sidebar}>
      <div style={styles.logo}>
        <div style={styles.logoIcon}>
          <span style={{ fontSize: '24px', fontWeight: 'bold', color: '#ffffff' }}>P</span>
        </div>
        <span style={styles.logoText}>PlanHub</span>
      </div>

      <nav style={styles.nav}>
        <button
          style={styles.addPlanButton}
          onClick={() => navigate('/my-plans?create=true')}
        >
          <Plus size={20} />
          <span>创建计划</span>
        </button>

        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <Link
              key={item.path}
              to={item.path}
              style={{
                ...styles.navItem,
                ...(isActive(item.path) && styles.navItemActive),
              }}
            >
              <div style={{ width: 28, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                <Icon size={20} />
              </div>
              <span>{item.label}</span>
              {item.badge !== undefined && item.badge > 0 && (
                <span style={styles.badge}>{item.badge > 99 ? '99+' : item.badge}</span>
              )}
            </Link>
          );
        })}
      </nav>

      <div style={styles.divider}></div>

      <div style={styles.aiSection}>
        <span style={styles.sectionTitle}>AI 助手</span>
        {aiItems.map((item) => {
          const Icon = item.icon;
          return (
            <Link
              key={item.path}
              to={item.path}
              style={{
                ...styles.navItem,
                ...(isActive(item.path) && styles.navItemActive),
              }}
            >
              <div style={{ width: 28, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                <Icon size={20} style={{ color: item.color }} />
              </div>
              <span>{item.label}</span>
            </Link>
          );
        })}
      </div>

      <div style={styles.divider}></div>

      <div style={styles.aiSection}>
        <span style={styles.sectionTitle}>系统</span>
        {systemItems.map((item) => {
          const Icon = item.icon;
          return (
            <Link
              key={item.path}
              to={item.path}
              style={{
                ...styles.navItem,
                ...(isActive(item.path) && styles.navItemActive),
              }}
            >
              <div style={{ width: 28, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                <Icon size={20} style={{ color: item.color }} />
              </div>
              <span>{item.label}</span>
            </Link>
          );
        })}
      </div>

      <div style={styles.logoutSection}>
        <button style={styles.logoutButton} onClick={logout}>
          <LogOut size={20} />
          <span>退出登录</span>
        </button>
      </div>
    </aside>
  );
};

const styles: { [key: string]: React.CSSProperties } = {
  sidebar: {
    width: '280px',
    background: '#ffffff',
    color: '#64748b',
    padding: '24px 0',
    position: 'fixed',
    height: '100vh',
    overflowY: 'auto',
    left: 0,
    top: 0,
    display: 'flex',
    flexDirection: 'column',
    borderRight: '1px solid #e2e8f0',
  },
  logo: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    padding: '0 24px 32px',
    borderBottom: '1px solid #e2e8f0',
    marginBottom: '24px',
  },
  logoIcon: {
    width: '40px',
    height: '40px',
    background: '#333333',
    borderRadius: '10px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: '#ffffff',
  },
  logoText: {
    fontSize: '20px',
    fontWeight: 'bold',
    color: '#0f172a',
  },
  nav: {
    padding: '0 12px',
  },
  addPlanButton: {
    width: '100%',
    padding: '14px 16px',
    background: '#333333',
    color: '#ffffff',
    border: '1px solid #333333',
    borderRadius: '10px',
    fontSize: '15px',
    fontWeight: 'medium',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '8px',
    marginBottom: '16px',
    transition: 'all 0.3s ease',
  },
  navItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    padding: '12px 16px',
    borderRadius: '10px',
    color: '#64748b',
    textDecoration: 'none',
    transition: 'all 0.3s ease',
    marginBottom: '4px',
  },
  navItemActive: {
    background: '#f1f5f9',
    color: '#0f172a',
  },
  badge: {
    background: '#f1f5f9',
    color: '#333333',
    fontSize: '11px',
    fontWeight: 'bold',
    padding: '2px 6px',
    borderRadius: '10px',
    minWidth: '18px',
    textAlign: 'center',
  },
  divider: {
    height: '1px',
    background: '#e2e8f0',
    margin: '24px 12px',
  },
  aiSection: {
    padding: '0 12px',
  },
  sectionTitle: {
    fontSize: '12px',
    fontWeight: 'bold',
    color: '#94a3b8',
    textTransform: 'uppercase',
    letterSpacing: '1px',
    padding: '0 16px 12px',
    display: 'block',
  },
  logoutSection: {
    padding: '24px 12px 0',
    marginTop: 'auto',
  },
  logoutButton: {
    width: '100%',
    padding: '12px 16px',
    background: '#f1f5f9',
    color: '#333333',
    border: '1px solid #e2e8f0',
    borderRadius: '10px',
    fontSize: '15px',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '12px',
    transition: 'all 0.3s ease',
  },
};

export default Sidebar;
