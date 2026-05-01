import React, { useState } from 'react';
import Sidebar from './Sidebar';
import Header from './Header';

export default function Layout({ activePage, onNavigate, title, onRefresh, isRefreshing, children }) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  return (
    <div className="app-layout">
      <Sidebar 
        activePage={activePage} 
        onNavigate={onNavigate} 
        isOpen={isSidebarOpen} 
        onClose={() => setIsSidebarOpen(false)} 
      />
      <div className="main-content">
        <Header
          title={title}
          onRefresh={onRefresh}
          isRefreshing={isRefreshing}
          onMenuClick={() => setIsSidebarOpen(true)}
        />
        <div className="page-content">
          {children}
        </div>
      </div>
    </div>
  );
}
