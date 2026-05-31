import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Sparkles, 
  AlertTriangle, 
  CheckCircle2, 
  Coins, 
  Info,
  ChevronRight,
  ChevronDown,
  TrendingDown,
  User as UserIcon,
  Package as Box
} from 'lucide-react';
import { useApi } from '../hooks/useApi';
import FutbinCard from '../components/FutbinCard';

// Componente de Dropdown Customizado Premium
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
        <span>{selectedOption ? selectedOption.label : 'Selecione...'}</span>
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

function SuggestedPlayerCard({ player, assignedPosition }) {
  const api = useApi();
  const [cardImage, setCardImage] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    const fetchImage = async () => {
      try {
        const data = await api.get(
          `/api/cards/search-image?name=${encodeURIComponent(player.name)}&league=${encodeURIComponent(player.league || '')}&team=${encodeURIComponent(player.team || '')}`
        );
        if (active) {
          setCardImage(data);
        }
      } catch (err) {
        // Log leve de erro para não poluir o console do frontend caso algum jogador não tenha screenshot de card no BD
        console.debug("Card não encontrado no BD para", player.name);
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };
    fetchImage();
    return () => {
      active = false;
    };
  }, [player.name, player.league, player.team, api]);

  const getPlayerPhotoUrl = (definitionId) => {
    if (!definitionId) return null;
    return `https://feeds.content.ea.com/content/fame/fc25/common/card-assets/player-faces/p${definitionId}.png`;
  };

  const getImageUrl = (url) => {
    if (!url) return null;
    if (url.startsWith('http')) return url.replace('cdn3.futbin.com', 'cdn.futbin.com');
    if (url.startsWith('/')) return `${api.API_BASE}${url}`;
    return `${api.API_BASE}/${url}`;
  };

  if (!loading && cardImage && cardImage.full_image_url) {
    const cardData = {
      name: player.name,
      rating: player.rating,
      position: assignedPosition || player.position || '',
      bg_url_hd: getImageUrl(cardImage.full_image_url),
    };
    return (
      <div style={{ display: 'flex', justifyContent: 'center', width: 45, height: 63, position: 'relative' }}>
        <FutbinCard data={cardData} size="xs" />
      </div>
    );
  }

  return (
    <div style={{ position: 'relative', width: 42, height: 52 }}>
      <div style={{ 
        position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', 
        background: 'var(--bg-secondary)', borderRadius: 'var(--radius-xs)', border: '1px solid var(--border)' 
      }}>
        {player.definition_id ? (
          <img 
            src={getPlayerPhotoUrl(player.definition_id)} 
            alt="" 
            style={{ width: '100%', height: '100%', objectFit: 'contain' }}
            onError={(e) => { e.target.style.display = 'none'; e.target.nextSibling.style.display = 'flex'; }}
          />
        ) : null}
        <div style={{ display: player.definition_id ? 'none' : 'flex', width: '100%', height: '100%', alignItems: 'center', justifyContent: 'center' }}>
          <UserIcon size={20} style={{ opacity: 0.3 }} />
        </div>
      </div>
      <div style={{ 
        position: 'absolute', bottom: -4, right: -4, width: 22, height: 22, 
        borderRadius: '50%', background: 'var(--text-primary)', border: '1px solid var(--border)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.65rem', fontWeight: 700, color: 'var(--bg-primary)', zIndex: 2,
        fontFamily: 'var(--font-mono)'
      }}>
        {player.rating}
      </div>
    </div>
  );
}

export default function CalculatorPage() {
  const api = useApi();
  const [sbcs, setSbcs] = useState([]);
  const [selectedSbcId, setSelectedSbcId] = useState('');
  const [analysis, setAnalysis] = useState(null);
  const [result, setResult] = useState(null);
  const [loadingAnalysis, setLoadingAnalysis] = useState(false);
  const [loadingCalculate, setLoadingCalculate] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const loadSbcs = async () => {
      try {
        const data = await api.get('/api/sbcs');
        setSbcs(data);
        const storedSbcId = localStorage.getItem('selected_sbc_id');
        if (storedSbcId) {
          setSelectedSbcId(storedSbcId);
          localStorage.removeItem('selected_sbc_id');
        } else if (data.length > 0) {
          setSelectedSbcId(data[0].id.toString());
        }
      } catch (e) {
        console.error('Erro ao carregar SBCs:', e);
      }
    };
    loadSbcs();
  }, []);

  // Aciona análise automática se houver um SBC selecionado via localStorage
  useEffect(() => {
    if (selectedSbcId && sbcs.length > 0) {
      handleAnalyze();
    }
  }, [selectedSbcId]);

  const handleAnalyze = async () => {
    if (!selectedSbcId) return;
    setLoadingAnalysis(true);
    setError(null);
    setAnalysis(null);
    setResult(null);
    
    try {
      const data = await api.get(`/api/calculate/${selectedSbcId}/analysis`);
      setAnalysis(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoadingAnalysis(false);
    }
  };

  const handleCalculate = async () => {
    if (!selectedSbcId) return;
    setLoadingCalculate(true);
    setError(null);
    
    try {
      const data = await api.post(`/api/calculate/${selectedSbcId}`, {});
      setResult(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoadingCalculate(false);
    }
  };

  const getPlayerPhotoUrl = (definitionId) => {
    if (!definitionId) return null;
    // URL Padrão EA FC 25 para faces de jogadores
    return `https://feeds.content.ea.com/content/fame/fc25/common/card-assets/player-faces/p${definitionId}.png`;
  };

  const selectedSbcData = sbcs.find(s => s.id.toString() === selectedSbcId);

  const getImageUrl = (url) => {
    if (!url) return null;
    if (url.startsWith('http')) return url.replace('cdn3.futbin.com', 'cdn.futbin.com');
    if (url.startsWith('/')) return `${api.API_BASE}${url}`;
    return `${api.API_BASE}/${url}`;
  };

  const sbcOptions = sbcs.map(s => ({ value: s.id.toString(), label: s.name }));

  return (
    <div className="fade-in" style={{ padding: '0 8px 24px 8px' }}>
      
      {/* Seletor e Cabeçalho do SBC */}
      <div className="card" style={{ 
        marginBottom: 24, 
        padding: 0, 
        overflow: 'hidden'
      }}>
        <div style={{ 
          padding: '16px 20px', 
          background: 'transparent', 
          borderBottom: '1px solid var(--border)', 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center' 
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{ padding: 8, background: 'var(--bg-tertiary)', border: '1px solid var(--border)', borderRadius: 'var(--radius-xs)' }}>
              <Sparkles size={18} style={{ color: 'var(--accent)' }} />
            </div>
            <h2 style={{ fontSize: '1.1rem', fontWeight: 800, margin: 0, fontFamily: 'var(--font-serif)', fontStyle: 'italic', color: 'var(--text-primary)' }}>
              Otimizador de Elenco
            </h2>
          </div>
          {sbcOptions.length > 0 && (
            <PremiumDropdown 
              value={selectedSbcId} 
              onChange={(val) => setSelectedSbcId(val)} 
              options={sbcOptions} 
            />
          )}
        </div>

        {selectedSbcData && (
          <div style={{ padding: '20px', display: 'flex', gap: 24, alignItems: 'center', flexWrap: 'wrap' }}>
             <div style={{ width: 80, height: 100, flexShrink: 0, borderRadius: 'var(--radius-xs)', overflow: 'hidden', background: 'var(--bg-primary)', border: '1px solid var(--border)', boxShadow: '0 4px 12px rgba(0, 0, 0, 0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <img src={getImageUrl(selectedSbcData.image_url)} referrerPolicy="no-referrer" style={{ width: '85%', height: '85%', objectFit: 'contain' }} />
             </div>
             <div style={{ flex: 1, minWidth: '200px' }}>
                <div style={{ fontSize: '1.4rem', fontWeight: 800, fontFamily: 'var(--font-serif)', fontStyle: 'italic', color: 'var(--text-primary)', marginBottom: 4 }}>
                  {selectedSbcData.name}
                </div>
                <div style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', marginBottom: 12 }}>
                  {selectedSbcData.description}
                </div>
                <div style={{ display: 'flex', gap: 16 }}>
                   <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--warning)', fontWeight: 700 }}>
                      <Coins size={14} /> {selectedSbcData.total_cost?.toLocaleString()} Coins
                   </div>
                   <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                      <TrendingDown size={14} /> {selectedSbcData.category.toUpperCase()}
                   </div>
                </div>
             </div>
             <button 
                className="btn btn-primary" 
                style={{ width: 'auto', padding: '12px 24px', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', fontSize: '0.75rem', fontWeight: 700 }}
                onClick={handleAnalyze}
                disabled={loadingAnalysis}
              >
                {loadingAnalysis ? 'Analisando...' : 'Verificar Elenco'}
              </button>
          </div>
        )}
      </div>

      {/* Grid de Duas Colunas em Proporção Áurea */}
      <div className="calculator-layout-grid">
        
        {/* Coluna da Esquerda: Resumos, Viabilidade, Status */}
        <div className="calculator-analysis-column" style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
          {error && (
            <motion.div 
              initial={{ opacity: 0, x: -20 }} 
              animate={{ opacity: 1, x: 0 }} 
              className="card" 
              style={{ 
                borderColor: 'var(--danger)', 
                background: 'var(--bg-secondary)',
                border: '1px solid var(--danger)',
                boxShadow: '0 4px 16px rgba(223, 58, 58, 0.15)',
                borderRadius: 'var(--radius-sm)'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: 'var(--danger)', fontWeight: 700, marginBottom: 4 }}>
                <AlertTriangle size={18} /> Erro no Processamento
              </div>
              <div style={{ fontSize: '0.88rem', color: 'var(--text-secondary)' }}>{error}</div>
            </motion.div>
          )}

          {analysis && !result && (
            <motion.div 
              initial={{ opacity: 0, y: 20 }} 
              animate={{ opacity: 1, y: 0 }} 
              className="card" 
              style={{ 
                border: '1px solid var(--border)',
                background: 'var(--bg-secondary)',
                borderRadius: 'var(--radius-sm)'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20, flexWrap: 'wrap', gap: 16 }}>
                <div>
                  <div style={{ fontSize: '0.65rem', fontWeight: 700, letterSpacing: '0.12em', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginBottom: 6 }}>ANÁLISE DE VIABILIDADE</div>
                  <div style={{ fontSize: '1.4rem', fontWeight: 800, fontFamily: 'var(--font-serif)', fontStyle: 'italic', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: 10 }}>
                    {analysis.feasible ? <CheckCircle2 size={24} style={{ color: 'var(--success)' }} /> : <AlertTriangle size={24} style={{ color: 'var(--warning)' }} />}
                    {analysis.feasible ? 'Totalmente Viável' : 'Recursos Insuficientes'}
                  </div>
                </div>
                <button 
                  className="btn btn-cta" 
                  onClick={handleCalculate}
                  disabled={loadingCalculate}
                  style={{ width: 'auto', padding: '14px 28px' }}
                >
                  {loadingCalculate ? 'Processando Rota...' : 'Calcular Melhor Rota'}
                  <ChevronRight size={18} style={{ marginLeft: 8 }} />
                </button>
              </div>

              <div style={{ marginBottom: 20 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10, fontSize: '0.82rem', fontFamily: 'var(--font-mono)' }}>
                  <span className="text-secondary">Progresso dos Requisitos ({analysis.met_requirements}/{analysis.total_requirements})</span>
                  <span style={{ color: 'var(--text-primary)', fontWeight: 700 }}>
                    {Math.round((analysis.met_requirements / (analysis.total_requirements || 1)) * 100)}%
                  </span>
                </div>
                <div style={{ width: '100%', height: 8, background: 'var(--bg-tertiary)', border: '1px solid var(--border)', borderRadius: 'var(--radius-xs)', overflow: 'hidden' }}>
                  <motion.div 
                    initial={{ width: 0 }}
                    animate={{ width: `${(analysis.met_requirements / (analysis.total_requirements || 1)) * 100}%` }}
                    transition={{ duration: 1, ease: 'easeOut' }}
                    style={{ 
                      height: '100%', 
                      background: 'var(--text-primary)'
                    }} 
                  />
                </div>
              </div>

              {analysis.unmet_requirements && analysis.unmet_requirements.length > 0 && (
                <div style={{ background: 'var(--bg-primary)', padding: 16, borderRadius: 'var(--radius-xs)', border: '1px solid var(--border)' }}>
                  <div style={{ color: 'var(--warning)', fontWeight: 700, marginBottom: 10, fontSize: '0.82rem', display: 'flex', alignItems: 'center', gap: 8, fontFamily: 'var(--font-mono)' }}>
                    <Info size={16} /> REQUISITOS PENDENTES:
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 8 }}>
                    {analysis.unmet_requirements.map((req, i) => (
                      <div key={i} style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: 6, fontFamily: 'var(--font-mono)' }}>
                        <div style={{ width: 4, height: 4, borderRadius: '50%', background: 'var(--warning)' }}></div> {req}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </motion.div>
          )}

          {result && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
              <div className="card" style={{ 
                border: '1px solid var(--border)', 
                background: 'var(--bg-secondary)',
                borderRadius: 'var(--radius-sm)',
                padding: '20px'
              }}>
                <div style={{ fontSize: '0.65rem', fontWeight: 700, letterSpacing: '0.12em', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginBottom: 6 }}>STATUS DA MONOGRAFIA</div>
                <div style={{ fontSize: '1.4rem', fontWeight: 800, fontFamily: 'var(--font-serif)', fontStyle: 'italic', color: 'var(--text-primary)', marginBottom: 8 }}>
                  {result.feasible ? 'ROTA COMPLETA DETECTADA' : 'ROTA INCOMPLETA'}
                </div>
                <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>{result.message}</div>
              </div>

              <div className="card" style={{ 
                border: '1px solid var(--border)', 
                background: 'var(--bg-secondary)',
                borderRadius: 'var(--radius-sm)',
                padding: '20px',
                boxShadow: '0 0 15px rgba(245, 159, 10, 0.05)'
              }}>
                <div style={{ fontSize: '0.65rem', fontWeight: 700, letterSpacing: '0.12em', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginBottom: 6 }}>CUSTO ESTIMADO EM MERCADO</div>
                <div style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--warning)', fontFamily: 'var(--font-mono)', display: 'flex', alignItems: 'center', gap: 8 }}>
                  {result.total_estimated_cost.toLocaleString()} <span style={{ fontSize: '1.1rem', color: 'var(--text-secondary)', fontWeight: 400 }}>🪙</span>
                </div>
                <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginTop: 8 }}>
                  * ECONOMIA CALCULADA COM BASE EM SUAS CARTAS INTRANSFERÍVEIS
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Coluna da Direita: Fluxograma Vertical de Passos */}
        <div className="calculator-steps-column">
          {result && (
            <div className="calculator-timeline-container">
              <h3 style={{ 
                marginBottom: 24, 
                display: 'flex', 
                alignItems: 'center', 
                gap: 10, 
                fontFamily: 'var(--font-serif)', 
                fontStyle: 'italic', 
                fontSize: '1.25rem',
                color: 'var(--text-primary)'
              }}>
                <Box size={20} /> Guia de Montagem Técnico
              </h3>

              <div className="calculator-steps-timeline">
                {result.steps.map((step, idx) => (
                  <motion.div 
                    key={step.order} 
                    initial={{ opacity: 0, x: 20 }} 
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: idx * 0.1 }}
                    className="card" 
                    style={{ 
                      padding: 0, 
                      overflow: 'hidden',
                      border: '1px solid var(--border)',
                      background: 'var(--bg-secondary)',
                      borderRadius: 'var(--radius-sm)',
                      marginBottom: 24
                    }}
                  >
                    <div style={{ 
                      display: 'flex', 
                      justifyContent: 'space-between', 
                      alignItems: 'center', 
                      padding: '14px 20px', 
                      background: 'var(--bg-primary)', 
                      borderBottom: '1px solid var(--border)' 
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                        <div style={{ 
                          width: 28, 
                          height: 28, 
                          borderRadius: 'var(--radius-xs)', 
                          background: 'var(--text-primary)', 
                          color: 'var(--bg-primary)', 
                          display: 'flex', 
                          alignItems: 'center', 
                          justifyContent: 'center', 
                          fontWeight: 700, 
                          fontFamily: 'var(--font-mono)',
                          fontSize: '0.85rem' 
                        }}>
                          {step.order.toString().padStart(2, '0')}
                        </div>
                        <div style={{ fontWeight: 800, fontFamily: 'var(--font-serif)', fontStyle: 'italic', fontSize: '1.05rem', color: 'var(--text-primary)' }}>
                          {step.challenge_name}
                        </div>
                      </div>
                      {step.estimated_cost > 0 && (
                        <div style={{ color: 'var(--warning)', fontWeight: 700, fontSize: '0.9rem', fontFamily: 'var(--font-mono)' }}>
                          + {step.estimated_cost.toLocaleString()} 🪙
                        </div>
                      )}
                    </div>

                    <div style={{ padding: 20 }}>
                      {step.gaps && step.gaps.length > 0 && (
                        <div style={{ marginBottom: 16, padding: '12px 16px', background: 'rgba(185, 28, 28, 0.06)', borderRadius: 'var(--radius-xs)', border: '1px solid rgba(185, 28, 28, 0.2)' }}>
                          <div style={{ color: 'var(--danger)', fontWeight: 700, marginBottom: 4, fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: 6, fontFamily: 'var(--font-mono)' }}>
                            <AlertTriangle size={14} /> FALTAM CARTAS PARA ESTE DESAFIO:
                          </div>
                          <ul style={{ margin: 0, paddingLeft: 20, color: 'var(--text-secondary)', fontSize: '0.78rem', fontFamily: 'var(--font-mono)' }}>
                            {step.gaps.map((gap, i) => <li key={i}>{gap.toUpperCase()}</li>)}
                          </ul>
                        </div>
                      )}

                      <div style={{ overflowX: 'auto' }}>
                        <table className="premium-table">
                          <thead>
                            <tr>
                              <th>CARTA</th>
                              <th>NOME DO JOGADOR</th>
                              <th>POS</th>
                              <th>MOTIVO</th>
                            </tr>
                          </thead>
                          <tbody>
                            {step.suggested_players.map(sp => (
                              <tr key={sp.player.id} className="table-row-hover">
                                <td style={{ width: 60 }}>
                                  <SuggestedPlayerCard player={sp.player} assignedPosition={sp.assigned_position} />
                                </td>
                                <td>
                                  <div style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{sp.player.name}</div>
                                  <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
                                    {sp.player.team} | {sp.player.league}
                                  </div>
                                </td>
                                <td>
                                  <span className="badge-position">{sp.assigned_position}</span>
                                </td>
                                <td>
                                  <div className={`badge-reason ${
                                    sp.reason === 'Duplicata' ? 'duplicate' : 
                                    sp.reason === 'Intransferível' ? 'untradeable' : 'default'
                                  }`}>
                                    {sp.reason}
                                  </div>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
