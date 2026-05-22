import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { LayoutDashboard, Trophy, Users, Calculator, Settings } from 'lucide-react';

const NAV_ITEMS = [
  { id: 'dashboard',  icon: LayoutDashboard, label: 'Dashboard' },
  { id: 'sbcs',       icon: Trophy,          label: 'DMEs / SBCs' },
  { id: 'squad',      icon: Users,           label: 'Elenco' },
  { id: 'calculator', icon: Calculator,      label: 'Calculador' },
];

export default function Sidebar({ activePage, onNavigate, isOpen, onClose }) {
  const [isHovered, setIsHovered] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  // Detecta se a tela é mobile para desativar a expansão por hover
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth <= 768);
    };
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // Determina se a sidebar deve estar no estado expandido
  const isExpanded = isMobile ? isOpen : isHovered;

  // Variantes de animação da largura da Sidebar (apenas no desktop)
  const sidebarVariants = {
    expanded: { 
      width: 240,
      paddingLeft: 16,
      paddingRight: 16,
      transition: { type: 'spring', stiffness: 350, damping: 32 } 
    },
    collapsed: { 
      width: 72,
      paddingLeft: 10,
      paddingRight: 10,
      transition: { type: 'spring', stiffness: 350, damping: 32 } 
    }
  };

  // Variantes de fade para os textos que aparecem sob expansão
  const textVariants = {
    hidden: { 
      opacity: 0, 
      x: -12,
      transition: { duration: 0.15, ease: 'easeInOut' } 
    },
    visible: { 
      opacity: 1, 
      x: 0,
      transition: { duration: 0.25, ease: 'easeOut', delay: 0.05 } 
    }
  };

  return (
    <>
      {/* Overlay escuro em dispositivos móveis */}
      <div className={`sidebar-overlay ${isOpen ? 'open' : ''}`} onClick={onClose} />

      <motion.aside
        className={`sidebar ${isOpen ? 'open' : ''}`}
        onMouseEnter={() => !isMobile && setIsHovered(true)}
        onMouseLeave={() => !isMobile && setIsHovered(false)}
        variants={!isMobile ? sidebarVariants : {}}
        animate={!isMobile ? (isExpanded ? 'expanded' : 'collapsed') : {}}
        initial={!isMobile ? 'collapsed' : {}}
      >
        {/* Topo / Logo do Site */}
        <div className="sidebar-logo" onClick={() => onNavigate('dashboard')} style={{ cursor: 'pointer' }}>
          <div className="sidebar-logo-icon">
            <img src="/logo.svg" alt="Help DMEs Logo" className="logo-svg-render" />
          </div>
          <AnimatePresence initial={false}>
            {isExpanded && (
              <motion.span
                className="sidebar-logo-text"
                variants={textVariants}
                initial="hidden"
                animate="visible"
                exit="hidden"
              >
                Help DMEs
              </motion.span>
            )}
          </AnimatePresence>
        </div>

        {/* Menu de Navegação */}
        <nav className="sidebar-nav">
          {NAV_ITEMS.map(item => {
            const Icon = item.icon;
            const isActive = activePage === item.id;
            return (
              <div
                key={item.id}
                className={`nav-item ${isActive ? 'active' : ''}`}
                onClick={() => {
                  onNavigate(item.id);
                  if (isMobile) onClose();
                }}
                title={!isExpanded ? item.label : undefined}
              >
                <div className="nav-item-icon">
                  <Icon size={20} strokeWidth={isActive ? 2.2 : 1.8} />
                </div>
                <AnimatePresence initial={false}>
                  {isExpanded && (
                    <motion.span
                      variants={textVariants}
                      initial="hidden"
                      animate="visible"
                      exit="hidden"
                    >
                      {item.label}
                    </motion.span>
                  )}
                </AnimatePresence>
              </div>
            );
          })}
        </nav>

        {/* Rodapé da Sidebar / Perfil do Usuário */}
        <div className="sidebar-footer">
          <div className="user-avatar" title={!isExpanded ? "Administrador" : undefined}>
            AD
          </div>
          <AnimatePresence initial={false}>
            {isExpanded && (
              <motion.div
                className="user-info"
                variants={textVariants}
                initial="hidden"
                animate="visible"
                exit="hidden"
              >
                <span className="user-name">Administrador</span>
                <span className="user-role">SBC Expert</span>
              </motion.div>
            )}
          </AnimatePresence>

          <div 
            className={`settings-trigger ${activePage === 'settings' ? 'active' : ''}`}
            onClick={() => {
              onNavigate('settings');
              if (isMobile) onClose();
            }}
            title="Configurações"
          >
            <Settings size={20} strokeWidth={1.8} />
          </div>
        </div>
      </motion.aside>
    </>
  );
}
