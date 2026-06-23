import React from 'react';
import type { ReactNode } from 'react';
import Sidebar from './Sidebar';

interface LayoutProps {
  children: ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  return (
    <div style={styles.dashboardContainer}>
      <Sidebar />
      <main style={styles.mainContent}>
        {children}
      </main>
    </div>
  );
};

const styles: { [key: string]: React.CSSProperties } = {
  dashboardContainer: {
    display: 'flex',
    minHeight: '100vh',
  },
  mainContent: {
    flex: 1,
    marginLeft: '280px',
    padding: '24px',
    overflowY: 'auto',
    backgroundColor: '#f1f5f9',
  },
};

export default Layout;
