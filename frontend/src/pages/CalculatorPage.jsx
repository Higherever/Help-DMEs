import React, { useState, useEffect } from 'react';
import { useApi } from '../hooks/useApi';

export default function CalculatorPage() {
  const api = useApi();
  const [sbcs, setSbcs] = useState([]);
  const [selectedSbc, setSelectedSbc] = useState('');
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
        if (data.length > 0) setSelectedSbc(data[0].id.toString());
      } catch (e) {
        console.error('Erro ao carregar SBCs:', e);
      }
    };
    loadSbcs();
  }, []);

  const handleAnalyze = async () => {
    if (!selectedSbc) return;
    setLoadingAnalysis(true);
    setError(null);
    setAnalysis(null);
    setResult(null);
    
    try {
      const data = await api.get(`/api/calculate/${selectedSbc}/analysis`);
      setAnalysis(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoadingAnalysis(false);
    }
  };

  const handleCalculate = async () => {
    if (!selectedSbc) return;
    setLoadingCalculate(true);
    setError(null);
    
    try {
      const data = await api.post(`/api/calculate/${selectedSbc}`, {});
      setResult(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoadingCalculate(false);
    }
  };

  return (
    <div className="fade-in">
      <div className="card" style={{ marginBottom: 24, display: 'flex', gap: 16, alignItems: 'flex-end' }}>
        <div style={{ flex: 1 }}>
          <label className="text-secondary" style={{ display: 'block', marginBottom: 8, fontSize: '0.85rem' }}>
            Selecione o DME a ser calculado
          </label>
          <select 
            value={selectedSbc} 
            onChange={(e) => {
              setSelectedSbc(e.target.value);
              setAnalysis(null);
              setResult(null);
            }}
            style={{
              width: '100%', padding: '12px 16px', borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border)', background: 'var(--bg-tertiary)',
              color: 'var(--text-primary)', fontFamily: 'var(--font-main)',
              outline: 'none', appearance: 'none', cursor: 'pointer'
            }}
          >
            {sbcs.map(sbc => (
              <option key={sbc.id} value={sbc.id}>{sbc.name}</option>
            ))}
          </select>
        </div>
        <button 
          className="btn-primary" 
          style={{ margin: 0, padding: '12px 24px', width: 'auto' }}
          onClick={handleAnalyze}
          disabled={loadingAnalysis || !selectedSbc}
        >
          {loadingAnalysis ? 'Analisando...' : 'Analisar Viabilidade'}
        </button>
      </div>

      {error && (
        <div className="card" style={{ borderLeft: '4px solid var(--danger)', marginBottom: 24 }}>
          <div style={{ color: 'var(--danger)', fontWeight: 600 }}>Erro</div>
          <div className="text-secondary">{error}</div>
        </div>
      )}

      {analysis && !result && (
        <div className="fade-in card" style={{ marginBottom: 24, border: analysis.feasible ? '1px solid var(--accent)' : '1px solid var(--danger)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <div>
              <div className="card-title" style={{ marginBottom: 4 }}>Análise de Viabilidade</div>
              <div style={{ fontSize: '1.2rem', fontWeight: 600, color: analysis.feasible ? 'var(--accent)' : 'var(--warning)' }}>
                {analysis.feasible ? '✅ Viável com seu Elenco' : '⚠️ Cartas Faltando'}
              </div>
            </div>
            <button 
              className="btn-cta" 
              onClick={handleCalculate}
              disabled={loadingCalculate}
              style={{ margin: 0 }}
            >
              {loadingCalculate ? 'Calculando...' : 'Calcular Rota Ótima'}
            </button>
          </div>

          <div style={{ marginBottom: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8, fontSize: '0.85rem' }}>
              <span className="text-secondary">Requisitos Atendidos: {analysis.met_requirements} de {analysis.total_requirements}</span>
              <span style={{ color: analysis.feasible ? 'var(--accent)' : 'var(--warning)', fontWeight: 600 }}>
                {Math.round((analysis.met_requirements / (analysis.total_requirements || 1)) * 100)}%
              </span>
            </div>
            <div style={{ width: '100%', height: 8, background: 'var(--bg-tertiary)', borderRadius: 4, overflow: 'hidden' }}>
              <div style={{ 
                width: `${(analysis.met_requirements / (analysis.total_requirements || 1)) * 100}%`, 
                height: '100%', 
                background: analysis.feasible ? 'var(--accent)' : 'var(--warning)',
                transition: 'width 0.5s ease'
              }} />
            </div>
          </div>

          {analysis.unmet_requirements && analysis.unmet_requirements.length > 0 && (
            <div style={{ background: 'rgba(255, 68, 68, 0.1)', padding: 16, borderRadius: 8, border: '1px solid var(--danger)' }}>
              <div style={{ color: 'var(--danger)', fontWeight: 600, marginBottom: 8, fontSize: '0.9rem' }}>⚠️ Requisitos Não Atendidos (Estimativa V1):</div>
              <ul style={{ margin: 0, paddingLeft: 20, color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                {analysis.unmet_requirements.map((req, i) => <li key={i}>{req}</li>)}
              </ul>
            </div>
          )}
        </div>
      )}

      {result && (
        <div className="fade-in">
          <div className="grid-2" style={{ marginBottom: 24 }}>
            <div className="card" style={{ border: result.feasible ? '1px solid var(--accent)' : '1px solid var(--danger)' }}>
              <div className="card-title">Status da Montagem</div>
              <div style={{ fontSize: '1.5rem', fontWeight: 800, color: result.feasible ? 'var(--accent)' : 'var(--danger)' }}>
                {result.feasible ? '✅ Rota Viável' : '❌ Impossível com o Elenco Atual'}
              </div>
              <div className="text-secondary" style={{ marginTop: 8 }}>{result.message}</div>
            </div>
            <div className="card">
              <div className="card-title">Custo Estimado da Rota</div>
              <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--warning)', fontFamily: 'var(--font-mono)' }}>
                {result.total_estimated_cost.toLocaleString()} <span style={{ fontSize: '1rem', color: 'var(--text-secondary)', fontWeight: 400 }}>coins</span>
              </div>
            </div>
          </div>

          <h3 style={{ marginBottom: 16 }}>Passo a Passo</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {result.steps.map(step => (
              <div key={step.order} className="card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, paddingBottom: 12, borderBottom: '1px solid var(--border)' }}>
                  <div style={{ fontWeight: 600, fontSize: '1.1rem', color: 'var(--accent)' }}>
                    Desafio {step.order}: {step.challenge_name}
                  </div>
                  {step.estimated_cost > 0 && (
                    <div className="text-mono" style={{ color: 'var(--warning)', fontSize: '0.9rem' }}>
                      Custo: {step.estimated_cost.toLocaleString()}
                    </div>
                  )}
                </div>

                {step.gaps && step.gaps.length > 0 && (
                  <div style={{ marginBottom: 16, padding: 12, background: 'rgba(255, 68, 68, 0.1)', borderRadius: 8, border: '1px solid var(--danger)' }}>
                    <div style={{ color: 'var(--danger)', fontWeight: 600, marginBottom: 4, fontSize: '0.9rem' }}>Avisos:</div>
                    <ul style={{ margin: 0, paddingLeft: 20, color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                      {step.gaps.map((gap, i) => <li key={i}>{gap}</li>)}
                    </ul>
                  </div>
                )}

                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border-accent)', textAlign: 'left' }}>
                      <th style={{ padding: '8px 4px', color: 'var(--text-secondary)' }}>OVR</th>
                      <th style={{ padding: '8px 4px', color: 'var(--text-secondary)' }}>Nome</th>
                      <th style={{ padding: '8px 4px', color: 'var(--text-secondary)' }}>Posição</th>
                      <th style={{ padding: '8px 4px', color: 'var(--text-secondary)' }}>Motivo</th>
                    </tr>
                  </thead>
                  <tbody>
                    {step.suggested_players.map(sp => (
                      <tr key={sp.player.id} style={{ borderBottom: '1px solid var(--border)' }}>
                        <td style={{ padding: '8px 4px', fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--text-primary)' }}>
                          <div style={{ width: 28, height: 28, borderRadius: '50%', background: 'var(--bg-tertiary)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                            {sp.player.rating}
                          </div>
                        </td>
                        <td style={{ padding: '8px 4px', fontWeight: 600, color: 'var(--text-primary)' }}>{sp.player.name}</td>
                        <td style={{ padding: '8px 4px', color: 'var(--text-secondary)' }}>{sp.assigned_position}</td>
                        <td style={{ padding: '8px 4px' }}>
                          <span style={{ 
                            background: sp.reason === 'Duplicata' ? 'rgba(0, 153, 255, 0.2)' : 
                                       sp.reason === 'Intransferível' ? 'rgba(0, 255, 136, 0.2)' : 'var(--bg-tertiary)',
                            color: sp.reason === 'Duplicata' ? '#0099ff' : 
                                   sp.reason === 'Intransferível' ? 'var(--accent)' : 'var(--text-secondary)',
                            padding: '2px 8px', borderRadius: 4, fontSize: '0.75rem', fontWeight: 600
                          }}>
                            {sp.reason}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
