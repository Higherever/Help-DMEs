import React, { useState, useEffect, useRef } from 'react';
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

  const pathRef = useRef(null);
  const sidebarRef = useRef(null);

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

  // Guardamos o estado de expansão em um ref para acesso instantâneo e síncrono no loop do rAF
  const isExpandedRef = useRef(isExpanded);
  useEffect(() => {
    isExpandedRef.current = isExpanded;
  }, [isExpanded]);

  // Hook principal da física elástica do Blob SVG (rodando a 60 FPS estáveis)
  useEffect(() => {
    if (isMobile) return;

    let widthTarget = isExpanded ? 240 : 72;
    let widthCurrent = isExpanded ? 240 : 72;
    let vw = 0;

    let blobXTarget = 0;
    let blobXCurrent = 0;
    let vx = 0;

    let yTarget = 400; // Ponto central inicial do viewBox
    let yCurrent = 400;
    let vy = 0;

    let animationFrameId = null;

    const handleMouseMove = (e) => {
      const sidebarWidth = isExpandedRef.current ? 240 : 72;
      const mouseX = e.clientX;
      const mouseY = e.clientY;

      // Mapeia o Y real da janela para o viewBox (0 a 800)
      yTarget = (mouseY / window.innerHeight) * 800;

      // Distância horizontal do mouse em relação à borda direita da sidebar
      const distX = mouseX - sidebarWidth;

      // Se o mouse estiver muito próximo da borda direita da barra lateral, puxa o blob elástico
      if (distX > -50 && distX < 120) {
        const factor = Math.max(0, 1 - Math.abs(distX) / 120);
        blobXTarget = factor * 45; // Protuberância máxima de 45px
      } else {
        blobXTarget = 0;
      }
    };

    window.addEventListener('mousemove', handleMouseMove);

    const updatePhysics = () => {
      // Define a largura alvo da física com base no estado expandido real
      widthTarget = isExpandedRef.current ? 240 : 72;

      // Física de mola para a largura da barra (cria a oscilação jelly de transição)
      const dw = widthTarget - widthCurrent;
      vw = vw * 0.76 + dw * 0.12; // Damping 0.76, Stiffness 0.12
      widthCurrent += vw;

      // Física de mola para o offset X do blob (peeling elástico do mouse)
      // Se a barra estiver mudando de tamanho ativamente, evitamos esticar o blob do mouse
      const isTransitioning = Math.abs(dw) > 1.5;
      const targetX = isTransitioning ? 0 : blobXTarget;

      const dx = targetX - blobXCurrent;
      vx = vx * 0.75 + dx * 0.14; // Damping 0.75, Stiffness 0.14
      blobXCurrent += vx;

      // Física de mola para o Y do blob
      const dy = yTarget - yCurrent;
      vy = vy * 0.78 + dy * 0.14; // Segue suavemente o Y
      yCurrent += vy;

      // Escreve o path de forma direta no DOM a cada frame do requestAnimationFrame
      if (pathRef.current) {
        const d = `M ${widthCurrent},800 H 0 V 0 H ${widthCurrent} C ${widthCurrent},0 ${widthCurrent},${yCurrent - 160} ${widthCurrent + blobXCurrent},${yCurrent - 90} ${widthCurrent + blobXCurrent},${yCurrent} S ${widthCurrent},${yCurrent + 160} ${widthCurrent},800 Z`;
        pathRef.current.setAttribute('d', d);
      }

      animationFrameId = requestAnimationFrame(updatePhysics);
    };

    animationFrameId = requestAnimationFrame(updatePhysics);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      if (animationFrameId) {
        cancelAnimationFrame(animationFrameId);
      }
    };
  }, [isMobile]);

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
        ref={sidebarRef}
        className={`sidebar ${isOpen ? 'open' : ''}`}
        onMouseEnter={() => !isMobile && setIsHovered(true)}
        onMouseLeave={() => !isMobile && setIsHovered(false)}
        variants={!isMobile ? sidebarVariants : {}}
        animate={!isMobile ? (isExpanded ? 'expanded' : 'collapsed') : {}}
        initial={!isMobile ? 'collapsed' : {}}
      >
        {/* SVG do blob elástico de fundo (renderizado apenas no desktop) */}
        {!isMobile && (
          <svg id="blob" viewBox="0 0 320 800" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">
            <path ref={pathRef} id="blob-path" d="M 72,800 H 0 V 0 H 72 Z" />
          </svg>
        )}

        {/* Topo: Hambúrguer e Logo do Site */}
        <div className="sidebar-header">
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
