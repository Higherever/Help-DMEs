import React from 'react';

export default function Dashboard({ squadStats, scrapeStatus }) {
  return (
    <div className="fade-in">
      <div className="grid-3" style={{ marginBottom: 24 }}>
        <div className="card">
          <div className="card-title">Elenco</div>
          <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--accent)', fontFamily: 'var(--font-mono)' }}>
            {squadStats?.total || 0}
          </div>
          <div className="text-muted" style={{ marginTop: 4, fontSize: '0.85rem' }}>jogadores importados</div>
        </div>
        <div className="card">
          <div className="card-title">Disponíveis para SBC</div>
          <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--accent)', fontFamily: 'var(--font-mono)' }}>
            {squadStats?.available_for_sbc || 0}
          </div>
          <div className="text-muted" style={{ marginTop: 4, fontSize: '0.85rem' }}>jogadores elegíveis</div>
        </div>
        <div className="card">
          <div className="card-title">Última Sincronização</div>
          <div style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
            {scrapeStatus?.last_scrape_at 
              ? new Date(scrapeStatus.last_scrape_at).toLocaleString('pt-BR')
              : 'Nunca sincronizado'
            }
          </div>
          <div className="text-muted" style={{ marginTop: 4, fontSize: '0.85rem' }}>
            {scrapeStatus?.sbcs_count || 0} SBCs coletados
          </div>
        </div>
      </div>

      {squadStats?.total === 0 && (
        <div className="card" style={{ textAlign: 'center', padding: '48px 24px', borderColor: 'var(--border-accent)' }}>
          <div style={{ fontSize: '3rem', marginBottom: 16 }}>📥</div>
          <div style={{ fontSize: '1.2rem', fontWeight: 600, marginBottom: 8 }}>Nenhum elenco importado</div>
          <div className="text-secondary" style={{ marginBottom: 24 }}>
            Importe seu CSV do EA FC para começar a montar seus DMEs.
          </div>
          <div className="text-muted" style={{ fontSize: '0.85rem' }}>
            Vá em <span className="text-accent">Elenco</span> → Importar CSV
          </div>
        </div>
      )}

      {squadStats && squadStats.total > 0 && (
        <div className="grid-2">
          <div className="card">
            <div className="card-title">Distribuição por Rating</div>
            {squadStats.by_rating_range && Object.entries(squadStats.by_rating_range).map(([range, count]) => (
              <div key={range} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--border)' }}>
                <span className="text-secondary">{range}</span>
                <span className="text-mono" style={{ color: 'var(--accent)' }}>{count}</span>
              </div>
            ))}
          </div>
          <div className="card">
            <div className="card-title">Resumo do Elenco</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span className="text-secondary">Duplicatas</span>
                <span className="text-mono text-accent">{squadStats.duplicates}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span className="text-secondary">Intransferíveis</span>
                <span className="text-mono text-accent">{squadStats.untradeables}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span className="text-secondary">Empréstimos</span>
                <span className="text-mono" style={{ color: 'var(--danger)' }}>{squadStats.loans}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span className="text-secondary">Excluídos</span>
                <span className="text-mono" style={{ color: 'var(--warning)' }}>{squadStats.excluded}</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
