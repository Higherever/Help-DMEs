import React, { useState, useEffect, useMemo, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Clock, 
  RotateCcw, 
  Coins, 
  LayoutGrid, 
  Trophy, 
  ChevronDown, 
  ChevronUp, 
  Sparkles,
  Info,
  Package as Box
} from 'lucide-react';

import { useApi } from '../hooks/useApi';
import FutbinCardTilt from '../components/FutbinCardTilt';
import GooeySearch from '../components/Search/GooeySearch';


// Componente de Dropdown Customizado Premium (Cyberpunk/Glassmorphism)
function PremiumDropdown({ value, onChange, options }) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);

  const selectedOption = options.find(opt => opt.value === value) || options[0];

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className="premium-dropdown-container" ref={dropdownRef}>
      <button 
        type="button"
        className="premium-dropdown-trigger"
        onClick={() => setIsOpen(!isOpen)}
      >
        <span>{selectedOption.label}</span>
        <ChevronDown 
          size={16} 
          style={{ 
            transition: 'transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
            transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)',
            color: 'var(--accent)'
          }} 
        />
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.ul 
            initial={{ opacity: 0, y: 8, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.98 }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
            className="premium-dropdown-menu"
          >
            {options.map((opt) => (
              <li 
                key={opt.value}
                className={`premium-dropdown-item ${opt.value === value ? 'selected' : ''}`}
                onClick={() => {
                  onChange(opt.value);
                  setIsOpen(false);
                }}
              >
                {opt.label}
              </li>
            ))}
          </motion.ul>
        )}
      </AnimatePresence>
    </div>
  );
}

// Componente SbcCard separado para gerenciar estado de expansão
function SbcCard({ sbc, api, onNavigate }) {
  const [expanded, setExpanded] = useState(false);
  const [details, setDetails] = useState(null);
  const [loadingDetails, setLoadingDetails] = useState(false);

  const getExpiresText = (dateString) => {
    if (!dateString) return '-';
    const expires = new Date(dateString);
    const now = new Date();
    const diffHours = (expires - now) / (1000 * 60 * 60);
    if (diffHours <= 0) return 'Expirado';
    if (diffHours < 24) return `${Math.floor(diffHours)} h`;
    return `${Math.floor(diffHours / 24)} dias`;
  };

  const formatExpiresText = (text) => {
    if (!text || text === '-') return null;
    if (text.toLowerCase() === 'expired') return 'Expirado';
    if (text.toLowerCase().includes('year') || text.toLowerCase().includes('ano')) return null;
    
    let ptText = text.toLowerCase()
      .replace('years', 'anos').replace('year', 'ano')
      .replace('months', 'meses').replace('month', 'mês')
      .replace('weeks', 'semanas').replace('week', 'semana')
      .replace('days', 'dias').replace('day', 'dia')
      .replace('hours', 'h').replace('hour', 'h')
      .replace('mins', 'min').replace('min', 'min');
      
    return `Expira em: ${ptText}`;
  };

  const handleExpand = async (e) => {
    e.stopPropagation();
    if (!expanded && !details) {
      setLoadingDetails(true);
      try {
        const data = await api.get(`/api/sbcs/${sbc.id}`);
        setDetails(data);
      } catch (e) {
        console.error('Erro ao carregar detalhes:', e);
      } finally {
        setLoadingDetails(false);
      }
    }
    setExpanded(!expanded);
  };

  const isChallenge = sbc.category === 'Challenges';
  const isUpgrade = sbc.category === 'Upgrades';

  const getImageUrl = (url) => {
    if (!url) return null;
    if (url.startsWith('http')) return url.replace('cdn3.futbin.com', 'cdn.futbin.com');
    if (url.startsWith('/')) return `${api.API_BASE}${url}`;
    return `${api.API_BASE}/${url}`;
  };

  // Priorizar imagem da carta do jogador (sempre versão FULL local em alta definição do console)
  const rawCardImageUrl = sbc.player_card?.card_image_url || details?.player_card?.card_image_url;
  // rawCardImageUrl é válido como card HD apenas se for um arquivo local de /full/ ou fc_player_ ou sbc_player_
  const isRawCardHD = rawCardImageUrl && !rawCardImageUrl.includes('/sbcs/') && (
    rawCardImageUrl.includes('/full/') || rawCardImageUrl.includes('fc_player_') || rawCardImageUrl.includes('sbc_player_')
  );
  const cardImage = isRawCardHD
    ? getImageUrl(rawCardImageUrl.replace('/small/', '/full/')) 
    : getImageUrl(sbc.image_url);

  // Estado resiliente para gerenciar a imagem de fallback ou card HD físico
  const [cardImgSrc, setCardImgSrc] = useState(cardImage);

  useEffect(() => {
    setCardImgSrc(cardImage);
  }, [cardImage]);

  const handleImgError = () => {
    const fallback = getImageUrl(sbc.image_url);
    if (cardImgSrc !== fallback && fallback) {
      setCardImgSrc(fallback);
    } else {
      setCardImgSrc(null);
    }
  };

  return (
    <motion.div 
      layout
      whileHover={{ y: -6, transition: { duration: 0.2 } }}
      className={`card sbc-card ${expanded ? 'expanded' : ''}`}
    >
      
      {/* Header com Brilho Superior */}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center', 
        padding: '12px 16px', 
        background: 'transparent', 
        borderBottom: '1px solid rgba(255,255,255,0.02)',
        position: 'relative'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {sbc.is_new && (
            <motion.span 
              animate={{ opacity: [0.7, 1, 0.7] }}
              transition={{ repeat: Infinity, duration: 2 }}
              style={{ 
                background: 'var(--accent)', 
                color: '#000', 
                fontSize: '0.6rem', 
                padding: '2px 6px', 
                borderRadius: 4, 
                fontWeight: 800, 
                letterSpacing: '0.05em',
                boxShadow: '0 0 10px rgba(var(--accent-rgb), 0.4)'
              }}
            >
              NOVO
            </motion.span>
          )}
          <div style={{ 
            fontWeight: 700, 
            fontSize: '1rem', 
            color: 'var(--text-primary)', 
            whiteSpace: 'nowrap', 
            overflow: 'hidden', 
            textOverflow: 'ellipsis', 
            maxWidth: '180px',
            letterSpacing: '-0.02em'
          }} title={sbc.name}>
            {sbc.name}
          </div>
        </div>
        <div className="text-mono" style={{ 
          color: 'var(--warning)', 
          fontWeight: 700, 
          fontSize: '1rem', 
          display: 'flex', 
          alignItems: 'center', 
          gap: 6,
          background: 'rgba(255, 184, 0, 0.05)',
          padding: '4px 8px',
          borderRadius: 6,
          border: '1px solid rgba(255, 184, 0, 0.1)'
        }}>
          {sbc.total_cost > 0 ? sbc.total_cost.toLocaleString('pt-BR') : '0'} 
          <Coins size={14} style={{ color: 'var(--warning)' }} />
        </div>
      </div>

      {/* Body */}
      <div style={{ display: 'flex', padding: '16px', gap: 16, flexWrap: 'wrap', justifyContent: 'center' }}>
        {/* Left: Player Card */}
        <div className="neon-border-wrapper">
          <FutbinCardTilt>
            <div style={{ 
              width: '252px', 
              height: '353px',
              flexShrink: 0, 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center',
              background: cardImage ? 'transparent' : 'linear-gradient(145deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.01) 100%)',
              borderRadius: 12,
              border: cardImage ? 'none' : '1px solid rgba(255,255,255,0.08)',
              position: 'relative',
              overflow: 'hidden'
            }}>
              {cardImgSrc ? (
                <motion.img 
                  layoutId={`img-${sbc.id}`}
                  whileHover={{ scale: 1.05 }}
                  src={cardImgSrc} 
                  alt={sbc.name} 
                  onError={handleImgError}
                  referrerPolicy="no-referrer"
                  style={{ width: '100%', height: '100%', objectFit: 'contain', zIndex: 2 }} 
                />
              ) : (
                <LayoutGrid size={80} strokeWidth={1} style={{ opacity: 0.2 }} />
              )}
              {!cardImage && details?.player_card_full && (
                <div style={{ 
                  position: 'absolute', 
                  top: 12, 
                  right: 12, 
                  background: 'var(--accent)', 
                  color: '#000', 
                  fontSize: '1.6rem', 
                  fontWeight: 900, 
                  padding: '2px 10px', 
                  borderRadius: 6, 
                  zIndex: 3 
                }}>
                  {details.player_card_full.overall}
                </div>
              )}
            </div>
          </FutbinCardTilt>
        </div>
        {/* Right: Info Content */}
        <div style={{ flex: 1, minWidth: '200px', display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div style={{ 
            fontSize: '1rem', 
            color: 'var(--text-secondary)', 
            lineHeight: 1.5, 
            display: '-webkit-box', 
            WebkitLineClamp: 6, 
            WebkitBoxOrient: 'vertical', 
            overflow: 'hidden' 
          }} title={sbc.description}>
             {sbc.description || 'Complete este desafio para ganhar recompensas exclusivas.'}
          </div>

          {/* Reward Strip (Miniaturas de recompensas) */}
          <div style={{ display: 'flex', gap: 8, height: 48, overflow: 'hidden' }}>
             {((details?.rewards || []).length > 0) ? (
               details.rewards.map((r, i) => (
                 <img 
                   key={i} 
                   src={getImageUrl(r.image_url)} 
                   title={r.name} 
                   referrerPolicy="no-referrer"
                   style={{ height: '100%', width: 'auto', borderRadius: 4, border: '1px solid rgba(255,255,255,0.1)' }} 
                 />
               ))
             ) : (
               <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 6 }}>
                 <Box size={14} /> {sbc.category}
               </div>
             )}
          </div>
          
          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: '1fr 1fr', 
            gap: '16px', 
            marginTop: 'auto'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <div style={{ padding: 8, background: 'rgba(255,255,255,0.05)', borderRadius: 8 }}>
                <Trophy size={20} className="text-muted" />
              </div>
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                <span style={{ fontSize: '1.2rem', fontWeight: 600, color: 'var(--text-primary)' }}>{sbc.challenges_count}</span>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 700, letterSpacing: '0.05em' }}>DESAFIOS</span>
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              {formatExpiresText(sbc.expires_text || getExpiresText(sbc.expires_at)) && (
                <span style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                  ⏱️ {formatExpiresText(sbc.expires_text || getExpiresText(sbc.expires_at))}
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Footer Info / Expand Trigger */}
      <div 
        onClick={handleExpand}
        style={{ 
          padding: '10px 16px', 
          borderTop: '1px solid rgba(255,255,255,0.02)', 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center',
          cursor: 'pointer',
          background: expanded ? 'rgba(var(--accent-rgb), 0.02)' : 'transparent'
        }}
      >
        <div style={{ display: 'flex', gap: 12 }}>
          {sbc.is_repeatable && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <RotateCcw size={10} style={{ color: 'var(--accent)' }} />
              <span style={{ fontSize: '0.65rem', color: 'var(--accent)', fontWeight: 700 }}>REPETÍVEL</span>
            </div>
          )}
          {sbc.refresh_text && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <Sparkles size={10} style={{ color: 'var(--warning)' }} />
              <span style={{ fontSize: '0.65rem', color: 'var(--warning)', fontWeight: 700 }}>RENOVA EM BREVE</span>
            </div>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4, color: 'var(--text-muted)', fontSize: '0.75rem', fontWeight: 600 }}>
          {expanded ? 'Ocultar' : 'Detalhes'}
          {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </div>
      </div>

      {/* Expanded details with Framer Motion */}
      <AnimatePresence>
        {expanded && (
          <motion.div 
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: 'easeInOut' }}
            style={{ overflow: 'hidden' }}
          >
            <div style={{ padding: '0 16px 16px 16px', display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div style={{ paddingTop: 12, borderTop: '1px solid rgba(255,255,255,0.05)', display: 'flex', flexDirection: 'column', gap: 10 }}>
                {loadingDetails ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    <div className="skeleton" style={{ height: 40, width: '100%', borderRadius: 8 }}></div>
                    <div className="skeleton" style={{ height: 40, width: '100%', borderRadius: 8 }}></div>
                  </div>
                ) : details && details.challenges && details.challenges.length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {details.challenges.map((c, idx) => (
                      <motion.div 
                        initial={{ x: -10, opacity: 0 }}
                        animate={{ x: 0, opacity: 1 }}
                        transition={{ delay: idx * 0.05 }}
                        key={c.id || c.name} 
                        style={{ 
                          fontSize: '0.8rem', 
                          background: 'rgba(255,255,255,0.03)', 
                          padding: '10px 12px', 
                          borderRadius: 8, 
                          border: '1px solid rgba(255,255,255,0.05)' 
                        }}
                      >
                        <div style={{ fontWeight: 600, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span style={{ color: 'var(--text-primary)' }}>{c.name}</span>
                          <span className="text-mono" style={{ color: 'var(--warning)', fontSize: '0.85rem' }}>
                            {c.estimated_cost > 0 ? `${c.estimated_cost.toLocaleString('pt-BR')} 🪙` : ''}
                          </span>
                        </div>
                        {c.rewards && c.rewards.length > 0 && (
                          <div style={{ marginTop: 8, display: 'flex', gap: 6, alignItems: 'center' }}>
                             {c.rewards.map((r, ri) => (
                               <div key={ri} style={{ display: 'flex', alignItems: 'center', gap: 4, background: 'rgba(255,255,255,0.02)', padding: '2px 6px', borderRadius: 4, border: '1px solid rgba(255,255,255,0.05)' }}>
                                 {r.image_url && <img src={getImageUrl(r.image_url)} referrerPolicy="no-referrer" style={{ height: 16, width: 'auto' }} />}
                                 <span style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>{r.name}</span>
                               </div>
                             ))}
                          </div>
                        )}
                      </motion.div>
                    ))}
                  </div>
                ) : (
                  <div style={{ fontSize: '0.8rem', textAlign: 'center', padding: '20px 0', opacity: 0.5 }}>
                    <Info size={24} style={{ margin: '0 auto 8px', display: 'block' }} />
                    Clique em Calcular para ver os requisitos.
                  </div>
                )}
                
                <motion.button 
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  className="btn btn-primary" 
                  style={{ 
                    marginTop: 8, 
                    width: '100%', 
                    height: '42px',
                    fontSize: '0.9rem',
                    fontWeight: 700,
                    boxShadow: '0 4px 15px rgba(var(--accent-rgb), 0.2)'
                  }}
                  onClick={(e) => {
                    e.stopPropagation();
                    localStorage.setItem('selected_sbc_id', sbc.id);
                    onNavigate('calculator');
                  }}
                >
                  <Sparkles size={16} style={{ marginRight: 8 }} />
                  OTIMIZAR ELENCO
                </motion.button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

// Skeleton para os cards enquanto carregam
function SbcCardSkeleton() {
  return (
    <div className="card sbc-card" style={{ opacity: 0.4 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 16px', background: 'transparent', borderBottom: '1px solid rgba(255,255,255,0.02)' }}>
        <div className="skeleton" style={{ height: 20, width: '60%', borderRadius: 4 }}></div>
        <div className="skeleton" style={{ height: 20, width: 60, borderRadius: 4 }}></div>
      </div>
      <div style={{ display: 'flex', padding: '16px', gap: 16, flexWrap: 'wrap', justifyContent: 'center' }}>
        <div className="skeleton" style={{ width: '252px', height: '353px', borderRadius: 12, flexShrink: 0 }}></div>
        <div style={{ flex: 1, minWidth: '200px', display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div className="skeleton" style={{ height: 16, width: '100%', borderRadius: 4 }}></div>
          <div className="skeleton" style={{ height: 16, width: '80%', borderRadius: 4 }}></div>
          <div className="skeleton" style={{ height: 16, width: '50%', borderRadius: 4 }}></div>
          <div style={{ marginTop: 'auto', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', background: 'rgba(0,0,0,0.1)', padding: '12px', borderRadius: 8 }}>
             <div className="skeleton" style={{ height: 32, width: '100%', borderRadius: 4 }}></div>
             <div className="skeleton" style={{ height: 32, width: '100%', borderRadius: 4 }}></div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Componente isolado para o Slider de Custo, garantindo 60 FPS e física de mola real de rotação
function CostSlider({ initialValue, onChangeFinished }) {
  const [localCost, setLocalCost] = useState(initialValue);
  const timeoutRef = useRef(null);

  // Referências para a física de mola elástica (spring physics)
  const percentRef = useRef((initialValue / 2000000) * 100);
  const currentRotationRef = useRef(0);
  const targetRotationRef = useRef(0);
  const velocityRef = useRef(0);
  const animFrameRef = useRef(null);
  const tooltipRef = useRef(null);

  useEffect(() => {
    setLocalCost(initialValue);
    percentRef.current = (initialValue / 2000000) * 100;
  }, [initialValue]);

  // Loop de física elástica rodando a 60 FPS nativos
  useEffect(() => {
    const updatePhysics = () => {
      const diff = targetRotationRef.current - currentRotationRef.current;
      
      // Equação física: força elástica com rigidez de 0.12 e amortecimento de 0.82
      const force = diff * 0.12;
      velocityRef.current = (velocityRef.current + force) * 0.82;
      currentRotationRef.current += velocityRef.current;

      // Suaviza a rotação de volta a 0 quando o arraste cessa
      targetRotationRef.current *= 0.90;

      // Escreve diretamente no DOM para performance extrema a 60 FPS cravados
      if (tooltipRef.current) {
        const percent = percentRef.current;
        tooltipRef.current.style.left = `${percent}%`;
        tooltipRef.current.style.transform = `translateX(-50%) rotate(${currentRotationRef.current}deg)`;
      }

      animFrameRef.current = requestAnimationFrame(updatePhysics);
    };

    animFrameRef.current = requestAnimationFrame(updatePhysics);

    return () => {
      if (animFrameRef.current) {
        cancelAnimationFrame(animFrameRef.current);
      }
    };
  }, []);

  const handleSliderChange = (e) => {
    const val = Number(e.target.value);
    setLocalCost(val);

    // Calcula a variação de posição física (deltaPercent) para alimentar a mola inercial
    const nextPercent = (val / 2000000) * 100;
    const deltaPercent = nextPercent - percentRef.current;
    percentRef.current = nextPercent;

    // A rotação alvo do balão de diálogo é calculada com base na direção e velocidade do arraste
    let targetRot = -deltaPercent * 3.5;
    targetRot = Math.max(-35, Math.min(35, targetRot)); // Trava em 35 graus para segurança estética
    targetRotationRef.current = targetRot;

    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    timeoutRef.current = setTimeout(() => {
      onChangeFinished(val);
    }, 150);
  };

  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  const percent = (localCost / 2000000) * 100;

  return (
    <label className="cost-slider-label-wrapper">
      <div className="cost-slider-header">
        <span>CUSTO MÁXIMO</span>
        <span className="highlight">
          {localCost >= 2000000 ? 'Qualquer Custo' : `${localCost.toLocaleString('pt-BR')} 🪙`}
        </span>
      </div>
      <div className="cost-slider-input-container">
        <input 
          type="range"
          min="0"
          max="2000000"
          step="1000"
          value={localCost}
          onChange={handleSliderChange}
          className="neon-slider-premium"
          style={{ '--percent': `${percent}%` }}
        />
        <output 
          ref={tooltipRef}
          className="neon-slider-tooltip-bubble"
          style={{
            left: `${percent}%`,
            transform: `translateX(-50%) rotate(0deg)`
          }}
        >
          {localCost >= 2000000 ? 'Qualquer Custo' : `${localCost.toLocaleString('pt-BR')} 🪙`}
        </output>
      </div>
    </label>
  );
}

// Extrai a expiração restante em horas de forma resiliente
const getDiffHours = (sbc) => {
  if (sbc.expires_at) {
    const expires = new Date(sbc.expires_at);
    const now = new Date();
    const diff = (expires - now) / (1000 * 60 * 60);
    if (diff > 0) return diff;
  }
  
  // Fallback: tentar parsear a partir do expires_text traduzido do Futbin
  const text = sbc.expires_text || '';
  if (!text) return Infinity; // Sem texto de expiração = longa duração
  
  const lowerText = text.toLowerCase();
  
  if (lowerText.includes('expirado') || lowerText.includes('expired')) {
    return -1;
  }
  
  const numMatch = lowerText.match(/(\d+)/);
  if (!numMatch) {
    return Infinity;
  }
  
  const num = parseInt(numMatch[1], 10);
  
  if (lowerText.includes('dia') || lowerText.includes('day')) {
    return num * 24;
  }
  if (lowerText.includes('h') || lowerText.includes('hour')) {
    return num;
  }
  if (lowerText.includes('semana') || lowerText.includes('week')) {
    return num * 24 * 7;
  }
  if (lowerText.includes('min')) {
    return num / 60;
  }
  
  return Infinity;
};


export default function SbcsPage({ onNavigate }) {
  const api = useApi();
  const [sbcs, setSbcs] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Scraping
  const [isScraping, setIsScraping] = useState(false);
  const [scrapeStatus, setScrapeStatus] = useState(null);
  const pollTimer = useRef(null);

  // Estados e efeitos para a nova Tela de Carregamento Interativa Cibernética 3D
  const [moedasCount, setMoedasCount] = useState(0);
  const [skinIndex, setSkinIndex] = useState(0);
  const [activeTab, setActiveTab] = useState('telemetry');
  const [sparks, setSparks] = useState([]);
  const [tilt, setTilt] = useState({ x: 0, y: 0 });
  const [gpuHeights, setGpuHeights] = useState(Array(18).fill(20));

  // Efeito de oscilação do gráfico da GPU (Aba 2)
  useEffect(() => {
    if (activeTab === 'gpu') {
      const interval = setInterval(() => {
        setGpuHeights(Array(18).fill(0).map(() => Math.floor(Math.random() * 60) + 10));
      }, 120);
      return () => clearInterval(interval);
    }
  }, [activeTab]);

  // Limpar faíscas expiradas
  useEffect(() => {
    if (sparks.length > 0) {
      const timer = setTimeout(() => {
        setSparks(prev => prev.filter(s => Date.now() - s.id < 800));
      }, 800);
      return () => clearTimeout(timer);
    }
  }, [sparks]);
  
  // Filtros
  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('Todos');
  const [sortOption, setSortOption] = useState('cost_desc');
  const [maxCost, setMaxCost] = useState(2000000); // Até 2M
  const [expirationDays, setExpirationDays] = useState('Todos'); // 'Todos', 1, 3, 7
  const [repeatableOnly, setRepeatableOnly] = useState(false); // boolean

  const triggerAutoScrape = async () => {
    setIsScraping(true);
    try {
      const statusRes = await api.get('/api/scrape/status');
      if (statusRes.status !== 'running') {
        const settings = await api.get('/api/settings');
        const source = settings.find(s => s.key === 'default_source')?.value || 'futbin';
        await api.post(`/api/scrape/start?source=${source}`, {});
      }
    } catch (err) {
      console.error('Erro ao iniciar auto-scrape:', err);
      setIsScraping(false);
      setLoading(false);
    }
  };

  useEffect(() => {
    const loadSbcs = async () => {
      try {
        const data = await api.get('/api/sbcs');
        if (data.length === 0) {
          await triggerAutoScrape();
        } else {
          setSbcs(data);
          setLoading(false);
        }
      } catch (e) {
        console.error('Erro ao carregar SBCs:', e);
        setLoading(false);
      }
    };
    loadSbcs();
    
    return () => {
      if (pollTimer.current) clearInterval(pollTimer.current);
    };
  }, []);

  // Polling para scraping se estiver ocorrendo
  useEffect(() => {
    if (isScraping) {
      pollTimer.current = setInterval(async () => {
        try {
          const statusData = await api.get('/api/scrape/status');
          setScrapeStatus(statusData);
          if (statusData.status && statusData.status !== 'running' && statusData.status !== 'pending') {
            clearInterval(pollTimer.current);
            pollTimer.current = null;
            setIsScraping(false);
            
            // Recarrega os SBCs
            const newData = await api.get('/api/sbcs');
            setSbcs(newData);
            setLoading(false);
          }
        } catch (e) {
          console.error("Erro no polling de scraping:", e);
        }
      }, 3000);
    } else {
      if (pollTimer.current) {
        clearInterval(pollTimer.current);
        pollTimer.current = null;
      }
    }
  }, [isScraping]);

  // Debounce para busca
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchTerm);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  // Reclassificação dinâmica e precisa das categorias para corrigir as abas no frontend
  const reclassifiedSbcs = useMemo(() => {
    return sbcs.map(s => {
      const name = (s.name || '').toLowerCase();
      
      // 1. Identificar se entrega um jogador especial fixo
      // SBCs de jogadores reais possuem player_card válido.
      // DMEs que contêm termos como "pick", "escolha" ou "melhoria" de cartas no nome
      // NÃO entregam um jogador especial fixo, mas sim uma ESCOLHA (Player Pick) ou Melhoria (Upgrade).
      const isPickOrPackName = name.includes('pick') || 
                               name.includes('escolha') || 
                               name.includes('1 de') || 
                               name.includes('1 of') || 
                               name.includes('2 de') || 
                               name.includes('2 of') || 
                               name.includes('3 de') || 
                               name.includes('3 of') || 
                               name.includes('4 de') || 
                               name.includes('4 of') || 
                               name.includes('5 de') || 
                               name.includes('5 of') || 
                               name.includes('pacote') || 
                               name.includes('pack') ||
                               name.includes('atualização') ||
                               name.includes('atualizacoes') ||
                               name.includes('upgrade') ||
                               name.includes('melhoria') ||
                               name.includes('melhorias') ||
                               name.includes('login') || 
                               name.includes('criação') || 
                               name.includes('criacao') || 
                               /\b\d{2}\+\b/.test(name);

      const deliversFixedPlayer = s.player_card && !isPickOrPackName;

      // 2. Classificação de Icons fixos (conforme decisão de design do usuário)
      // Icons devem conter estritamente as cartas de Ícones/Heroes fixos.
      const isFixedIcon = deliversFixedPlayer && (
        name.includes('icon') || 
        name.includes('ícone') || 
        name.includes('ídolo') || 
        name.includes('hero') || 
        name.includes('herói') || 
        name.includes('maldini') || 
        name.includes('kaká') || 
        name.includes('kaka') ||
        (s.player_card && (s.player_card.card_type || '').toLowerCase().includes('icon')) ||
        (s.player_card && (s.player_card.card_type || '').toLowerCase().includes('hero'))
      );

      // 3. Determinar categoria final de acordo com a aba mapeada
      let category = 'Upgrades'; // Fallback padrão
      
      if (isFixedIcon) {
        category = 'Icons';
      } else if (deliversFixedPlayer) {
        category = 'Players';
      } else {
        // Se não entrega jogador fixo, dividimos entre Upgrades e Challenges
        const isUpgrade = name.includes('upgrade') || 
                          name.includes('melhoria') || 
                          name.includes('melhorias') || 
                          name.includes('atualização') || 
                          name.includes('atualizacoes') || 
                          name.includes('pick') || 
                          name.includes('escolha') || 
                          name.includes('1 de') || 
                          name.includes('1 of') || 
                          name.includes('pack') || 
                          name.includes('pacote') ||
                          name.includes('provisões') || 
                          name.includes('provisoes') || 
                          name.includes('login') || 
                          name.includes('criação') || 
                          name.includes('criacao') || 
                          /\b\d{2}\+\b/.test(name);
                           
        if (isUpgrade) {
          category = 'Upgrades';
        } else {
          // Se for puzzle/desafio diário ou semanal que entrega pacotes
          const isChallenge = name.includes('desafio') || 
                              name.includes('challenge') || 
                              name.includes('combates marcantes') || 
                              name.includes('marquee') || 
                              name.includes('confrontos') || 
                              name.includes('puzzle') || 
                              name.includes('diário') || 
                              name.includes('diario') || 
                              name.includes('daily');
          if (isChallenge) {
            category = 'Challenges';
          } else {
            // Preservar categoria original ou aplicar fallback inteligente
            category = s.category && s.category.toLowerCase() === 'challenges' ? 'Challenges' : 'Upgrades';
          }
        }
      }

      // Garantir primeira letra em maiúsculo ('Players', 'Upgrades', 'Challenges', 'Icons')
      const formattedCategory = category.charAt(0).toUpperCase() + category.slice(1).toLowerCase();

      return {
        ...s,
        category: formattedCategory
      };
    });
  }, [sbcs]);

  const filteredAndSortedSbcs = useMemo(() => {
    let result = [...reclassifiedSbcs];

    // Categoria
    if (categoryFilter !== 'Todos') {
      result = result.filter(s => s.category && s.category.toLowerCase() === categoryFilter.toLowerCase());
    }

    // Busca
    if (debouncedSearch) {
      const lowerSearch = debouncedSearch.toLowerCase();
      result = result.filter(s => 
        s.name.toLowerCase().includes(lowerSearch) || 
        (s.description && s.description.toLowerCase().includes(lowerSearch))
      );
    }

    // Filtro de Custo Máximo
    if (maxCost < 2000000) {
      result = result.filter(s => (s.total_cost || 0) <= maxCost);
    }

    // Filtro de Repetição
    if (repeatableOnly) {
      result = result.filter(s => s.is_repeatable);
    }

    // Filtro de Expiração Relativa (Consertado com fallback inteligente para expires_text do Futbin)
    if (expirationDays !== 'Todos') {
      result = result.filter(s => {
        const diffHours = getDiffHours(s);
        if (diffHours < 0) return false;
        
        const maxHours = expirationDays * 24;
        return diffHours <= maxHours;
      });
    }

    // Ordenação
    result.sort((a, b) => {
      // Deixar os SBCs diários por último
      const isDaily = (name) => {
        const lower = name.toLowerCase();
        return lower.includes('daily') || lower.includes('diário') || lower.includes('diario');
      };
      
      const aIsDaily = isDaily(a.name);
      const bIsDaily = isDaily(b.name);

      if (aIsDaily && !bIsDaily) return 1;
      if (!aIsDaily && bIsDaily) return -1;

      if (sortOption === 'cost_desc') return (b.total_cost || 0) - (a.total_cost || 0);
      if (sortOption === 'cost_asc') return (a.total_cost || 0) - (b.total_cost || 0);
      if (sortOption === 'exp_asc') {
        const tA = getDiffHours(a) === -1 ? Infinity : (a.expires_at ? new Date(a.expires_at).getTime() : Date.now() + getDiffHours(a) * 60 * 60 * 1000);
        const tB = getDiffHours(b) === -1 ? Infinity : (b.expires_at ? new Date(b.expires_at).getTime() : Date.now() + getDiffHours(b) * 60 * 60 * 1000);
        return tA - tB;
      }
      return 0;
    });

    return result;
  }, [reclassifiedSbcs, debouncedSearch, categoryFilter, sortOption, maxCost, expirationDays, repeatableOnly]);

  if (loading || isScraping) {
    const current = scrapeStatus?.progress?.current || 0;
    const total = scrapeStatus?.progress?.total || 0;
    const percent = total > 0 ? (current / total) * 100 : 0;
    
    // Extrai o nome do jogador em processamento para o scanner de rede
    let currentPlayerName = '';
    if (scrapeStatus?.message) {
      const match = scrapeStatus.message.match(/:\s*(.*)$/);
      if (match && match[1]) {
        currentPlayerName = match[1];
      } else {
        currentPlayerName = scrapeStatus.message;
      }
    }

    const SKINS = [
      { name: 'Amber Orange', stroke: 'var(--accent)', glow: 'rgba(var(--accent-rgb), 0.65)', text: 'var(--accent)' },
      { name: 'Cyber Green', stroke: '#00ff88', glow: 'rgba(0, 255, 136, 0.65)', text: '#00ff88' },
      { name: 'Quantum Cyan', stroke: '#3399ff', glow: 'rgba(51, 153, 255, 0.65)', text: '#3399ff' },
      { name: 'Icon Gold', stroke: '#ffd700', glow: 'rgba(255, 215, 0, 0.65)', text: '#ffd700' },
      { name: 'Glitch Purple', stroke: '#cc00ff', glow: 'rgba(204, 0, 255, 0.65)', text: '#cc00ff' }
    ];
    const activeSkin = SKINS[skinIndex];

    const handleMouseMove = (e) => {
      const rect = e.currentTarget.getBoundingClientRect();
      const width = rect.width;
      const height = rect.height;
      const mouseX = e.clientX - rect.left - width / 2;
      const mouseY = e.clientY - rect.top - height / 2;
      const rX = -(mouseY / (height / 2)) * 20;
      const rY = (mouseX / (width / 2)) * 20;
      setTilt({ x: rX, y: rY });
    };

    const handleMouseLeave = () => {
      setTilt({ x: 0, y: 0 });
    };

    const handleCardClick = (e) => {
      setMoedasCount(prev => prev + 1);
      setSkinIndex(prev => (prev + 1) % SKINS.length);

      const rect = e.currentTarget.getBoundingClientRect();
      const clickX = e.clientX - rect.left;
      const clickY = e.clientY - rect.top;

      const phraseList = [
        '+1 Moeda!', 
        'Fodder!', 
        'Química +1!', 
        'Injetado!', 
        'Skins Glitched!', 
        'Elite Link!', 
        'Decodificado!'
      ];
      const text = phraseList[Math.floor(Math.random() * phraseList.length)];
      
      const newSpark = {
        id: Date.now() + Math.random(),
        x: clickX,
        y: clickY,
        text: text,
        tx: (Math.random() - 0.5) * 160,
        ty: -60 - Math.random() * 80
      };
      
      setSparks(prev => [...prev, newSpark]);
    };

    return (
      <div className="hologram-container fade-in">
        {/* Auroras neon de background sutis */}
        <div style={{
          position: 'absolute',
          top: '30%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          width: '300px',
          height: '300px',
          background: 'radial-gradient(circle, rgba(var(--accent-rgb), 0.05) 0%, transparent 70%)',
          pointerEvents: 'none',
          zIndex: 0
        }} />
        
        {/* ──────── TÍTULO E STATUS DO PROCESSO ──────── */}
        <div style={{ textAlign: 'center', zIndex: 1, width: '100%', maxWidth: '480px', display: 'flex', flexDirection: 'column', gap: 12, alignItems: 'center', marginBottom: 20 }}>
          <div>
            <h2 style={{ 
              fontSize: '1.7rem', 
              fontWeight: 800, 
              color: '#ffffff', 
              letterSpacing: '-0.02em',
              fontFamily: 'var(--font-main)',
              marginBottom: 4
            }}>
              {isScraping ? 'SINCRONIZAÇÃO EM ANDAMENTO' : 'CARREGANDO DMEs'}
            </h2>
            <p style={{ 
              fontSize: '0.85rem', 
              color: 'var(--text-secondary)',
              letterSpacing: '0.02em',
              textTransform: 'uppercase',
              fontWeight: 600,
              opacity: 0.8
            }}>
              {isScraping 
                ? 'Varrendo e decodificando novos desafios globais' 
                : 'Estabelecendo conexões de alta performance'
              }
            </p>
          </div>

          {/* Mini-Game de Cliques e Moedas */}
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center', 
            gap: 10, 
            background: 'rgba(var(--accent-rgb), 0.04)', 
            border: '1px solid rgba(var(--accent-rgb), 0.12)', 
            borderRadius: 12, 
            padding: '6px 14px', 
            boxShadow: '0 0 15px rgba(var(--accent-rgb), 0.05)'
          }}>
            <Coins size={16} style={{ color: 'var(--accent)', animation: 'spin 5s linear infinite' }} />
            <span style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-secondary)' }}>MOEDAS DE TREINO:</span>
            <span style={{ fontFamily: "'Oswald', 'Teko', sans-serif", fontSize: '1.25rem', fontWeight: 700, color: 'var(--accent)' }}>{moedasCount}</span>
          </div>
        </div>

        {/* ──────── CARD FIFA 3D INTERATIVO ──────── */}
        <div 
          className="cyborg-card-3d-wrapper"
          onMouseMove={handleMouseMove}
          onMouseLeave={handleMouseLeave}
          onClick={handleCardClick}
        >
          <div 
            className="cyborg-card-3d"
            style={{
              transform: `rotateX(${tilt.x}deg) rotateY(${tilt.y}deg)`,
            }}
          >
            <svg 
              viewBox="0 0 100 140" 
              style={{ 
                width: '100%', 
                height: '100%', 
                filter: `drop-shadow(0 0 16px ${activeSkin.glow})`,
                overflow: 'visible'
              }}
            >
              <path 
                d="M 50,0 L 88,12 L 100,45 L 100,105 L 50,140 L 0,105 L 0,45 L 12,12 Z" 
                fill="rgba(10, 10, 10, 0.9)" 
                stroke={activeSkin.stroke} 
                strokeWidth="3.5"
                strokeLinejoin="round"
                style={{ transition: 'stroke 0.3s ease' }}
              />
              <path 
                d="M 12,15 L 88,15 M 50,0 L 50,15 M 50,15 L 50,120 M 15,103 L 85,103" 
                fill="none" 
                stroke={activeSkin.stroke} 
                strokeWidth="1.5"
                opacity="0.3"
                style={{ transition: 'stroke 0.3s ease' }}
              />
            </svg>
            <div style={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%) translateZ(15px)',
              backfaceVisibility: 'hidden',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: 6
            }}>
              <Sparkles size={26} style={{ color: activeSkin.text, transition: 'color 0.3s ease' }} />
              <span style={{ fontSize: '0.52rem', fontWeight: 800, letterSpacing: '0.08em', color: activeSkin.text, textTransform: 'uppercase', transition: 'color 0.3s ease', textAlign: 'center', width: '90px' }}>
                {activeSkin.name}
              </span>
            </div>
          </div>
          
          {/* Faíscas sob cliques */}
          {sparks.map(s => (
            <span 
              key={s.id} 
              className="cyborg-card-spark"
              style={{
                left: s.x,
                top: s.y,
                '--tx': `${s.tx}px`,
                '--ty': `${s.ty}px`,
                color: activeSkin.text
              }}
            >
              {s.text}
            </span>
          ))}
        </div>

        {/* ──────── CONTEÚDO DE TEXTO E STATUS ──────── */}
        <div style={{ textAlign: 'center', zIndex: 1, width: '100%', maxWidth: '480px', display: 'flex', flexDirection: 'column', gap: 16 }}>
          
          {/* Estatística de Progresso em Tamanho Gigante (Fonte Teko/Oswald) */}
          {isScraping && (
            <div style={{ 
              display: 'flex', 
              alignItems: 'baseline', 
              justifyContent: 'center', 
              gap: 8, 
              marginTop: 4 
            }}>
              <span style={{ 
                fontFamily: "'Oswald', 'Teko', sans-serif", 
                fontSize: '4.2rem', 
                lineHeight: 1, 
                fontWeight: 700, 
                color: 'var(--accent)',
                textShadow: '0 0 15px rgba(var(--accent-rgb), 0.3)' 
              }}>
                {current}
              </span>
              <span style={{ 
                fontFamily: "'Oswald', 'Teko', sans-serif", 
                fontSize: '2.2rem', 
                color: 'var(--text-muted)',
                fontWeight: 500 
              }}>
                /
              </span>
              <span style={{ 
                fontFamily: "'Oswald', 'Teko', sans-serif", 
                fontSize: '2.8rem', 
                color: 'var(--text-secondary)',
                fontWeight: 600 
              }}>
                {total > 0 ? total : '58'}
              </span>
              <span style={{ 
                fontSize: '0.75rem', 
                color: 'var(--text-muted)', 
                fontWeight: 800, 
                letterSpacing: '0.1em',
                marginLeft: 6
              }}>
                PROCESSADOS
              </span>
            </div>
          )}

          {/* Barra de Progresso Neon */}
          <div style={{ 
            width: '100%', 
            height: '6px', 
            background: 'rgba(255,255,255,0.04)', 
            borderRadius: '3px', 
            overflow: 'hidden', 
            position: 'relative',
            border: '1px solid rgba(255,255,255,0.01)',
            boxShadow: 'inset 0 1px 3px rgba(0,0,0,0.8)'
          }}>
            {isScraping ? (
              // Barra de Progresso Real Reativa
              <motion.div 
                initial={{ width: 0 }}
                animate={{ width: `${percent}%` }}
                transition={{ duration: 0.5, ease: 'easeOut' }}
                style={{
                  height: '100%',
                  background: 'linear-gradient(90deg, #3399ff, var(--accent))',
                  borderRadius: '3px',
                  boxShadow: '0 0 10px rgba(var(--accent-rgb), 0.5)'
                }}
              />
            ) : (
              // Barra de Progresso Indeterminada Infinita
              <motion.div 
                animate={{ 
                  x: ['-100%', '100%'] 
                }}
                transition={{ 
                  repeat: Infinity, 
                  duration: 1.5, 
                  ease: 'easeInOut' 
                }}
                style={{
                  width: '60%',
                  height: '100%',
                  background: 'linear-gradient(90deg, transparent, var(--accent), transparent)',
                  borderRadius: '3px',
                  boxShadow: '0 0 10px rgba(var(--accent-rgb), 0.5)',
                  position: 'absolute'
                }}
              />
            )}
          </div>

          {/* Painel Terminal Hacker de Logs e Telemetria com Abas */}
          <div style={{ width: '100%', marginTop: 8 }}>
            <div className="terminal-tabs">
              <button 
                className={`terminal-tab-btn ${activeTab === 'telemetry' ? 'active' : ''}`}
                onClick={() => setActiveTab('telemetry')}
              >
                Telemetria
              </button>
              <button 
                className={`terminal-tab-btn ${activeTab === 'gpu' ? 'active' : ''}`}
                onClick={() => setActiveTab('gpu')}
              >
                Gráfico CPU/GPU
              </button>
              <button 
                className={`terminal-tab-btn ${activeTab === 'playstyles' ? 'active' : ''}`}
                onClick={() => setActiveTab('playstyles')}
              >
                Playstyles
              </button>
            </div>
            <div className="terminal-content-box">
              {activeTab === 'telemetry' && (
                <>
                  <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.03)', paddingBottom: 4, marginBottom: 4 }}>
                    <span style={{ color: 'var(--accent)', fontWeight: 600 }}>[CONEXÃO SEGURA]</span>
                    <span className="text-mono" style={{ opacity: 0.5 }}>STATUS: ACTIVE</span>
                  </div>
                  
                  {isScraping ? (
                    <>
                      <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                        <span style={{ color: 'var(--accent)' }}>▶</span>
                        <span>[SYS_LINK]: Lendo DMEs locais e do servidor...</span>
                      </div>
                      {currentPlayerName ? (
                        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                          <motion.span 
                            animate={{ opacity: [0.3, 1, 0.3] }}
                            transition={{ repeat: Infinity, duration: 1.2 }}
                            style={{ color: 'var(--warning)' }}
                          >
                            ◉
                          </motion.span>
                          <span>
                            [SCANNING]: <span style={{ color: 'var(--warning)', fontWeight: 600 }}>{currentPlayerName.toUpperCase()}</span>
                          </span>
                        </div>
                      ) : (
                        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                          <span style={{ color: 'var(--info)' }}>◉</span>
                          <span>{scrapeStatus?.message || 'Processando banco de dados...'}</span>
                        </div>
                      )}
                    </>
                  ) : (
                    <>
                      <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                        <span style={{ color: 'var(--accent)' }}>▶</span>
                        <span>[SYS_LOAD]: Alinhando engine de cálculo linear...</span>
                      </div>
                      <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                        <span style={{ color: 'var(--accent)' }}>▶</span>
                        <span>[SYS_CACHE]: Carregando dicionários de futebol PT-BR...</span>
                      </div>
                    </>
                  )}
                </>
              )}

              {activeTab === 'gpu' && (
                <>
                  <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.03)', paddingBottom: 4, marginBottom: 4 }}>
                    <span style={{ color: 'var(--accent)', fontWeight: 600 }}>[TELEMETRIA DE PROCESSAMENTO]</span>
                    <span className="text-mono" style={{ opacity: 0.5 }}>THREAD: LOCK_60FPS</span>
                  </div>
                  <div style={{ display: 'flex', gap: 12, alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 4, textAlign: 'left' }}>
                      <span style={{ fontSize: '0.68rem' }}>CPU LINEAR: <span style={{ color: 'var(--accent)' }}>{(35 + percent * 0.45).toFixed(1)}%</span></span>
                      <span style={{ fontSize: '0.68rem' }}>GPU RENDER: <span style={{ color: '#3399ff' }}>60 FPS estáveis</span></span>
                    </div>
                    <div className="bar-chart-container">
                      {gpuHeights.map((h, i) => (
                        <div 
                          key={i} 
                          className="bar-chart-column" 
                          style={{ 
                            height: `${h}%`,
                            background: i % 2 === 0 ? 'linear-gradient(to top, rgba(var(--accent-rgb), 0.1), var(--accent))' : 'linear-gradient(to top, rgba(51, 153, 255, 0.1), #3399ff)'
                          }} 
                        />
                      ))}
                    </div>
                  </div>
                </>
              )}

              {activeTab === 'playstyles' && (
                <>
                  <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.03)', paddingBottom: 4, marginBottom: 4 }}>
                    <span style={{ color: 'var(--accent)', fontWeight: 600 }}>[PLAYSTYLES INJETADOS]</span>
                    <span className="text-mono" style={{ opacity: 0.5 }}>DECODIFICADOR: OK</span>
                  </div>
                  <div className="playstyles-decoder-grid">
                    <div className={`decoder-badge-item ${percent >= 10 ? 'active' : ''}`}>
                      <Sparkles size={14} style={{ color: percent >= 10 ? 'var(--accent)' : 'var(--text-muted)' }} />
                      <span className="decoder-badge-label">Chute Colocado</span>
                    </div>
                    <div className={`decoder-badge-item ${percent >= 35 ? 'active' : ''}`}>
                      <Sparkles size={14} style={{ color: percent >= 35 ? '#3399ff' : 'var(--text-muted)' }} />
                      <span className="decoder-badge-label">Passe Longo</span>
                    </div>
                    <div className={`decoder-badge-item ${percent >= 65 ? 'active' : ''}`}>
                      <Sparkles size={14} style={{ color: percent >= 65 ? '#ffd700' : 'var(--text-muted)' }} />
                      <span className="decoder-badge-label">Interceptar</span>
                    </div>
                    <div className={`decoder-badge-item ${percent >= 85 ? 'active' : ''}`}>
                      <Sparkles size={14} style={{ color: percent >= 85 ? '#cc00ff' : 'var(--text-muted)' }} />
                      <span className="decoder-badge-label">Implacável</span>
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>

        </div>
      </div>
    );
  }

  // Variantes para animação Staggered (entrada em cascata de 60 FPS acelerada na GPU)
  const gridVariants = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.05
      }
    }
  };

  const cardVariants = {
    hidden: { opacity: 0, y: 20, scale: 0.98 },
    show: { 
      opacity: 1, 
      y: 0, 
      scale: 1,
      transition: {
        type: "spring",
        stiffness: 110,
        damping: 16
      }
    }
  };

  return (
    <div className="fade-in" style={{ padding: '0px 24px 24px 24px', display: 'flex', flexDirection: 'column', gap: 24 }}>
      
      {/* Painel Command Center de Filtros Premium */}
      <div className="command-center-filters">
        <div className="filters-row-primary">
          
          {/* Busca Futurista com Efeito Gooey Viscoso e Elástico */}
          <GooeySearch 
            value={searchTerm} 
            onChange={setSearchTerm} 
            placeholder="Buscar DMEs por nome..." 
            suggestions={['Melhoria', '83+', 'Ícone', 'Elenco', 'Desafio', 'Campanha']}
          />


          {/* Chicletes de Categoria Neon */}
          <div className="category-pills-container">
            {['Todos', 'Players', 'Upgrades', 'Challenges', 'Icons'].map((cat) => (
              <button
                key={cat}
                className={`category-pill ${categoryFilter === cat ? 'active' : ''}`}
                onClick={() => setCategoryFilter(cat)}
              >
                {cat === 'Todos' ? 'Todos' : cat === 'Players' ? 'Jogadores' : cat === 'Upgrades' ? 'Melhorias' : cat === 'Challenges' ? 'Desafios' : cat}
              </button>
            ))}
          </div>

          {/* Ordenação Premium */}
          <PremiumDropdown 
            value={sortOption}
            onChange={setSortOption}
            options={[
              { value: 'cost_desc', label: 'Custo: Maior ➔ Menor' },
              { value: 'cost_asc', label: 'Custo: Menor ➔ Maior' },
              { value: 'exp_asc', label: 'Expiração Próxima' }
            ]}
          />

        </div>

        {/* Segunda Linha: Filtros Avançados Inteligentes */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16, alignItems: 'center', marginTop: 8 }}>
          
          {/* Slider de Custo Dinâmico Premium com Tooltip Flutuante 3D Isolado a 60 FPS */}
          <CostSlider 
            initialValue={maxCost} 
            onChangeFinished={setMaxCost} 
          />

          {/* Filtros Rápidos de Expiração e Repetição */}
          <div className="quick-toggle-container">
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.05em', marginRight: 4 }}>EXPIRAÇÃO</span>
            
            <button 
              className={`quick-toggle-btn ${expirationDays === 'Todos' ? 'active' : ''}`}
              onClick={() => setExpirationDays('Todos')}
            >
              Tudo
            </button>
            <button 
              className={`quick-toggle-btn ${expirationDays === 1 ? 'active warning-color' : ''}`}
              onClick={() => setExpirationDays(1)}
            >
              <Clock size={12} /> 24h
            </button>
            <button 
              className={`quick-toggle-btn ${expirationDays === 3 ? 'active warning-color' : ''}`}
              onClick={() => setExpirationDays(3)}
            >
              3 dias
            </button>
            <button 
              className={`quick-toggle-btn ${expirationDays === 7 ? 'active' : ''}`}
              onClick={() => setExpirationDays(7)}
            >
              7 dias
            </button>

            <div style={{ width: 1, height: 24, background: 'rgba(255,255,255,0.06)', margin: '0 8px' }} />

            <button 
              className={`quick-toggle-btn accent-color ${repeatableOnly ? 'active' : ''}`}
              onClick={() => setRepeatableOnly(!repeatableOnly)}
            >
              <RotateCcw size={12} /> Apenas Repetíveis
            </button>
          </div>

        </div>
      </div>

      {filteredAndSortedSbcs.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '48px 24px', borderColor: 'var(--border-accent)', marginTop: 24 }}>
          <div style={{ fontSize: '3rem', marginBottom: 16 }}>🎯</div>
          <div style={{ fontSize: '1.2rem', fontWeight: 600, marginBottom: 8 }}>Nenhum DME encontrado</div>
          <div className="text-secondary" style={{ marginBottom: 24 }}>
            Verifique seus filtros ou tente sincronizar manualmente.
          </div>
          <button className="btn btn-primary" onClick={triggerAutoScrape}>
            🔄 Sincronizar Agora
          </button>
        </div>
      ) : (
        <motion.div 
          className="sbc-grid"
          variants={gridVariants}
          initial="hidden"
          animate="show"
        >
          {filteredAndSortedSbcs.map(sbc => (
            <motion.div key={sbc.id} variants={cardVariants} layout>
              <SbcCard sbc={sbc} api={api} onNavigate={onNavigate} />
            </motion.div>
          ))}
        </motion.div>
      )}
    </div>
  );
}

