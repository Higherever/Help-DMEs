import React, { useState, useEffect, useMemo, useRef } from 'react';
import { useApi } from '../hooks/useApi';

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
    if (diffHours < 24) return `em ${Math.floor(diffHours)}h`;
    return `em ${Math.floor(diffHours / 24)} dias`;
  };

  const handleExpand = async () => {
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
  const fallbackIcon = isChallenge ? '🧩' : isUpgrade ? '⬆️' : '👤';

  return (
    <div className={`card ${expanded ? 'expanded' : ''}`} style={{ display: 'flex', flexDirection: 'column', gap: 0, padding: 0, cursor: 'pointer', transition: 'border-color 0.2s', borderColor: expanded ? 'var(--accent)' : 'var(--border-primary)', overflow: 'hidden' }} onClick={handleExpand}>
      
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 16px', background: 'rgba(255,255,255,0.03)', borderBottom: '1px solid var(--border-primary)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {sbc.is_new && <span style={{ background: 'var(--danger)', color: '#fff', fontSize: '0.65rem', padding: '2px 4px', borderRadius: 2, fontWeight: 700, letterSpacing: '0.05em' }}>NOVO</span>}
          <div style={{ fontWeight: 600, fontSize: '0.95rem', color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '200px' }} title={sbc.name}>{sbc.name}</div>
        </div>
        <div className="text-mono" style={{ color: 'var(--warning)', fontWeight: 600, fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: 4 }}>
          {sbc.total_cost > 0 ? sbc.total_cost.toLocaleString('pt-BR') : '0'} <span style={{ fontSize: '1.1rem' }}>🪙</span>
        </div>
      </div>

      {/* Body */}
      <div style={{ display: 'flex', padding: '16px', gap: 16 }}>
        {/* Left: Image */}
        <div style={{ width: '80px', flexShrink: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
          {sbc.image_url ? (
            <img src={sbc.image_url} alt={sbc.name} style={{ width: '100%', height: 'auto', objectFit: 'contain' }} />
          ) : (
            <div style={{ width: '100%', aspectRatio: '1/1.2', background: 'var(--bg-tertiary)', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '2rem' }}>
               {fallbackIcon}
            </div>
          )}
        </div>

        {/* Right: Info Grid */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', lineHeight: 1.3, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }} title={sbc.description}>
             {sbc.description || 'Complete este desafio para ganhar recompensas.'}
          </div>
          
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginTop: 'auto', background: 'rgba(0,0,0,0.2)', padding: '8px 4px', borderRadius: 6, border: '1px solid rgba(255,255,255,0.05)' }}>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
              <span style={{ fontSize: '0.6rem', color: 'var(--text-muted)', letterSpacing: '0.05em' }}>DESAFIOS</span>
              <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)' }}>{sbc.challenges_count}</span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
              <span style={{ fontSize: '0.6rem', color: 'var(--text-muted)', letterSpacing: '0.05em' }}>EXPIRA</span>
              <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)' }}>{getExpiresText(sbc.expires_at)}</span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: 6 }}>
              <span style={{ fontSize: '0.6rem', color: 'var(--text-muted)', letterSpacing: '0.05em' }}>REPETÍVEL</span>
              <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)' }}>{sbc.is_repeatable ? 'Sim' : '-'}</span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: 6 }}>
              <span style={{ fontSize: '0.6rem', color: 'var(--text-muted)', letterSpacing: '0.05em' }}>ATUALIZA EM</span>
              <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)' }}>-</span>
            </div>
          </div>
        </div>
      </div>

      {/* Expanded details */}
      {expanded && (
        <div style={{ padding: '0 16px 16px 16px', display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div style={{ paddingTop: 12, borderTop: '1px solid var(--border-secondary)', display: 'flex', flexDirection: 'column', gap: 8 }}>
            {loadingDetails ? (
              <div className="skeleton" style={{ height: 60, width: '100%', borderRadius: 4 }}></div>
            ) : details && details.challenges && details.challenges.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {details.challenges.map(c => (
                  <div key={c.id || c.name} style={{ fontSize: '0.85rem', background: 'var(--bg-primary)', padding: 8, borderRadius: 4, border: '1px solid var(--border-secondary)' }}>
                    <div style={{ fontWeight: 600, display: 'flex', justifyContent: 'space-between' }}>
                      <span>{c.name}</span>
                      <span className="text-mono text-secondary">
                        {c.cost > 0 ? `🪙 ${c.cost.toLocaleString('pt-BR')}` : ''}
                      </span>
                    </div>
                    {c.rewards && c.rewards.length > 0 && (
                      <div className="text-secondary" style={{ fontSize: '0.75rem', marginTop: 4 }}>
                        🎁 {c.rewards.map(r => r.name).join(', ')}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-secondary" style={{ fontSize: '0.85rem', textAlign: 'center' }}>Nenhum desafio encontrado.</div>
            )}
            
            <button 
              className="btn btn-primary" 
              style={{ marginTop: 8, width: '100%' }}
              onClick={(e) => {
                e.stopPropagation(); // Previne fechar o card
                localStorage.setItem('selected_sbc_id', sbc.id);
                onNavigate('calculator');
              }}
            >
              🧮 Calcular DMEs
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// Skeleton para os cards enquanto carregam
function SbcCardSkeleton() {
  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 0, padding: 0, overflow: 'hidden' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 16px', background: 'rgba(255,255,255,0.03)', borderBottom: '1px solid var(--border-primary)' }}>
        <div className="skeleton" style={{ height: 20, width: '60%', borderRadius: 4 }}></div>
        <div className="skeleton" style={{ height: 16, width: 40, borderRadius: 4 }}></div>
      </div>
      <div style={{ display: 'flex', padding: '16px', gap: 16 }}>
        <div className="skeleton" style={{ width: '80px', height: '100px', borderRadius: 8, flexShrink: 0 }}></div>
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div className="skeleton" style={{ height: 12, width: '100%', borderRadius: 4 }}></div>
          <div className="skeleton" style={{ height: 12, width: '80%', borderRadius: 4 }}></div>
          <div style={{ marginTop: 'auto', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', background: 'rgba(0,0,0,0.2)', padding: '8px', borderRadius: 6 }}>
             <div className="skeleton" style={{ height: 24, width: '100%', borderRadius: 4 }}></div>
             <div className="skeleton" style={{ height: 24, width: '100%', borderRadius: 4 }}></div>
             <div className="skeleton" style={{ height: 24, width: '100%', borderRadius: 4 }}></div>
             <div className="skeleton" style={{ height: 24, width: '100%', borderRadius: 4 }}></div>
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
        const source = settings.find(s => s.key === 'default_source')?.value || 'fut.gg';
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
        <div className="grid-3">
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
        <div className="grid-3">
          {filteredAndSortedSbcs.map(sbc => (
            <SbcCard key={sbc.id} sbc={sbc} api={api} onNavigate={onNavigate} />
          ))}
        </div>
      )}
    </div>
  );
}

