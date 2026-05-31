import React, { useState, useEffect, useRef } from 'react';
import { useApi } from '../hooks/useApi';

export default function SettingsPage() {
  const api = useApi();
  const [settings, setSettings] = useState([]);
  const [scrapeStatus, setScrapeStatus] = useState(null);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isSyncing, setIsSyncing] = useState(false);
  
  const pollTimer = useRef(null);

  const loadData = async () => {
    try {
      const [settingsData, statusData, logsData] = await Promise.all([
        api.get('/api/settings'),
        api.get('/api/scrape/status'),
        api.get('/api/scrape/logs?limit=10')
      ]);
      setSettings(settingsData);
      setScrapeStatus(statusData);
      setLogs(logsData);
    } catch (e) {
      console.error('Erro ao carregar dados de configurações:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    return () => {
      if (pollTimer.current) clearInterval(pollTimer.current);
    };
  }, []);

  // Polling para status de scraping
  useEffect(() => {
    if (scrapeStatus?.status === 'running') {
      if (!pollTimer.current) {
        pollTimer.current = setInterval(async () => {
          try {
            const data = await api.get('/api/scrape/status');
            setScrapeStatus(data);
            if (data.status !== 'running') {
              clearInterval(pollTimer.current);
              pollTimer.current = null;
              // Recarrega logs ao finalizar
              const newLogs = await api.get('/api/scrape/logs?limit=10');
              setLogs(newLogs);
            }
          } catch (e) {
            console.error('Erro no polling:', e);
          }
        }, 3000);
      }
    } else {
      if (pollTimer.current) {
        clearInterval(pollTimer.current);
        pollTimer.current = null;
      }
    }
  }, [scrapeStatus?.status]);

  const handleToggle = async (key, currentValue) => {
    const isTrue = currentValue.toLowerCase() === 'true';
    const newValue = isTrue ? 'false' : 'true';
    try {
      await api.patch(`/api/settings/${key}`, { value: newValue });
      setSettings(prev => prev.map(s => s.key === key ? { ...s, value: newValue } : s));
    } catch (e) {
      alert('Erro ao atualizar configuração');
    }
  };

  const handleSourceChange = async (newSource) => {
    try {
      await api.patch(`/api/settings/default_source`, { value: newSource });
      setSettings(prev => prev.map(s => s.key === 'default_source' ? { ...s, value: newSource } : s));
    } catch (e) {
      alert('Erro ao atualizar fonte');
    }
  };

  const startSync = async () => {
    const source = settings.find(s => s.key === 'default_source')?.value || 'futbin';
    setIsSyncing(true);
    try {
      await api.post(`/api/scrape/start?source=${source}`, {});
      const status = await api.get('/api/scrape/status');
      setScrapeStatus(status);
    } catch (e) {
      alert('Erro ao iniciar sincronização');
    } finally {
      setIsSyncing(false);
    }
  };

  const startEaSync = async () => {
    setIsSyncing(true);
    try {
      await api.post('/api/scrape/players/playstyles?pages=1-3', {});
      const status = await api.get('/api/scrape/status');
      setScrapeStatus(status);
    } catch (e) {
      alert('Erro ao iniciar sincronização de playstyles da EA');
    } finally {
      setIsSyncing(false);
    }
  };

  if (loading) {
    return (
      <div className="flex-center" style={{ height: '200px' }}>
        <div className="text-secondary">Carregando configurações...</div>
      </div>
    );
  }

  const getStatusColor = (status) => {
    switch (status?.toLowerCase()) {
      case 'completed': return 'var(--success)';
      case 'running': return 'var(--warning)';
      case 'failed': return 'var(--danger)';
      default: return 'var(--text-muted)';
    }
  };

  return (
    <div className="fade-in" style={{ maxWidth: '900px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '32px' }}>
      
      {/* Seção: Preferências do Sistema */}
      <section className="card">
        <h3 className="card-title">Preferências do Sistema</h3>
        <p className="text-secondary" style={{ fontSize: '0.9rem', marginBottom: '24px' }}>
          Configure como o Help DMEs deve se comportar durante o cálculo e a coleta de dados.
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {settings.filter(s => s.key !== 'default_source').map(setting => {
            const isTrue = setting.value.toLowerCase() === 'true';
            return (
              <div key={setting.key} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingBottom: '16px', borderBottom: '1px solid var(--border)' }}>
                <div style={{ flex: 1, paddingRight: '20px' }}>
                  <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '4px' }}>
                    {setting.key === 'allow_active_11_in_sbc' ? '🛡️ Proteger Time Titular' : 
                     setting.key === 'auto_exclude_loans' ? '🚫 Bloquear Empréstimos' :
                     setting.key === 'scrape_on_startup' ? '🔄 Sincronizar ao Iniciar' : setting.key}
                  </div>
                  <div className="text-secondary" style={{ fontSize: '0.8rem' }}>
                    {setting.description}
                  </div>
                </div>
                
                <div 
                  onClick={() => handleToggle(setting.key, setting.value)}
                  style={{
                    width: '48px', height: '26px', borderRadius: '13px', cursor: 'pointer',
                    background: isTrue ? 'var(--accent)' : 'var(--bg-tertiary)',
                    position: 'relative', transition: 'all 0.2s var(--ease-cinematic)',
                    border: '1px solid var(--border)',
                    boxShadow: isTrue ? '0 0 10px rgba(79, 70, 229, 0.25)' : 'none'
                  }}
                >
                  <div style={{
                    width: '20px', height: '20px', borderRadius: '50%', background: 'var(--text-primary)',
                    position: 'absolute', top: '2px', left: isTrue ? '24px' : '2px',
                    transition: 'all 0.2s var(--ease-cinematic)'
                  }} />
                </div>
              </div>
            );
          })}

          {/* Fonte de Scraping */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: '4px' }}>
            <div>
              <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '4px' }}>🌐 Fonte de Scraping</div>
              <div className="text-secondary" style={{ fontSize: '0.8rem' }}>
                Escolha o provedor de dados oficial para preços e desafios.
              </div>
            </div>
            <select 
              value={settings.find(s => s.key === 'default_source')?.value || 'futbin'}
              onChange={(e) => handleSourceChange(e.target.value)}
              style={{
                background: 'var(--bg-tertiary)', color: 'var(--text-primary)',
                border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)',
                padding: '8px 12px', cursor: 'pointer', outline: 'none'
              }}
            >
              <option value="futbin">Futbin (Recomendado)</option>
            </select>
          </div>
        </div>
      </section>

      {/* Seção: Sincronização de Dados */}
      <section className="card" style={{ borderColor: scrapeStatus?.status === 'running' ? 'var(--accent-glow-strong)' : 'var(--border)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '24px' }}>
          <div>
            <h3 className="card-title">Sincronização de Dados</h3>
            <p className="text-secondary" style={{ fontSize: '0.9rem' }}>
              Atualize a base de dados de SBCs e preços com as informações mais recentes.
            </p>
          </div>
          <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
            <button 
              className={`btn btn-secondary ${isSyncing || scrapeStatus?.status === 'running' ? 'spinning' : ''}`}
              onClick={startEaSync}
              disabled={isSyncing || scrapeStatus?.status === 'running'}
              style={{ minWidth: '190px', justifyContent: 'center', borderColor: 'var(--accent)', background: 'rgba(79, 70, 229, 0.04)', color: 'var(--text-primary)' }}
            >
              {scrapeStatus?.status === 'running' && scrapeStatus?.message?.includes('EA') ? '🔄 Sincronizando EA...' : '🎮 Playstyles EA (Prata/Bronze)'}
            </button>
            <button 
              className={`btn btn-primary ${isSyncing || scrapeStatus?.status === 'running' ? 'spinning' : ''}`}
              onClick={startSync}
              disabled={isSyncing || scrapeStatus?.status === 'running'}
              style={{ minWidth: '160px', justifyContent: 'center' }}
            >
              {scrapeStatus?.status === 'running' && !scrapeStatus?.message?.includes('EA') ? '🔄 Sincronizando...' : '🚀 Sincronizar Tudo'}
            </button>
          </div>
        </div>

        <div style={{ background: 'var(--bg-tertiary)', borderRadius: 'var(--radius-md)', padding: '16px', display: 'flex', gap: '24px' }}>
          <div style={{ flex: 1 }}>
            <div className="text-muted" style={{ fontSize: '0.75rem', textTransform: 'uppercase', marginBottom: '8px', letterSpacing: '0.05em' }}>Status Atual</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 600, color: getStatusColor(scrapeStatus?.status) }}>
              <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: getStatusColor(scrapeStatus?.status), display: 'inline-block' }} />
              {scrapeStatus?.status === 'running' ? 'Em execução' : 
               scrapeStatus?.status === 'completed' ? 'Finalizado' :
               scrapeStatus?.status === 'failed' ? 'Falha na última tentativa' : 'Aguardando'}
            </div>
          </div>
          <div style={{ flex: 1 }}>
            <div className="text-muted" style={{ fontSize: '0.75rem', textTransform: 'uppercase', marginBottom: '8px', letterSpacing: '0.05em' }}>SBCs Processados</div>
            <div style={{ color: 'var(--text-primary)', fontWeight: 600 }}>
              {scrapeStatus?.progress?.current || 0} / {scrapeStatus?.progress?.total || '?'}
            </div>
          </div>
          <div style={{ flex: 2 }}>
            <div className="text-muted" style={{ fontSize: '0.75rem', textTransform: 'uppercase', marginBottom: '8px', letterSpacing: '0.05em' }}>Mensagem</div>
            <div className="text-secondary" style={{ fontSize: '0.9rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {scrapeStatus?.message || 'Nenhuma atividade recente.'}
            </div>
          </div>
        </div>
      </section>

      {/* Seção: Histórico de Logs */}
      <section className="card">
        <h3 className="card-title">Histórico de Atividade</h3>
        <div style={{ overflowX: 'auto' }}>
          <table className="premium-table">
            <thead>
              <tr>
                <th>Data/Hora</th>
                <th>Fonte</th>
                <th>Status</th>
                <th>Resultado</th>
              </tr>
            </thead>
            <tbody>
              {logs.length > 0 ? logs.map((log, i) => (
                <tr key={i} className="table-row-hover">
                  <td className="text-mono" style={{ padding: '12px 16px' }}>{new Date(log.timestamp).toLocaleString('pt-BR')}</td>
                  <td style={{ padding: '12px 16px' }}>
                    <span className="badge-reason default">
                      {log.source}
                    </span>
                  </td>
                  <td style={{ padding: '12px 16px' }}>
                    {log.status === 'completed' ? (
                      <span className="badge-reason untradeable" style={{ textTransform: 'none' }}>
                        Sucesso
                      </span>
                    ) : log.status === 'failed' ? (
                      <span className="badge-reason" style={{ color: 'var(--danger)', borderColor: 'rgba(223, 58, 58, 0.15)', background: 'rgba(223, 58, 58, 0.06)', textTransform: 'none' }}>
                        Erro
                      </span>
                    ) : (
                      <span className="badge-reason default" style={{ textTransform: 'none' }}>
                        {log.status}
                      </span>
                    )}
                  </td>
                  <td className="text-secondary" style={{ padding: '12px 16px' }}>{log.message}</td>
                </tr>
              )) : (
                <tr>
                  <td colSpan="4" style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)' }}>Nenhum log encontrado.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
