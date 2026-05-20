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
import FutbinCard from '../components/FutbinCard';

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

  // Priorizar imagem da carta do jogador se disponível nos detalhes
  const cardImage = getImageUrl((details?.player_card?.card_image_url) || sbc.image_url);

  return (
    <motion.div 
      layout
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -4, transition: { duration: 0.2 } }}
      className={`card ${expanded ? 'expanded' : ''}`} 
      style={{ 
        display: 'flex', 
        flexDirection: 'column', 
        gap: 0, 
        padding: 0, 
        cursor: 'default', 
        transition: 'all 0.3s ease',
        borderColor: expanded ? 'var(--accent)' : 'rgba(255,255,255,0.1)',
        background: expanded ? 'rgba(0, 255, 136, 0.03)' : 'rgba(255,255,255,0.02)',
        backdropFilter: 'blur(12px)',
        boxShadow: expanded ? '0 8px 32px rgba(0, 255, 136, 0.1)' : 'none',
        overflow: 'hidden'
      }}
    >
      
      {/* Header com Brilho Superior */}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center', 
        padding: '12px 16px', 
        background: 'rgba(255,255,255,0.03)', 
        borderBottom: '1px solid rgba(255,255,255,0.05)',
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
                boxShadow: '0 0 10px rgba(0, 255, 136, 0.4)'
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
        {sbc.raw_card_data ? (() => {
          let cardData;
          try {
            cardData = typeof sbc.raw_card_data === 'string' ? JSON.parse(sbc.raw_card_data) : sbc.raw_card_data;
          } catch { cardData = null; }
          return cardData ? (
            <div style={{
              flexShrink: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              <FutbinCard data={cardData} size="lg" />
            </div>
          ) : (
            <FutbinCard data={null} size="lg" />
          );
        })() : (
          <div style={{ 
            width: '252px', 
            height: '353px',
            flexShrink: 0, 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center',
            background: 'linear-gradient(145deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.01) 100%)',
            borderRadius: 12,
            border: '1px solid rgba(255,255,255,0.08)',
            position: 'relative',
            overflow: 'hidden'
          }}>
            {cardImage ? (
              <motion.img 
                layoutId={`img-${sbc.id}`}
                whileHover={{ scale: 1.05 }}
                src={cardImage} 
                alt={sbc.name} 
                referrerPolicy="no-referrer"
                style={{ width: '85%', height: '85%', objectFit: 'contain', zIndex: 2 }} 
              />
            ) : (
              <LayoutGrid size={80} strokeWidth={1} style={{ opacity: 0.2 }} />
            )}
            {details?.player_card && (
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
                {details.player_card.overall}
              </div>
            )}
          </div>
        )}

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
          borderTop: '1px solid rgba(255,255,255,0.05)', 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center',
          cursor: 'pointer',
          background: expanded ? 'rgba(0, 255, 136, 0.05)' : 'transparent'
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
                    boxShadow: '0 4px 15px rgba(0, 255, 136, 0.2)'
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
    <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 0, padding: 0, overflow: 'hidden', opacity: 0.6 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 16px', background: 'rgba(255,255,255,0.03)', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
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


export default function SbcsPage({ onNavigate }) {
  const api = useApi();
  const [sbcs, setSbcs] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Scraping
  const [isScraping, setIsScraping] = useState(false);
  const [scrapeStatus, setScrapeStatus] = useState(null);
  const pollTimer = useRef(null);
  
  // Filtros
  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('Todos');
  const [sortOption, setSortOption] = useState('cost_desc');

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

  const filteredAndSortedSbcs = useMemo(() => {
    let result = [...sbcs];

    // Categoria
    if (categoryFilter !== 'Todos') {
      result = result.filter(s => s.category === categoryFilter);
    }

    // Busca
    if (debouncedSearch) {
      const lowerSearch = debouncedSearch.toLowerCase();
      result = result.filter(s => 
        s.name.toLowerCase().includes(lowerSearch) || 
        (s.description && s.description.toLowerCase().includes(lowerSearch))
      );
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
        const tA = a.expires_at ? new Date(a.expires_at).getTime() : Infinity;
        const tB = b.expires_at ? new Date(b.expires_at).getTime() : Infinity;
        return tA - tB;
      }
      return 0;
    });

    return result;
  }, [sbcs, debouncedSearch, categoryFilter, sortOption]);

  if (loading || isScraping) {
    return (
      <div className="fade-in" style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 24 }}>
        {isScraping && (
           <div className="card" style={{ textAlign: 'center', borderColor: 'var(--accent)', padding: '32px' }}>
             <h2 style={{ color: 'var(--accent)', marginBottom: '8px' }}>Sincronizando DMEs Automaticamente...</h2>
             <p className="text-secondary" style={{ marginBottom: '16px' }}>
               Descobrindo novos Desafios de Montagem de Elenco na base de dados.
             </p>
             <div style={{ color: 'var(--text-primary)', fontWeight: 600, fontSize: '1.2rem' }}>
               {scrapeStatus?.progress?.current || 0} / {scrapeStatus?.progress?.total || '?'} processados
             </div>
             {scrapeStatus?.message && (
               <div className="text-secondary" style={{ marginTop: '8px', fontSize: '0.9rem' }}>
                 {scrapeStatus.message}
               </div>
             )}
           </div>
        )}
        <div className="skeleton" style={{ height: 60, width: '100%', borderRadius: 8 }}></div>
        <div className="sbc-grid">
          {[1, 2, 3, 4, 5, 6].map(i => <SbcCardSkeleton key={i} />)}
        </div>
      </div>
    );
  }

  return (
    <div className="fade-in" style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 24 }}>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16, alignItems: 'center', background: 'var(--bg-secondary)', padding: 16, borderRadius: 8, border: '1px solid var(--border-primary)' }}>
        
        <input 
          type="text" 
          placeholder="🔍 Buscar DMEs..." 
          className="input"
          style={{ flex: '1 1 250px' }}
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />

        <select 
          className="input" 
          style={{ width: 'auto', flex: '0 1 auto' }}
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
        >
          <option value="Todos">Todas as Categorias</option>
          <option value="Players">Players</option>
          <option value="Upgrades">Upgrades</option>
          <option value="Challenges">Challenges</option>
          <option value="Icons">Icons</option>
        </select>

        <select 
          className="input" 
          style={{ width: 'auto', flex: '0 1 auto' }}
          value={sortOption}
          onChange={(e) => setSortOption(e.target.value)}
        >
          <option value="cost_desc">Custo (Maior &gt; Menor)</option>
          <option value="cost_asc">Custo (Menor &gt; Maior)</option>
          <option value="exp_asc">Expiração (Mais Próximo)</option>
        </select>

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
        <div className="sbc-grid">
          {filteredAndSortedSbcs.map(sbc => (
            <SbcCard key={sbc.id} sbc={sbc} api={api} onNavigate={onNavigate} />
          ))}
        </div>
      )}
    </div>
  );
}

