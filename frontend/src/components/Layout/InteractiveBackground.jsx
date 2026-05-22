import React, { useEffect, useRef, useState } from 'react';
import { Sliders, Sparkles, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export default function InteractiveBackground() {
  // 1. Estados Reativos com persistência em localStorage
  const [theme, setTheme] = useState(() => localStorage.getItem('bg_theme') || 'orange');
  const [opacity, setOpacity] = useState(() => {
    const val = localStorage.getItem('bg_opacity');
    return val !== null ? parseFloat(val) : 0.35; // Padrão 0.35 do WaveBackground4K
  });
  const [speed, setSpeed] = useState(() => {
    const val = localStorage.getItem('bg_speed');
    return val !== null ? parseFloat(val) : 0.13; // Fator de escala reativo
  });
  const [waveCount, setWaveCount] = useState(() => {
    const val = localStorage.getItem('bg_waveCount');
    return val !== null ? parseInt(val, 10) : 42; // Padrão 42 do WaveBackground4K
  });
  const [waveAmplitude, setWaveAmplitude] = useState(() => {
    const val = localStorage.getItem('bg_waveAmplitude');
    return val !== null ? parseInt(val, 10) : 38; // Padrão 38 do WaveBackground4K
  });
  const [spacing, setSpacing] = useState(() => {
    const val = localStorage.getItem('bg_spacing');
    return val !== null ? parseInt(val, 10) : 35; // Profundidade do Vale (warp)
  });
  const [isOpen, setIsOpen] = useState(false);

  const canvasRef = useRef(null);

  // Auxiliares de cores
  const getThemeColor = (currentTheme) => {
    switch (currentTheme) {
      case 'orange':
        return '#F27D26';
      case 'neon-green':
        return '#00ff88';
      case 'quantum-cyan':
        return '#00d4ff';
      default:
        return '#F27D26';
    }
  };

  const getThemeRgb = (currentTheme) => {
    switch (currentTheme) {
      case 'orange':
        return '242, 125, 38';
      case 'neon-green':
        return '0, 255, 136';
      case 'quantum-cyan':
        return '0, 212, 255';
      default:
        return '242, 125, 38';
    }
  };

  const themeColor = getThemeColor(theme);
  const themeRgb = getThemeRgb(theme);

  // 2. Referências sincronizadas para o loop do Canvas a 60 FPS estáveis sem lag de render React
  const themeRef = useRef(theme);
  const opacityRef = useRef(opacity);
  const speedRef = useRef(speed);
  const waveCountRef = useRef(waveCount);
  const waveAmplitudeRef = useRef(waveAmplitude);
  const spacingRef = useRef(spacing);

  useEffect(() => {
    themeRef.current = theme;
    opacityRef.current = opacity;
    speedRef.current = speed;
    waveCountRef.current = waveCount;
    waveAmplitudeRef.current = waveAmplitude;
    spacingRef.current = spacing;
  }, [theme, opacity, speed, waveCount, waveAmplitude, spacing]);

  // 3. Sincronização cromática em tempo real no documentElement (:root) para design unificado
  useEffect(() => {
    const root = document.documentElement;
    root.style.setProperty('--bg-theme-accent', themeColor);
    root.style.setProperty('--bg-theme-accent-rgb', themeRgb);
    root.style.setProperty('--accent', themeColor);
    root.style.setProperty('--accent-rgb', themeRgb);
    root.style.setProperty('--text-accent', themeColor);
  }, [theme, themeColor, themeRgb]);

  // 4. Renderização do Canvas e animação matemática a 60 FPS
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    let animationFrameId;
    let time = 0;

    function resize() {
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      ctx.scale(dpr, dpr);
    }

    window.addEventListener('resize', resize);
    resize();

    // Converte hexadecimal para RGB
    const hexToRgbStr = (hex) => {
      const clean = hex.replace('#', '');
      const num = parseInt(clean, 16);
      return `${(num >> 16) & 255}, ${(num >> 8) & 255}, ${num & 255}`;
    };

    // Desenho físico com aceleração de GPU
    function draw() {
      if (!canvas) return;
      const w = canvas.clientWidth;
      const h = canvas.clientHeight;

      ctx.clearRect(0, 0, w, h);

      // Lê os valores atuais a partir de referências (Zero lag e 60 FPS constantes)
      const currentTheme = themeRef.current;
      const currentOpacity = opacityRef.current;
      const currentSpeed = speedRef.current;
      const currentWaveCount = waveCountRef.current;
      const currentWaveAmplitude = waveAmplitudeRef.current;
      const currentSpacing = spacingRef.current; // Profundidade do vale

      // Escalar o incremento do time baseando-se na velocidade do controle deslizante
      // 0.13 (padrão) * 0.0046 = ~0.0006 (que é igual a 0.012 * 0.05 do original)
      time += currentSpeed * 0.0046;

      // Desenhar o gradiente de fundo preto topográfico (#050505 a #0f0e0d)
      const bg = ctx.createLinearGradient(0, 0, 0, h);
      bg.addColorStop(0, '#050505');
      bg.addColorStop(1, '#0f0e0d');
      ctx.fillStyle = bg;
      ctx.fillRect(0, 0, w, h);

      // Atributos da linha
      ctx.lineWidth = 0.8;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';

      // Resgatar a cor com base no tema reativo
      const activeColor = getThemeColor(currentTheme);
      const activeColorRgb = hexToRgbStr(activeColor);

      // Algoritmo matemático original do WaveBackground4K.tsx adaptado reativamente
      for (let i = 0; i < currentWaveCount; i++) {
        const ratio = i / (currentWaveCount - 1 || 1);
        const yBase = ratio * h;

        // Modula a opacidade total conforme a opacidade do controle + o fade da profundidade original
        ctx.strokeStyle = `rgba(${activeColorRgb}, ${currentOpacity * (0.15 + (1 - ratio) * 0.85)})`;

        const points = [];
        const segments = 150;
        for (let s = 0; s <= segments; s++) {
          const xr = s / segments;
          const x = xr * w;

          const freq1 = 0.009 * 1.5;
          const freq2 = 0.009 * 3.2;
          const compression = Math.sin(xr * Math.PI) * 1.2;

          // w1 e w2 usam a amplitude de ondas reativa
          const w1 = Math.sin(x * freq1 - time * 0.4 + i * 0.08) * currentWaveAmplitude * compression;
          const w2 = Math.cos(x * freq2 + time * 0.25 - i * 0.12) * (currentWaveAmplitude * 0.45);
          
          // Deslocamento lento das ondas
          const displacement = Math.sin(time * 0.15 + (1 - ratio) * 4.5) * (currentWaveAmplitude * 0.3);
          
          // Vale centralizado em 42% da tela com largura 28%
          const valley = Math.max(0, 1 - (Math.abs(xr - 0.42) / 0.28));
          // O valleyWarp modula a distorção no centro da tela baseado no spacing reativo (profundidade)
          const valleyWarp = Math.sin(valley * Math.PI / 2) * -currentSpacing * (1 + ratio * 0.6);

          const y = yBase + w1 + w2 + displacement + valleyWarp;
          points.push({ x, y });
        }

        ctx.beginPath();
        if (points.length > 0) {
          ctx.moveTo(points[0].x, points[0].y);
          
          for (let p = 1; p < points.length - 1; p++) {
            const xc = (points[p].x + points[p + 1].x) / 2;
            const yc = (points[p].y + points[p + 1].y) / 2;
            ctx.quadraticCurveTo(points[p].x, points[p].y, xc, yc);
          }
          
          // Conecta ao último ponto de forma suave
          ctx.quadraticCurveTo(
            points[points.length - 1].x,
            points[points.length - 1].y,
            points[points.length - 1].x,
            points[points.length - 1].y
          );
        }
        ctx.stroke();
      }

      animationFrameId = requestAnimationFrame(draw);
    }

    draw();

    return () => {
      window.removeEventListener('resize', resize);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  // 5. Funções de Callback reativas que salvam imediatamente no LocalStorage
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
      case 'waveCount':
        setWaveCount(val);
        localStorage.setItem('bg_waveCount', val.toString());
        break;
      case 'waveAmplitude':
        setWaveAmplitude(val);
        localStorage.setItem('bg_waveAmplitude', val.toString());
        break;
      case 'spacing':
        setSpacing(val);
        localStorage.setItem('bg_spacing', val.toString());
        break;
      default:
        break;
    }
  };

  return (
    <div 
      className="site-background-container"
      style={{
        '--bg-theme-accent': themeColor,
        '--bg-theme-accent-rgb': themeRgb
      }}
    >
      {/* Canvas do Fundo WaveBackground4K */}
      <canvas ref={canvasRef} id="site-background-canvas" />

      {/* Botão Flutuante Discreto para Abrir o Painel Holográfico de Ajustes */}
      <button 
        className={`bg-control-trigger ${isOpen ? 'active' : ''}`}
        onClick={() => setIsOpen(!isOpen)}
        title="Ajustes de Efeitos Visuais"
      >
        <Sparkles className="glow-icon" size={16} />
        <span>Efeitos Visuais</span>
      </button>

      {/* Painel Holográfico de Ajustes (Slide & Blur) */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, x: -300, y: 0, scale: 0.95 }}
            animate={{ opacity: 1, x: 0, y: 0, scale: 1 }}
            exit={{ opacity: 0, x: -300, scale: 0.95 }}
            transition={{ type: 'spring', damping: 22, stiffness: 150 }}
            className="bg-cyber-panel"
          >
            <div className="bg-panel-header">
              <div className="header-title-wrapper">
                <Sliders className="neon-text" size={16} />
                <h3>EFEITOS VISUAIS</h3>
              </div>
              <button className="bg-close-btn" onClick={() => setIsOpen(false)}>
                <X size={16} />
              </button>
            </div>

            <p className="bg-panel-desc">
              Calibre o fluxo cibernético do plano de fundo em tempo real. Suas preferências são salvas automaticamente.
            </p>

            {/* Alternar Tema */}
            <div className="control-row">
              <label>Paleta Cromática (Ondas)</label>
              <div className="bg-theme-selectors">
                <button
                  className={`bg-theme-btn ${theme === 'orange' ? 'active' : ''}`}
                  onClick={() => updateSetting('theme', 'orange')}
                >
                  Laranja
                </button>
                <button
                  className={`bg-theme-btn ${theme === 'neon-green' ? 'active' : ''}`}
                  onClick={() => updateSetting('theme', 'neon-green')}
                >
                  Cyber
                </button>
                <button
                  className={`bg-theme-btn ${theme === 'quantum-cyan' ? 'active' : ''}`}
                  onClick={() => updateSetting('theme', 'quantum-cyan')}
                >
                  Ciano
                </button>
              </div>
            </div>

            {/* Opacidade */}
            <div className="control-row">
              <div className="control-label-row">
                <span>Opacidade das Ondas</span>
                <span className="value-label">{Math.round(opacity * 100)}%</span>
              </div>
              <input
                type="range"
                className="bg-slider"
                min="0.05"
                max="0.80"
                step="0.01"
                value={opacity}
                onChange={(e) => updateSetting('opacity', parseFloat(e.target.value))}
              />
            </div>

            {/* Velocidade */}
            <div className="control-row">
              <div className="control-label-row">
                <span>Velocidade de Fluxo</span>
                <span className="value-label">{speed.toFixed(2)}</span>
              </div>
              <input
                type="range"
                className="bg-slider"
                min="0.01"
                max="0.40"
                step="0.01"
                value={speed}
                onChange={(e) => updateSetting('speed', parseFloat(e.target.value))}
              />
            </div>

            {/* Quantidade (Densidade) */}
            <div className="control-row">
              <div className="control-label-row">
                <span>Densidade (Linhas)</span>
                <span className="value-label">{waveCount}</span>
              </div>
              <input
                type="range"
                className="bg-slider"
                min="10"
                max="65"
                step="1"
                value={waveCount}
                onChange={(e) => updateSetting('waveCount', parseInt(e.target.value, 10))}
              />
            </div>

            {/* Amplitude (Altura) */}
            <div className="control-row">
              <div className="control-label-row">
                <span>Altura das Ondas</span>
                <span className="value-label">{waveAmplitude}px</span>
              </div>
              <input
                type="range"
                className="bg-slider"
                min="5"
                max="100"
                step="1"
                value={waveAmplitude}
                onChange={(e) => updateSetting('waveAmplitude', parseInt(e.target.value, 10))}
              />
            </div>

            {/* Profundidade do Vale (Distorção Central) */}
            <div className="control-row">
              <div className="control-label-row">
                <span>Profundidade do Vale</span>
                <span className="value-label">{spacing}px</span>
              </div>
              <input
                type="range"
                className="bg-slider"
                min="0"
                max="80"
                step="2"
                value={spacing}
                onChange={(e) => updateSetting('spacing', parseInt(e.target.value, 10))}
              />
            </div>

            <button 
              className="bg-panel-hide-btn"
              onClick={() => setIsOpen(false)}
            >
              Ocultar Controles
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
