import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import PixelIcon from './PixelIcon';

const NAV_ITEMS = [
  { id: 'dashboard',  label: 'Dashboard' },
  { id: 'sbcs',       label: 'DMEs / SBCs' },
  { id: 'squad',      label: 'Elenco' },
  { id: 'calculator', label: 'Calculador' },
];

export default function Sidebar({ activePage, onNavigate, isOpen, onClose }) {
  const [isHovered, setIsHovered] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const sidebarRef = useRef(null);

  // Detecta se a tela é mobile
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

  // Variantes de fade para os textos que aparecem sob expansão
  const textVariants = {
    hidden: { 
      opacity: 0, 
      x: -8,
      transition: { duration: 0.2, ease: 'easeInOut' } 
    },
    visible: { 
      opacity: 1, 
      x: 0,
      transition: { duration: 0.3, ease: 'easeOut', delay: 0.05 } 
    }
  };

  return (
    <>
      {/* Overlay escuro em dispositivos móveis */}
      <div className={`sidebar-overlay ${isOpen ? 'open' : ''}`} onClick={onClose} />

      <aside
        ref={sidebarRef}
        className={`sidebar ${isOpen ? 'open' : ''} ${isExpanded ? 'expanded' : 'collapsed'}`}
        onMouseEnter={() => !isMobile && setIsHovered(true)}
        onMouseLeave={() => !isMobile && setIsHovered(false)}
      >
        {/* Topo: Hambúrguer e Logo do Site */}
        <div className={`sidebar-header ${isExpanded ? 'expanded' : 'collapsed'}`}>
          <AnimatePresence initial={false}>
            {isExpanded && (
              <motion.div 
                className="hamburger-trigger-wrapper"
                initial={{ width: 0, opacity: 0, marginRight: 0 }}
                animate={{ width: 'auto', opacity: 1, marginRight: 8 }}
                exit={{ width: 0, opacity: 0, marginRight: 0 }}
                transition={{ type: 'spring', stiffness: 180, damping: 20 }}
                style={{ overflow: 'hidden', display: 'flex', alignItems: 'center' }}
              >
                <div 
                  className={`hamburger-trigger ${isExpanded ? 'active' : ''}`} 
                  onClick={() => !isMobile && setIsHovered(!isHovered)}
                  title={isExpanded ? "Recolher Menu" : "Expandir Menu"}
                >
                  <div className="hamburger">
                    <div className="line"></div>
                    <div className="line"></div>
                    <div className="line"></div>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          <div 
            className="sidebar-logo" 
            onClick={() => {
              if (!isExpanded && !isMobile) {
                setIsHovered(true); // Clicar na logo colapsada expande a barra
              } else {
                onNavigate('sbcs');
              }
            }} 
            style={{ cursor: 'pointer' }}
          >
            <div className="sidebar-logo-icon">
              <img 
                src="/logo.png" 
                alt="Help DMEs Logo" 
                className="logo-svg-render" 
                style={{ width: '100%', height: '100%', objectFit: 'cover', filter: 'invert(1)' }} 
              />
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
        </div>

        {/* Menu de Navegação */}
        <nav className="sidebar-nav">
          {NAV_ITEMS.map(item => {
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
                  <PixelIcon name={item.id} size={22} active={isActive} />
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

          <AnimatePresence initial={false}>
            {isExpanded && (
              <motion.div
                className="settings-trigger-wrapper"
                initial={{ width: 0, opacity: 0, marginLeft: 0 }}
                animate={{ width: 'auto', opacity: 1, marginRight: 8 }}
                exit={{ width: 0, opacity: 0, marginLeft: 0 }}
                transition={{ type: 'spring', stiffness: 180, damping: 20 }}
                style={{ overflow: 'hidden', display: 'flex', alignItems: 'center' }}
              >
                <div 
                  className={`settings-trigger ${activePage === 'settings' ? 'active' : ''}`}
                  onClick={() => {
                    onNavigate('settings');
                    if (isMobile) onClose();
                  }}
                  title="Configurações"
                >
                  <PixelIcon name="settings" size={22} active={activePage === 'settings'} />
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </aside>
    </>
  );
}
