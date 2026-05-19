import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Sparkles, 
  AlertTriangle, 
  CheckCircle2, 
  Coins, 
  Info,
  ChevronRight,
  TrendingDown,
  User as UserIcon,
  Package as Box
} from 'lucide-react';
import { useApi } from '../hooks/useApi';

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

  return (
    <div className="fade-in" style={{ padding: '0 8px 24px 8px' }}>
      
      {/* Seletor e Cabeçalho do SBC */}
      <div className="card" style={{ marginBottom: 24, padding: 0, overflow: 'hidden' }}>
        <div style={{ padding: '16px 20px', background: 'rgba(255,255,255,0.03)', borderBottom: '1px solid rgba(255,255,255,0.05)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{ padding: 8, background: 'rgba(0, 255, 136, 0.1)', borderRadius: 8 }}>
              <Sparkles size={18} style={{ color: 'var(--accent)' }} />
            </div>
            <h2 style={{ fontSize: '1.1rem', fontWeight: 700, margin: 0 }}>Otimizador de Elenco</h2>
          </div>
          <select 
            value={selectedSbcId} 
            onChange={(e) => setSelectedSbcId(e.target.value)}
            style={{
              padding: '8px 16px', borderRadius: 8,
              border: '1px solid rgba(255,255,255,0.1)', background: 'rgba(0,0,0,0.2)',
              color: 'var(--text-primary)', fontFamily: 'inherit',
              fontSize: '0.85rem', outline: 'none', cursor: 'pointer'
            }}
          >
            {sbcs.map(sbc => (
              <option key={sbc.id} value={sbc.id}>{sbc.name}</option>
            ))}
          </select>
        </div>

        {selectedSbcData && (
          <div style={{ padding: '20px', display: 'flex', gap: 24, alignItems: 'center' }}>
             <div style={{ width: 80, height: 100, flexShrink: 0, borderRadius: 8, overflow: 'hidden', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <img src={getImageUrl(selectedSbcData.image_url)} referrerPolicy="no-referrer" style={{ width: '85%', height: '85%', objectFit: 'contain' }} />
             </div>
             <div style={{ flex: 1 }}>
                <div style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--text-primary)', marginBottom: 4 }}>{selectedSbcData.name}</div>
                <div className="text-secondary" style={{ fontSize: '0.85rem', marginBottom: 12 }}>{selectedSbcData.description}</div>
                <div style={{ display: 'flex', gap: 16 }}>
                   <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.75rem', color: 'var(--warning)', fontWeight: 600 }}>
                      <Coins size={14} /> {selectedSbcData.total_cost?.toLocaleString()} Coins
                   </div>
                   <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      <TrendingDown size={14} /> {selectedSbcData.category}
                   </div>
                </div>
             </div>
             <button 
                className="btn btn-primary" 
                style={{ width: 'auto', padding: '12px 24px' }}
                onClick={handleAnalyze}
                disabled={loadingAnalysis}
              >
                {loadingAnalysis ? 'Analisando...' : 'Verificar Elenco'}
              </button>
          </div>
        )}
      </div>

      {error && (
        <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} className="card" style={{ borderColor: 'var(--danger)', marginBottom: 24, background: 'rgba(255, 68, 68, 0.02)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: 'var(--danger)', fontWeight: 700, marginBottom: 4 }}>
            <AlertTriangle size={18} /> Erro no Processamento
          </div>
          <div className="text-secondary" style={{ fontSize: '0.9rem' }}>{error}</div>
        </motion.div>
      )}

      {analysis && !result && (
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="card" style={{ marginBottom: 24, border: analysis.feasible ? '1px solid var(--accent)' : '1px solid rgba(255, 184, 0, 0.3)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
            <div>
              <div className="text-muted" style={{ fontSize: '0.75rem', fontWeight: 700, letterSpacing: '0.1em', marginBottom: 6 }}>ANÁLISE DE VIABILIDADE</div>
              <div style={{ fontSize: '1.5rem', fontWeight: 800, color: analysis.feasible ? 'var(--accent)' : 'var(--warning)', display: 'flex', alignItems: 'center', gap: 10 }}>
                {analysis.feasible ? <CheckCircle2 size={24} /> : <AlertTriangle size={24} />}
                {analysis.feasible ? 'Totalmente Viável' : 'Recursos Insuficientes'}
              </div>
            </div>
            <button 
              className="btn btn-cta" 
              onClick={handleCalculate}
              disabled={loadingCalculate}
              style={{ width: 'auto', padding: '14px 32px' }}
            >
              {loadingCalculate ? 'Processando Rota...' : 'Calcular Melhor Rota'}
              <ChevronRight size={18} style={{ marginLeft: 8 }} />
            </button>
          </div>

          <div style={{ marginBottom: 20 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10, fontSize: '0.85rem' }}>
              <span className="text-secondary">Progresso dos Requisitos ({analysis.met_requirements}/{analysis.total_requirements})</span>
              <span style={{ color: analysis.feasible ? 'var(--accent)' : 'var(--warning)', fontWeight: 700 }}>
                {Math.round((analysis.met_requirements / (analysis.total_requirements || 1)) * 100)}%
              </span>
            </div>
            <div style={{ width: '100%', height: 10, background: 'rgba(255,255,255,0.05)', borderRadius: 10, overflow: 'hidden' }}>
              <motion.div 
                initial={{ width: 0 }}
                animate={{ width: `${(analysis.met_requirements / (analysis.total_requirements || 1)) * 100}%` }}
                transition={{ duration: 1, ease: 'easeOut' }}
                style={{ 
                  height: '100%', 
                  background: analysis.feasible ? 'linear-gradient(90deg, #00ff88 0%, #00cc6a 100%)' : 'linear-gradient(90deg, #ffb800 0%, #cc9300 100%)',
                  boxShadow: analysis.feasible ? '0 0 10px rgba(0, 255, 136, 0.3)' : '0 0 10px rgba(255, 184, 0, 0.3)'
                }} 
              />
            </div>
          </div>

          {analysis.unmet_requirements && analysis.unmet_requirements.length > 0 && (
            <div style={{ background: 'rgba(255, 184, 0, 0.05)', padding: 16, borderRadius: 12, border: '1px solid rgba(255, 184, 0, 0.1)' }}>
              <div style={{ color: 'var(--warning)', fontWeight: 700, marginBottom: 10, fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: 8 }}>
                <Info size={16} /> Requisitos Pendentes:
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 8 }}>
                {analysis.unmet_requirements.map((req, i) => (
                  <div key={i} style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: 6 }}>
                    <div style={{ width: 4, height: 4, borderRadius: '50%', background: 'var(--warning)' }}></div> {req}
                  </div>
                ))}
              </div>
            </div>
          )}
        </motion.div>
      )}

      {result && (
        <div className="fade-in">
          <div className="grid-2" style={{ marginBottom: 24 }}>
            <div className="card" style={{ border: result.feasible ? '1px solid var(--accent)' : '1px solid var(--danger)', background: result.feasible ? 'rgba(0, 255, 136, 0.02)' : 'rgba(255, 68, 68, 0.02)' }}>
              <div className="text-muted" style={{ fontSize: '0.7rem', fontWeight: 700, letterSpacing: '0.1em', marginBottom: 4 }}>STATUS</div>
              <div style={{ fontSize: '1.6rem', fontWeight: 900, color: result.feasible ? 'var(--accent)' : 'var(--danger)' }}>
                {result.feasible ? 'ROTA COMPLETA' : 'ROTA INCOMPLETA'}
              </div>
              <div className="text-secondary" style={{ marginTop: 6, fontSize: '0.85rem' }}>{result.message}</div>
            </div>
            <div className="card">
              <div className="text-muted" style={{ fontSize: '0.7rem', fontWeight: 700, letterSpacing: '0.1em', marginBottom: 4 }}>CUSTO TOTAL EM COINS</div>
              <div style={{ fontSize: '1.6rem', fontWeight: 900, color: 'var(--warning)', fontFamily: 'var(--font-mono)' }}>
                {result.total_estimated_cost.toLocaleString()} <span style={{ fontSize: '1rem', color: 'var(--text-secondary)', fontWeight: 400 }}>🪙</span>
              </div>
              <div className="text-secondary" style={{ marginTop: 6, fontSize: '0.85rem' }}>Economia gerada por intransferíveis</div>
            </div>
          </div>

          <h3 style={{ marginBottom: 20, display: 'flex', alignItems: 'center', gap: 10 }}>
            <Box size={20} style={{ color: 'var(--accent)' }} /> Guia de Montagem Passo a Passo
          </h3>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            {result.steps.map((step, idx) => (
              <motion.div 
                key={step.order} 
                initial={{ opacity: 0, x: -20 }} 
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: idx * 0.1 }}
                className="card" 
                style={{ padding: 0, overflow: 'hidden' }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '14px 20px', background: 'rgba(255,255,255,0.02)', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <div style={{ width: 28, height: 28, borderRadius: '50%', background: 'var(--accent)', color: '#000', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 900, fontSize: '0.9rem' }}>
                      {step.order}
                    </div>
                    <div style={{ fontWeight: 700, fontSize: '1.05rem', color: 'var(--text-primary)' }}>
                      {step.challenge_name}
                    </div>
                  </div>
                  {step.estimated_cost > 0 && (
                    <div className="text-mono" style={{ color: 'var(--warning)', fontWeight: 700, fontSize: '0.95rem' }}>
                      + {step.estimated_cost.toLocaleString()} 🪙
                    </div>
                  )}
                </div>

                <div style={{ padding: 20 }}>
                  {step.gaps && step.gaps.length > 0 && (
                    <div style={{ marginBottom: 16, padding: '12px 16px', background: 'rgba(255, 68, 68, 0.05)', borderRadius: 10, border: '1px solid rgba(255, 68, 68, 0.1)' }}>
                      <div style={{ color: 'var(--danger)', fontWeight: 700, marginBottom: 4, fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: 6 }}>
                        <AlertTriangle size={14} /> Faltam cartas para este desafio:
                      </div>
                      <ul style={{ margin: 0, paddingLeft: 20, color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
                        {step.gaps.map((gap, i) => <li key={i}>{gap}</li>)}
                      </ul>
                    </div>
                  )}

                  <div style={{ overflowX: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                      <thead>
                        <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', textAlign: 'left' }}>
                          <th style={{ padding: '8px 12px', color: 'var(--text-muted)', fontWeight: 600 }}>CARTA</th>
                          <th style={{ padding: '8px 12px', color: 'var(--text-muted)', fontWeight: 600 }}>NOME</th>
                          <th style={{ padding: '8px 12px', color: 'var(--text-muted)', fontWeight: 600 }}>POSIÇÃO</th>
                          <th style={{ padding: '8px 12px', color: 'var(--text-muted)', fontWeight: 600 }}>MOTIVO</th>
                        </tr>
                      </thead>
                      <tbody>
                        {step.suggested_players.map(sp => (
                          <tr key={sp.player.id} className="table-row-hover" style={{ borderBottom: '1px solid rgba(255,255,255,0.02)' }}>
                            <td style={{ padding: '10px 12px' }}>
                              <div style={{ position: 'relative', width: 42, height: 52 }}>
                                 <div style={{ 
                                   position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', 
                                   background: 'rgba(255,255,255,0.05)', borderRadius: 4, border: '1px solid rgba(255,255,255,0.1)' 
                                 }}>
                                    <img 
                                      src={getPlayerPhotoUrl(sp.player.definition_id)} 
                                      alt="" 
                                      style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                                      onError={(e) => { e.target.style.display = 'none'; e.target.nextSibling.style.display = 'flex'; }}
                                    />
                                    <div style={{ display: 'none', width: '100%', height: '100%', alignItems: 'center', justifyContent: 'center' }}>
                                       <UserIcon size={20} style={{ opacity: 0.3 }} />
                                    </div>
                                 </div>
                                 <div style={{ 
                                   position: 'absolute', bottom: -4, right: -4, width: 22, height: 22, 
                                   borderRadius: '50%', background: '#000', border: '1px solid var(--accent)',
                                   display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.65rem', fontWeight: 900, color: 'var(--accent)', zIndex: 2
                                 }}>
                                    {sp.player.rating}
                                 </div>
                              </div>
                            </td>
                            <td style={{ padding: '10px 12px' }}>
                              <div style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{sp.player.name}</div>
                              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{sp.player.team} | {sp.player.league}</div>
                            </td>
                            <td style={{ padding: '10px 12px' }}>
                              <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{sp.assigned_position}</span>
                            </td>
                            <td style={{ padding: '10px 12px' }}>
                              <div style={{ 
                                display: 'inline-flex',
                                background: sp.reason === 'Duplicata' ? 'rgba(0, 153, 255, 0.1)' : 
                                           sp.reason === 'Intransferível' ? 'rgba(0, 255, 136, 0.1)' : 'rgba(255,255,255,0.05)',
                                color: sp.reason === 'Duplicata' ? '#33adff' : 
                                       sp.reason === 'Intransferível' ? 'var(--accent)' : 'var(--text-secondary)',
                                padding: '3px 10px', borderRadius: 6, fontSize: '0.75rem', fontWeight: 700, border: '1px solid rgba(255,255,255,0.05)'
                              }}>
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
  );
}
