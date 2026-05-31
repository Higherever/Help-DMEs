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
          size={14} 
          style={{ 
            transition: 'transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
            transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)',
            color: 'var(--text-secondary)'
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

// Componente de CostSlider Refatorado de Forma Minimalista
function CostSlider({ initialValue, onChangeFinished }) {
  const [localCost, setLocalCost] = useState(initialValue);
  const timeoutRef = useRef(null);

  useEffect(() => {
    setLocalCost(initialValue);
  }, [initialValue]);

  const handleSliderChange = (e) => {
    const val = Number(e.target.value);
    setLocalCost(val);

    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    timeoutRef.current = setTimeout(() => {
      onChangeFinished(val);
    }, 150);
  };

  const percent = (localCost / 2000000) * 100;

  return (
    <div className="cyber-cost-slider">
      <div className="slider-meta-header">
        <span className="slider-title font-mono">CUSTO MÁXIMO</span>
        <span className="slider-value font-mono">
          {localCost >= 2000000 ? 'AO INFINITO E ALÉM' : `${localCost.toLocaleString('pt-BR')} 🪙`}
        </span>
      </div>
      <div className="slider-track-container">
        <input 
          type="range"
          min="0"
          max="2000000"
          step="10000"
          value={localCost}
          onChange={handleSliderChange}
          className="cyber-range-input"
          style={{ '--percent': `${percent}%` }}
        />
        <div className="slider-tick-labels font-mono">
          <span>0</span>
          <span>1M</span>
          <span>2M</span>
        </div>
      </div>
    </div>
  );
}

// Card SBC Destacado (FeaturedSbcCard) - Layout Horizontal de Revista de Luxo
function FeaturedSbcCard({ sbc, api, onNavigate }) {
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
      
    return ptText;
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

  const getImageUrl = (url) => {
    if (!url) return null;
    if (url.startsWith('http')) return url.replace('cdn3.futbin.com', 'cdn.futbin.com');
    if (url.startsWith('/')) return `${api.API_BASE}${url}`;
    return `${api.API_BASE}/${url}`;
  };

  const rawCardImageUrl = sbc.player_card?.card_image_url || details?.player_card?.card_image_url;
  const isRawCardHD = rawCardImageUrl && !rawCardImageUrl.includes('/sbcs/') && (
    rawCardImageUrl.includes('/full/') || rawCardImageUrl.includes('fc_player_') || rawCardImageUrl.includes('sbc_player_')
  );
  const cardImage = isRawCardHD
    ? getImageUrl(rawCardImageUrl.replace('/small/', '/full/')) 
    : getImageUrl(sbc.image_url);

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

  const expiresText = formatExpiresText(sbc.expires_text || getExpiresText(sbc.expires_at));

  return (
    <div className={`featured-sbc-card ${expanded ? 'expanded' : ''}`}>
      <div className="featured-card-body">
        {/* Lado Esquerdo: Player Card (Compactado e com tilt 3D) */}
        <div className="featured-card-visual">
          <FutbinCardTilt>
            <div className="featured-card-frame">
              {cardImgSrc ? (
                <motion.img 
                  layoutId={`img-${sbc.id}`}
                  src={cardImgSrc} 
                  alt={sbc.name} 
                  onError={handleImgError}
                  referrerPolicy="no-referrer"
                  className="featured-card-image"
                />
              ) : (
                <LayoutGrid size={50} strokeWidth={1} style={{ opacity: 0.15, color: 'var(--text-secondary)' }} />
              )}
            </div>
          </FutbinCardTilt>
        </div>

        {/* Lado Direito: Info Content */}
        <div className="featured-card-info">
          {/* Header */}
          <div className="featured-info-header">
            <div className="featured-title-row">
              {sbc.is_new && (
                <span className="featured-new-badge font-mono">NOVO</span>
              )}
              <h2 className="featured-name font-serif italic" title={sbc.name}>
                {sbc.name}
              </h2>
            </div>
            <div className="featured-cost font-mono">
              <span>{sbc.total_cost > 0 ? sbc.total_cost.toLocaleString('pt-BR') : '0'}</span>
              <Coins size={14} style={{ color: 'var(--warning)' }} />
            </div>
          </div>

          {/* Descrição */}
          <p className="featured-description font-sans">
            {sbc.description || 'Desafio especial para a obtenção de itens de jogador de alto nível no mercado.'}
          </p>

          {/* Recompensa & Metadados */}
          <div className="featured-metadata-row">
            {/* Rewards */}
            <div className="featured-rewards-strip">
              {((details?.rewards || []).length > 0) ? (
                details.rewards.map((r, i) => (
                  <img 
                    key={i} 
                    src={getImageUrl(r.image_url)} 
                    title={r.name} 
                    alt={r.name}
                    referrerPolicy="no-referrer"
                    className="featured-reward-img"
                  />
                ))
              ) : (
                <div className="featured-category-badge font-mono">
                  <Box size={12} />
                  <span>{sbc.category.toUpperCase()}</span>
                </div>
              )}
            </div>

            {/* Desafios e Expiração */}
            <div className="featured-stats-group font-mono">
              <div className="featured-stat-item">
                <Trophy size={13} />
                <span>{sbc.challenges_count} {sbc.challenges_count === 1 ? 'DESAFIO' : 'DESAFIOS'}</span>
              </div>
              {expiresText && (
                <div className="featured-stat-item warn">
                  <Clock size={13} />
                  <span>{expiresText.toUpperCase()}</span>
                </div>
              )}
            </div>
          </div>

          {/* Actions */}
          <div className="featured-actions-row">
            <div className="featured-badges-left">
              {sbc.is_repeatable && (
                <span className="badge-repeatable font-mono">
                  <RotateCcw size={10} /> REPETÍVEL
                </span>
              )}
              {sbc.refresh_text && (
                <span className="badge-refresh font-mono">
                  <Sparkles size={10} /> RENOVA
                </span>
              )}
            </div>
            <button 
              type="button" 
              className="featured-expand-btn font-mono" 
              onClick={handleExpand}
            >
              <span>{expanded ? 'OCULTAR' : 'DETALHES'}</span>
              <ChevronDown 
                size={14} 
                style={{ 
                  transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)',
                  transition: 'transform 0.25s var(--ease-cinematic)'
                }} 
              />
            </button>
          </div>
        </div>
      </div>

      {/* Detalhes Expandidos com Animação */}
      <AnimatePresence>
        {expanded && (
          <motion.div 
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: 'easeInOut' }}
            className="featured-expanded-panel"
          >
            <div className="expanded-inner-content">
              {loadingDetails ? (
                <div className="expanded-skeleton-loader">
                  <div className="skeleton-bar"></div>
                  <div className="skeleton-bar short"></div>
                </div>
              ) : details && details.challenges && details.challenges.length > 0 ? (
                <div className="expanded-challenges-list">
                  {details.challenges.map((c, idx) => (
                    <motion.div 
                      initial={{ x: -10, opacity: 0 }}
                      animate={{ x: 0, opacity: 1 }}
                      transition={{ delay: idx * 0.05 }}
                      key={c.id || c.name} 
                      className="expanded-challenge-row"
                    >
                      <div className="challenge-main-info font-mono">
                        <span className="challenge-name">{c.name}</span>
                        <span className="challenge-cost">
                          {c.estimated_cost > 0 ? `${c.estimated_cost.toLocaleString('pt-BR')} 🪙` : 'Requisitos Especiais'}
                        </span>
                      </div>
                      {c.rewards && c.rewards.length > 0 && (
                        <div className="challenge-rewards-row">
                          {c.rewards.map((r, ri) => (
                            <div key={ri} className="challenge-reward-pill font-mono">
                              {r.image_url && <img src={getImageUrl(r.image_url)} referrerPolicy="no-referrer" alt="" />}
                              <span>{r.name}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </motion.div>
                  ))}
                </div>
              ) : (
                <div className="expanded-empty-state font-mono">
                  <Info size={14} />
                  <span>Clique em calcular rota para otimizar.</span>
                </div>
              )}
              
              <button 
                type="button"
                className="expanded-calc-btn font-mono"
                onClick={(e) => {
                  e.stopPropagation();
                  localStorage.setItem('selected_sbc_id', sbc.id);
                  onNavigate('calculator');
                }}
              >
                CALCULAR ROTA DE OTIMIZAÇÃO
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
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

  // Estados e efeitos para a Tela de Carregamento Interativa Cibernética 3D
  const [moedasCount, setMoedasCount] = useState(0);
  const [skinIndex, setSkinIndex] = useState(0);
  const [activeTab, setActiveTab] = useState('telemetry');
  const [sparks, setSparks] = useState([]);
  const [tilt, setTilt] = useState({ x: 0, y: 0 });
  const [gpuHeights, setGpuHeights] = useState(Array(18).fill(20));

  // Efeito de oscilação do gráfico da GPU
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

      let category = 'Upgrades'; // Fallback padrão
      
      if (isFixedIcon) {
        category = 'Icons';
      } else if (deliversFixedPlayer) {
        category = 'Players';
      } else {
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
            category = s.category && s.category.toLowerCase() === 'challenges' ? 'Challenges' : 'Upgrades';
          }
        }
      }

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

    // Filtro de Expiração Relativa
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
      { name: 'Selo Ametista', stroke: 'var(--text-primary)', glow: 'rgba(79, 70, 229, 0.2)', text: 'var(--accent)' },
      { name: 'Selo Terracota', stroke: 'var(--text-primary)', glow: 'rgba(180, 83, 9, 0.2)', text: '#b45309' },
      { name: 'Selo Esmeralda', stroke: 'var(--text-primary)', glow: 'rgba(4, 120, 87, 0.2)', text: '#047857' },
      { name: 'Selo Cobalto', stroke: 'var(--text-primary)', glow: 'rgba(3, 105, 161, 0.2)', text: '#0369a1' }
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
        <div style={{
          position: 'absolute',
          top: '30%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          width: '300px',
          height: '300px',
          background: 'radial-gradient(circle, rgba(83, 83, 82, 0.03) 0%, transparent 70%)',
          pointerEvents: 'none',
          zIndex: 0
        }} />
        
        <div style={{ textAlign: 'center', zIndex: 1, width: '100%', maxWidth: '480px', display: 'flex', flexDirection: 'column', gap: 12, alignItems: 'center', marginBottom: 20 }}>
          <div>
            <h2 style={{ 
              fontSize: '1.7rem', 
              fontWeight: 800, 
              color: 'var(--text-primary)', 
              letterSpacing: '-0.02em',
              fontFamily: 'var(--font-serif)',
              fontStyle: 'italic',
              marginBottom: 4
            }}>
              {isScraping ? 'Sincronização em Andamento' : 'Carregando DMEs'}
            </h2>
            <p style={{ 
              fontSize: '0.78rem', 
              color: 'var(--text-secondary)',
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              fontWeight: 700,
              opacity: 0.8
            }}>
              {isScraping 
                ? 'Varrendo e estruturando novos desafios globais' 
                : 'Estabelecendo conexões de alta performance'
              }
            </p>
          </div>

          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center', 
            gap: 10, 
            background: 'var(--bg-tertiary)', 
            border: '1.5px solid var(--text-primary)', 
            borderRadius: 'var(--radius-xs)', 
            padding: '6px 14px',
            boxShadow: '2px 2px 0px var(--text-secondary)'
          }}>
            <Coins size={16} style={{ color: 'var(--accent)', animation: 'spin 5s linear infinite' }} />
            <span style={{ fontSize: '0.72rem', fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--text-secondary)' }}>MOEDAS DE TREINO:</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-primary)' }}>{moedasCount}</span>
          </div>
        </div>

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
                filter: 'drop-shadow(3px 3px 0px rgba(83, 83, 82, 0.35))',
                overflow: 'visible'
              }}
            >
              <path 
                d="M 50,0 L 88,12 L 100,45 L 100,105 L 50,140 L 0,105 L 0,45 L 12,12 Z" 
                fill="var(--bg-tertiary)" 
                stroke="var(--text-primary)" 
                strokeWidth="1.8"
                strokeLinejoin="round"
                style={{ transition: 'stroke 0.3s ease' }}
              />
              <path 
                d="M 12,15 L 88,15 M 50,0 L 50,15 M 50,15 L 50,120 M 15,103 L 85,103" 
                fill="none" 
                stroke="var(--text-secondary)" 
                strokeWidth="1.0"
                opacity="0.4"
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

        <div style={{ textAlign: 'center', zIndex: 1, width: '100%', maxWidth: '480px', display: 'flex', flexDirection: 'column', gap: 16 }}>
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
                  <div style={{ display: 'flex', justifycontent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.03)', paddingBottom: 4, marginBottom: 4 }}>
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
                  <div style={{ display: 'flex', justifycontent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.03)', paddingBottom: 4, marginBottom: 4 }}>
                    <span style={{ color: 'var(--accent)', fontWeight: 600 }}>[TELEMETRIA DE PROCESSAMENTO]</span>
                    <span className="text-mono" style={{ opacity: 0.5 }}>THREAD: LOCK_60FPS</span>
                  </div>
                  <div style={{ display: 'flex', gap: 12, alignItems: 'center', justifycontent: 'space-between', width: '100%' }}>
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
                  <div style={{ display: 'flex', justifycontent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.03)', paddingBottom: 4, marginBottom: 4 }}>
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

  const gridVariants = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.04
      }
    }
  };

  const cardVariants = {
    hidden: { opacity: 0, y: 15, scale: 0.99 },
    show: { 
      opacity: 1, 
      y: 0, 
      scale: 1,
      transition: {
        type: "spring",
        stiffness: 130,
        damping: 18
      }
    }
  };

  return (
    <div className="sbc-page-container fade-in">
      
      {/* ── BARRA LATERAL DE FILTROS ULTRA-FINA (SIDEBAR) ── */}
      <aside className="sbc-sidebar-filters">
        <div className="sidebar-filters-inner">
          <div className="sidebar-section-header">
            <span className="sidebar-serif-title font-serif italic">Filtragem Analítica</span>
            <span className="sidebar-mono-sub font-mono">SYS_CATALOG_v2.5</span>
          </div>

          <div className="sidebar-divider" />

          {/* Busca Gooey */}
          <div className="sidebar-filter-item">
            <span className="filter-label font-mono">BUSCA DE TERMO</span>
            <GooeySearch 
              value={searchTerm} 
              onChange={setSearchTerm} 
              placeholder="Buscar DMEs..." 
              suggestions={['Melhoria', '83+', 'Ícone', 'Elenco', 'Desafio']}
            />
          </div>

          <div className="sidebar-divider" />

          {/* Ordenação */}
          <div className="sidebar-filter-item">
            <span className="filter-label font-mono">ORDENAÇÃO</span>
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

          <div className="sidebar-divider" />

          {/* Slider de Custo Máximo */}
          <div className="sidebar-filter-item">
            <CostSlider 
              initialValue={maxCost} 
              onChangeFinished={setMaxCost} 
            />
          </div>

          <div className="sidebar-divider" />

          {/* Filtros de Expiração */}
          <div className="sidebar-filter-item">
            <span className="filter-label font-mono">EXPIRAÇÃO EM DIAS</span>
            <div className="sidebar-expire-buttons">
              <button 
                type="button"
                className={`sidebar-expire-btn ${expirationDays === 'Todos' ? 'active' : ''}`}
                onClick={() => setExpirationDays('Todos')}
              >
                Tudo
              </button>
              <button 
                type="button"
                className={`sidebar-expire-btn ${expirationDays === 1 ? 'active warning' : ''}`}
                onClick={() => setExpirationDays(1)}
              >
                24h
              </button>
              <button 
                type="button"
                className={`sidebar-expire-btn ${expirationDays === 3 ? 'active warning' : ''}`}
                onClick={() => setExpirationDays(3)}
              >
                3d
              </button>
              <button 
                type="button"
                className={`sidebar-expire-btn ${expirationDays === 7 ? 'active' : ''}`}
                onClick={() => setExpirationDays(7)}
              >
                7d
              </button>
            </div>
          </div>

          <div className="sidebar-divider" />

          {/* Repetíveis */}
          <div className="sidebar-filter-item">
            <button 
              type="button"
              className={`sidebar-toggle-btn ${repeatableOnly ? 'active' : ''}`}
              onClick={() => setRepeatableOnly(!repeatableOnly)}
            >
              <RotateCcw size={12} />
              <span>APENAS REPETÍVEIS</span>
            </button>
          </div>
        </div>
      </aside>

      {/* ── FEED DE CONTEÚDO PRINCIPAL (DIREITO) ── */}
      <main className="sbc-main-feed">
        {/* Cabeçalho Editorial Dramático */}
        <header className="sbc-editorial-header">
          <div className="header-meta-series font-mono">[ OTIMIZADOR DE DESAFIOS ]</div>
          <h1 className="header-editorial-title font-serif italic">
            Desafios de Montagem de Elenco
          </h1>
          <p className="header-editorial-desc font-sans">
            Catálogo estatístico de SBCs ativos estruturado sob a lógica de análise de portfólio.
          </p>
          <div className="header-border-line" />
        </header>

        {/* Abas Superiores de Categoria (Proporção Áurea) */}
        <div className="category-tabs-container">
          {['Todos', 'Players', 'Upgrades', 'Challenges', 'Icons'].map((cat) => (
            <button
              key={cat}
              type="button"
              className={`category-tab-btn ${categoryFilter === cat ? 'active' : ''}`}
              onClick={() => setCategoryFilter(cat)}
            >
              {cat === 'Todos' ? 'Todos DMEs' : cat === 'Players' ? 'Jogadores' : cat === 'Upgrades' ? 'Melhorias' : cat === 'Challenges' ? 'Desafios' : cat}
            </button>
          ))}
        </div>

        {filteredAndSortedSbcs.length === 0 ? (
          <div className="empty-state-portfolio">
            <div className="empty-icon font-mono">Ø</div>
            <h3 className="empty-title font-serif italic">Nenhum DME catalogado</h3>
            <p className="empty-desc font-sans font-mono">FILTRO EXTREMO / SEM RESULTADOS ENCONTRADOS.</p>
            <button type="button" className="btn-sync-action font-mono" onClick={triggerAutoScrape}>
              🔄 SINC_BASE_DADOS
            </button>
          </div>
        ) : (
          <motion.div 
            className="sbc-portfolio-layout"
            variants={gridVariants}
            initial="hidden"
            animate="show"
          >
            {filteredAndSortedSbcs.map(sbc => {
              return (
                <motion.div 
                  key={sbc.id} 
                  variants={cardVariants} 
                  layout
                  className="portfolio-featured-item"
                >
                  <FeaturedSbcCard sbc={sbc} api={api} onNavigate={onNavigate} />
                </motion.div>
              );
            })}
          </motion.div>
        )}
      </main>
    </div>
  );
}
