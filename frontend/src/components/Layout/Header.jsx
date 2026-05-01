import React from 'react';
import { Menu } from 'lucide-react';

export default function Header({ title, onRefresh, isRefreshing, onMenuClick }) {
  return (
    <header className="top-header">
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <button className="mobile-menu-btn" onClick={onMenuClick}>
          <Menu size={24} />
        </button>
        <h2 className="header-title">{title}</h2>
      </div>
      <div className="header-actions">
        <button
          className={`btn-refresh ${isRefreshing ? 'spinning' : ''}`}
          onClick={onRefresh}
          disabled={isRefreshing}
        >
          <span className="refresh-icon">🔄</span>
          <span className="hidden-mobile">{isRefreshing ? 'Sincronizando...' : 'Atualizar dados'}</span>
        </button>
      </div>
    </header>
  );
}
