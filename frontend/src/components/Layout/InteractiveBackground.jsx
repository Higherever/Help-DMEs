import React, { useEffect, useRef, useState } from 'react';
import { Sliders, Sparkles, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export default function InteractiveBackground() {
  // 1. Estados Reativos com persistência em localStorage
  const [theme, setTheme] = useState(() => localStorage.getItem('bg_theme') || 'violet');
  const [opacity, setOpacity] = useState(() => {
    const val = localStorage.getItem('bg_opacity');
    return val !== null ? parseFloat(val) : 0.35;
  });
  const [speed, setSpeed] = useState(() => {
    const val = localStorage.getItem('bg_speed');
    return val !== null ? parseFloat(val) : 0.15;
  });
  const [density, setDensity] = useState(() => {
    const val = localStorage.getItem('bg_density');
    return val !== null ? parseInt(val, 10) : 35; // Espaçamento em px da grade
  });
  const [glowEffect, setGlowEffect] = useState(() => {
    const val = localStorage.getItem('bg_glow');
    return val !== null ? val === 'true' : true;
  });
  const [isOpen, setIsOpen] = useState(false);

  const canvasRef = useRef(null);

  // Auxiliares de cores para o tema claro-mineral
  const getThemeColor = (currentTheme) => {
    switch (currentTheme) {
      case 'violet':
        return '#4f46e5'; // Roxo Editorial
      case 'orange':
        return '#b45309'; // Laranja Queimado
      case 'neon-green':
        return '#047857'; // Verde Floresta
      case 'quantum-cyan':
        return '#0369a1'; // Azul Mineral
      default:
        return '#4f46e5';
    }
  };

  const getThemeRgb = (currentTheme) => {
    switch (currentTheme) {
      case 'violet':
        return '79, 70, 229';
      case 'orange':
        return '180, 83, 9';
      case 'neon-green':
        return '4, 120, 87';
      case 'quantum-cyan':
        return '3, 105, 161';
      default:
        return '79, 70, 229';
    }
  };

  const themeColor = getThemeColor(theme);
  const themeRgb = getThemeRgb(theme);

  // 2. Referências sincronizadas para o loop do Canvas a 60 FPS
  const themeRef = useRef(theme);
  const opacityRef = useRef(opacity);
  const speedRef = useRef(speed);
  const densityRef = useRef(density);
  const glowRef = useRef(glowEffect);

  useEffect(() => {
    themeRef.current = theme;
    opacityRef.current = opacity;
    speedRef.current = speed;
    densityRef.current = density;
    glowRef.current = glowEffect;
  }, [theme, opacity, speed, density, glowEffect]);

  // 3. Sincronização cromática em tempo real no documentElement (:root)
  useEffect(() => {
    const root = document.documentElement;
    root.style.setProperty('--bg-theme-accent', themeColor);
    root.style.setProperty('--bg-theme-accent-rgb', themeRgb);
    root.style.setProperty('--accent', themeColor);
    root.style.setProperty('--accent-rgb', themeRgb);
    root.style.setProperty('--text-accent', theme === 'violet' ? '#818cf8' : themeColor);
  }, [theme, themeColor, themeRgb]);

  // 4. Renderização do Canvas da grade vetorial Matrix Engine
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    let animationFrameId;
    let time = 0;
    
    // Configurações físicas da grade de pontos
    let dots = [];
    let width = 0;
    let height = 0;

    const mouse = { x: null, y: null, radius: 110 };

    function initDots(w, h, spacing) {
      dots = [];
      const numCols = Math.ceil(w / spacing) + 1;
      const numRows = Math.ceil(h / spacing) + 1;

      for (let r = 0; r < numRows; r++) {
        for (let c = 0; c < numCols; c++) {
          const x = c * spacing;
          const y = r * spacing;
          dots.push({
            x: x,
            y: y,
            baseX: x,
            baseY: y,
            phase: Math.random() * Math.PI * 2
          });
        }
      }
    }

    function resize() {
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      width = canvas.width = rect.width * dpr;
      height = canvas.height = rect.height * dpr;
      ctx.scale(dpr, dpr);
      
      initDots(rect.width, rect.height, densityRef.current);
    }

    window.addEventListener('resize', resize);
    
    // Rastreia o mouse
    const handleMouseMove = (e) => {
      const rect = canvas.getBoundingClientRect();
      mouse.x = e.clientX - rect.left;
      mouse.y = e.clientY - rect.top;
    };

    const handleMouseLeave = () => {
      mouse.x = null;
      mouse.y = null;
    };

    window.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseleave', handleMouseLeave);
    
    // Forçar inicialização rápida
    resize();

    // Loop de animação física
    function draw() {
      if (!canvas) return;
      const w = canvas.clientWidth;
      const h = canvas.clientHeight;

      ctx.clearRect(0, 0, w, h);

      // Fundo escuro (Obsidian)
      ctx.fillStyle = '#050505';
      ctx.fillRect(0, 0, w, h);

      const currentOpacity = opacityRef.current;
      const currentSpeed = speedRef.current;
      const currentDensity = densityRef.current;
      const rgb = getThemeRgb(themeRef.current);

      time += currentSpeed * 0.05;

      // Se o espaçamento da grade mudou no painel, reinicializa os pontos
      if (dots.length === 0 || Math.abs(currentDensity - (dots[1]?.baseX - dots[0]?.baseX || 0)) > 2) {
        initDots(w, h, currentDensity);
      }

      // ── 1. Linhas técnicas de grade de fundo (Estética rigorosa) ──
      ctx.strokeStyle = `rgba(${rgb}, ${currentOpacity * 0.08})`;
      ctx.lineWidth = 0.5;
      
      for (let x = 0; x < w; x += currentDensity) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, h);
        ctx.stroke();
      }
      for (let y = 0; y < h; y += currentDensity) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(w, y);
        ctx.stroke();
      }

      // ── 2. Atualizar física dos pontos e desenhar conexões ──
      dots.forEach(dot => {
        // Oscilação autônoma lenta (simulando atividade de rede viva)
        const offsetRange = 3.5;
        const waveX = Math.sin(time + dot.phase) * offsetRange;
        const waveY = Math.cos(time + dot.phase) * offsetRange;

        let targetX = dot.baseX + waveX;
        let targetY = dot.baseY + waveY;

        // Repulsão do cursor
        if (mouse.x !== null && mouse.y !== null) {
          const dx = mouse.x - dot.x;
          const dy = mouse.y - dot.y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          if (dist < mouse.radius) {
            const force = (mouse.radius - dist) / mouse.radius;
            // Empurra os pontos levemente para longe do cursor
            targetX -= (dx / (dist || 1)) * force * 16;
            targetY -= (dy / (dist || 1)) * force * 16;
          }
        }

        // Interpolação suave para movimento fluído (Spring-damping aproximado)
        dot.x += (targetX - dot.x) * 0.09;
        dot.y += (targetY - dot.y) * 0.09;

        // Desenhar conexões de luz do ponto ao mouse se estiver no raio de atração
        if (mouse.x !== null && mouse.y !== null) {
          const dx = mouse.x - dot.x;
          const dy = mouse.y - dot.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          
          if (dist < mouse.radius - 10) {
            ctx.strokeStyle = `rgba(${rgb}, ${currentOpacity * 0.35 * (1 - dist / mouse.radius)})`;
            ctx.lineWidth = 0.8;
            ctx.beginPath();
            ctx.moveTo(dot.x, dot.y);
            ctx.lineTo(mouse.x, mouse.y);
            ctx.stroke();
          }
        }

        // Desenhar ponto individual
        ctx.fillStyle = `rgba(${rgb}, ${currentOpacity * 0.45})`;
        
        // Brilho reativo no mouse
        if (mouse.x !== null && mouse.y !== null) {
          const dx = mouse.x - dot.x;
          const dy = mouse.y - dot.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < mouse.radius) {
            ctx.fillStyle = `rgba(${themeRef.current === 'violet' ? '129, 140, 248' : rgb}, ${currentOpacity * 0.9})`;
          }
        }

        ctx.beginPath();
        ctx.arc(dot.x, dot.y, 1.2, 0, Math.PI * 2);
        ctx.fill();
      });

      animationFrameId = requestAnimationFrame(draw);
    }

    draw();

    return () => {
      window.removeEventListener('resize', resize);
      window.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseleave', handleMouseLeave);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  const updateSetting = (key, val) => {
    switch (key) {
      case 'theme':
        setTheme(val);
        localStorage.setItem('bg_theme', val);
        break;
      case 'opacity':
        setOpacity(val);
        localStorage.setItem('bg_opacity', val.toString());
        break;
      case 'speed':
        setSpeed(val);
        localStorage.setItem('bg_speed', val.toString());
        break;
      case 'density':
        setDensity(val);
        localStorage.setItem('bg_density', val.toString());
        break;
      case 'glow':
        setGlowEffect(val);
        localStorage.setItem('bg_glow', val.toString());
        break;
      default:
        break;
    }
  };

  return (
    <div className="site-background-container">
      {/* Canvas principal do Matrix Engine Grid */}
      <canvas ref={canvasRef} id="site-background-canvas" />

      {/* Overlay de granulado dinâmico global */}
      <div className="noise-container">
        <div className="noise"></div>
      </div>

      {/* Botão de ajustes discretos */}
      <button 
        className={`bg-control-trigger ${isOpen ? 'active' : ''}`}
        onClick={() => setIsOpen(!isOpen)}
        title="Calibrar Grade Técnica"
      >
        <Sparkles className="glow-icon" size={14} />
      </button>

      {/* Painel de ajustes editoriais */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, x: 300, scale: 0.95 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: 300, scale: 0.95 }}
            transition={{ type: 'spring', damping: 22, stiffness: 150 }}
            className="bg-cyber-panel"
          >
            <div className="bg-panel-header">
              <div className="header-title-wrapper">
                <Sliders className="neon-text" size={14} />
                <h3>GRADE MATEMÁTICA</h3>
              </div>
              <button className="bg-close-btn" onClick={() => setIsOpen(false)}>
                <X size={14} />
              </button>
            </div>

            <p className="bg-panel-desc">
              Calibre o espaçamento e a densidade dos elementos vetoriais em tempo real.
            </p>

            {/* Tema de Cores */}
            <div className="control-row">
              <label>Paleta de Cores (Acento)</label>
              <div className="bg-theme-selectors">
                <button
                  className={`bg-theme-btn ${theme === 'violet' ? 'active' : ''}`}
                  onClick={() => updateSetting('theme', 'violet')}
                >
                  Ametista
                </button>
                <button
                  className={`bg-theme-btn ${theme === 'orange' ? 'active' : ''}`}
                  onClick={() => updateSetting('theme', 'orange')}
                >
                  Terracota
                </button>
                <button
                  className={`bg-theme-btn ${theme === 'neon-green' ? 'active' : ''}`}
                  onClick={() => updateSetting('theme', 'neon-green')}
                >
                  Esmeralda
                </button>
                <button
                  className={`bg-theme-btn ${theme === 'quantum-cyan' ? 'active' : ''}`}
                  onClick={() => updateSetting('theme', 'quantum-cyan')}
                >
                  Cobalto
                </button>
              </div>
            </div>

            {/* Opacidade */}
            <div className="control-row">
              <div className="control-label-row">
                <span>Opacidade dos Pontos</span>
                <span className="value-label">{Math.round(opacity * 100)}%</span>
              </div>
              <input
                type="range"
                className="bg-slider"
                min="0.10"
                max="0.90"
                step="0.05"
                value={opacity}
                onChange={(e) => updateSetting('opacity', parseFloat(e.target.value))}
              />
            </div>

            {/* Velocidade de oscilação */}
            <div className="control-row">
              <div className="control-label-row">
                <span>Frequência / Velocidade</span>
                <span className="value-label">{speed.toFixed(2)} Hz</span>
              </div>
              <input
                type="range"
                className="bg-slider"
                min="0.02"
                max="0.40"
                step="0.02"
                value={speed}
                onChange={(e) => updateSetting('speed', parseFloat(e.target.value))}
              />
            </div>

            {/* Densidade da grade */}
            <div className="control-row">
              <div className="control-label-row">
                <span>Espaçamento da Grade</span>
                <span className="value-label">{density}px</span>
              </div>
              <input
                type="range"
                className="bg-slider"
                min="20"
                max="60"
                step="5"
                value={density}
                onChange={(e) => updateSetting('density', parseInt(e.target.value, 10))}
              />
            </div>

            {/* Brilho Quântico toggle */}
            <div className="control-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: '4px' }}>
              <span>Luz de Status da Grade</span>
              <div 
                onClick={() => updateSetting('glow', !glowEffect)}
                style={{
                  width: '38px', height: '20px', borderRadius: '10px', cursor: 'pointer',
                  background: glowEffect ? 'var(--accent)' : 'var(--border)',
                  position: 'relative', transition: 'all 0.3s var(--ease-cinematic)',
                  border: '1px solid var(--border)'
                }}
              >
                <div style={{
                  width: '14px', height: '14px', borderRadius: '50%', background: '#fff',
                  position: 'absolute', top: '2px', left: glowEffect ? '20px' : '2px',
                  transition: 'all 0.3s var(--ease-cinematic)'
                }} />
              </div>
            </div>

            <button 
              className="bg-panel-hide-btn"
              onClick={() => setIsOpen(false)}
            >
              Fechar Ajustes
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
