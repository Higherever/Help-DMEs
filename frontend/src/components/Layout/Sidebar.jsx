import React from 'react';

const NAV_ITEMS = [
  { id: 'dashboard', icon: '📊', label: 'Dashboard' },
  { id: 'sbcs',      icon: '⚽', label: 'DMEs / SBCs' },
  { id: 'squad',     icon: '👥', label: 'Elenco' },
  { id: 'calculator',icon: '🧮', label: 'Calculador' },
  { id: 'settings',  icon: '⚙️', label: 'Configurações' },
];

export default function Sidebar({ activePage, onNavigate, isOpen, onClose }) {
  return (
    <>
      <div className={`sidebar-overlay ${isOpen ? 'open' : ''}`} onClick={onClose} />
      <aside className={`sidebar ${isOpen ? 'open' : ''}`}>
        <div className="sidebar-logo">Help DMEs</div>
        <nav className="sidebar-nav">
          {NAV_ITEMS.map(item => (
            <div
              key={item.id}
              className={`nav-item ${activePage === item.id ? 'active' : ''}`}
              onClick={() => {
                onNavigate(item.id);
                if (window.innerWidth <= 768) onClose();
              }}
            >
              <span className="nav-item-icon">{item.icon}</span>
              <span>{item.label}</span>
            </div>
          ))}
        </nav>
      </aside>
    </>
  );
}
