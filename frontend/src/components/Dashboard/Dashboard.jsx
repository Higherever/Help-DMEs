import React from 'react';
import { Users, Shield, Sparkles, Trophy, TrendingUp, Layers } from 'lucide-react';

export default function Dashboard({ squadStats, scrapeStatus, onNavigate }) {
  return (
    <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
      
      {/* Grade Principal de 3 Cards de Telemetria */}
      <div className="grid-3">
        <div className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between', minHeight: '140px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <span className="text-muted" style={{ fontFamily: 'var(--font-mono)', fontSize: '0.65rem', letterSpacing: '0.1em', textTransform: 'uppercase' }}>
                // TELEMETRIA 01
              </span>
              <h3 className="card-title" style={{ marginTop: '4px', marginBottom: 0 }}>Elenco Total</h3>
            </div>
            <div style={{ padding: '8px', background: 'var(--accent-dim)', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(79, 70, 229, 0.15)' }}>
              <Users size={16} style={{ color: 'var(--accent-light)' }} />
            </div>
          </div>
          <div>
            <div style={{ fontSize: '2.5rem', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)', lineHeight: 1 }}>
              {squadStats?.total || 0}
            </div>
            <div className="text-muted" style={{ marginTop: 6, fontSize: '0.72rem', fontFamily: 'var(--font-mono)', textTransform: 'uppercase' }}>
              jogadores importados
            </div>
          </div>
        </div>

        <div className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between', minHeight: '140px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <span className="text-muted" style={{ fontFamily: 'var(--font-mono)', fontSize: '0.65rem', letterSpacing: '0.1em', textTransform: 'uppercase' }}>
                // TELEMETRIA 02
              </span>
              <h3 className="card-title" style={{ marginTop: '4px', marginBottom: 0 }}>Disponíveis p/ SBC</h3>
            </div>
            <div style={{ padding: '8px', background: 'var(--accent-dim)', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(79, 70, 229, 0.15)' }}>
              <Shield size={16} style={{ color: 'var(--accent-light)' }} />
            </div>
          </div>
          <div>
            <div style={{ fontSize: '2.5rem', fontWeight: 700, color: 'var(--accent-light)', fontFamily: 'var(--font-mono)', lineHeight: 1 }}>
              {squadStats?.available_for_sbc || 0}
            </div>
            <div className="text-muted" style={{ marginTop: 6, fontSize: '0.72rem', fontFamily: 'var(--font-mono)', textTransform: 'uppercase' }}>
              jogadores qualificados
            </div>
          </div>
        </div>

        <div className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between', minHeight: '140px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <span className="text-muted" style={{ fontFamily: 'var(--font-mono)', fontSize: '0.65rem', letterSpacing: '0.1em', textTransform: 'uppercase' }}>
                // TELEMETRIA 03
              </span>
              <h3 className="card-title" style={{ marginTop: '4px', marginBottom: 0 }}>Última Coleta</h3>
            </div>
            <div style={{ padding: '8px', background: 'rgba(245, 159, 10, 0.08)', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(245, 159, 10, 0.15)' }}>
              <Sparkles size={16} style={{ color: 'var(--warning)' }} />
            </div>
          </div>
          <div>
            <div style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)', wordBreak: 'break-all' }}>
              {scrapeStatus?.last_scrape_at 
                ? new Date(scrapeStatus.last_scrape_at).toLocaleString('pt-BR')
                : 'Pendente'
              }
            </div>
            <div className="text-muted" style={{ marginTop: 6, fontSize: '0.72rem', fontFamily: 'var(--font-mono)', textTransform: 'uppercase' }}>
              {scrapeStatus?.sbcs_count || 0} SBCs sincronizados
            </div>
          </div>
        </div>
      </div>

      {/* Caso Elenco Vazio */}
      {squadStats?.total === 0 && (
        <div className="card" style={{ textAlign: 'center', padding: '64px 32px', borderStyle: 'dashed', borderColor: 'var(--border-hover)' }}>
          <div style={{ fontSize: '3rem', marginBottom: 20 }}>📥</div>
          <h3 className="card-title" style={{ fontSize: '1.45rem', marginBottom: 8 }}>Nenhum elenco importado</h3>
          <p className="text-secondary" style={{ marginBottom: 28, maxWidth: '500px', marginLeft: 'auto', marginRight: 'auto', fontSize: '0.92rem' }}>
            Importe seu arquivo CSV do elenco exportado do Web App do EA FC para que o otimizador possa sugerir soluções inteligentes.
          </p>
          <div className="text-muted" style={{ fontSize: '0.78rem', fontFamily: 'var(--font-mono)', textTransform: 'uppercase' }}>
            vá em <span className="text-accent" style={{ textDecoration: 'underline', fontWeight: 'bold' }}>Elenco</span> → Importar CSV
          </div>
        </div>
      )}

      {/* Gráficos e Tabelas de Resumo */}
      {squadStats && squadStats.total > 0 && (
        <div className="grid-2">
          {/* Distribuição por Rating */}
          <div className="card">
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20, borderBottom: '1px solid var(--border)', paddingBottom: 12 }}>
              <TrendingUp size={16} className="text-accent" />
              <h3 className="card-title" style={{ marginBottom: 0 }}>Distribuição por Classificação</h3>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {squadStats.by_rating_range && Object.entries(squadStats.by_rating_range).map(([range, count]) => {
                const total = squadStats.total || 1;
                const pct = Math.max(2, (count / total) * 100);
                
                return (
                  <div key={range} style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem' }}>
                      <span className="text-secondary" style={{ fontFamily: 'var(--font-mono)' }}>{range}</span>
                      <span className="text-mono" style={{ color: 'var(--accent-light)', fontWeight: 'bold' }}>{count}</span>
                    </div>
                    <div style={{ height: '4px', background: 'rgba(255,255,255,0.03)', borderRadius: '2px', overflow: 'hidden', border: '1px solid rgba(255,255,255,0.01)' }}>
                      <div style={{ height: '100%', width: `${pct}%`, background: 'var(--accent)', borderRadius: '2px', boxShadow: '0 0 6px var(--accent)' }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Resumo Técnico do Elenco */}
          <div className="card">
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20, borderBottom: '1px solid var(--border)', paddingBottom: 12 }}>
              <Layers size={16} className="text-accent" />
              <h3 className="card-title" style={{ marginBottom: 0 }}>Resumo Técnico do Elenco</h3>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: 10, borderBottom: '1px solid var(--border)' }}>
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <span className="text-secondary" style={{ fontSize: '0.88rem' }}>Cartas Duplicadas</span>
                  <span className="text-muted" style={{ fontSize: '0.72rem' }}>Utilize primeiro nos DMEs</span>
                </div>
                <span className="text-mono" style={{ fontSize: '1.25rem', color: 'var(--accent-light)', fontWeight: 700 }}>
                  {squadStats.duplicates}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: 10, borderBottom: '1px solid var(--border)' }}>
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <span className="text-secondary" style={{ fontSize: '0.88rem' }}>Cartas Intransferíveis</span>
                  <span className="text-muted" style={{ fontSize: '0.72rem' }}>Não podem ser vendidas no mercado</span>
                </div>
                <span className="text-mono" style={{ fontSize: '1.25rem', color: 'var(--text-secondary)', fontWeight: 700 }}>
                  {squadStats.untradeables}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: 10, borderBottom: '1px solid var(--border)' }}>
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <span className="text-secondary" style={{ fontSize: '0.88rem' }}>Empréstimos</span>
                  <span className="text-muted" style={{ fontSize: '0.72rem' }}>Ignorados pelo otimizador</span>
                </div>
                <span className="text-mono" style={{ fontSize: '1.25rem', color: 'var(--danger)', fontWeight: 700 }}>
                  {squadStats.loans}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: 4 }}>
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <span className="text-secondary" style={{ fontSize: '0.88rem' }}>Jogadores Excluídos</span>
                  <span className="text-muted" style={{ fontSize: '0.72rem' }}>Marcados para não serem usados</span>
                </div>
                <span className="text-mono" style={{ fontSize: '1.25rem', color: 'var(--warning)', fontWeight: 700 }}>
                  {squadStats.excluded}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
