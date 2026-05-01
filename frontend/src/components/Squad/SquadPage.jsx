import React, { useState, useEffect } from 'react';
import { useApi } from '../../hooks/useApi';

const thStyle = { padding: '12px 16px', textAlign: 'left', fontWeight: 600, color: 'var(--text-secondary)', fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.04em' };
const tdStyle = { padding: '10px 16px', color: 'var(--text-primary)' };

export default function SquadPage({ squadStats, onImportCSV }) {
  const api = useApi();
  const [squad, setSquad] = useState([]);
  const [loading, setLoading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  const loadSquad = async (search = '') => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (search) params.set('search', search);
      const data = await api.get(`/api/squad?${params}`);
      setSquad(data);
    } catch (e) {
      console.error('Erro ao carregar elenco:', e);
    }
    setLoading(false);
  };

  useEffect(() => { loadSquad(); }, []);

  const handleSearch = (e) => {
    setSearchTerm(e.target.value);
    loadSquad(e.target.value);
  };

  const handleFileDrop = async (e) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer?.files?.[0] || e.target?.files?.[0];
    if (!file) return;
    await onImportCSV(file);
    loadSquad();
  };

  const toggleExclude = async (playerId) => {
    try {
      await api.patch(`/api/squad/${playerId}/exclude`, {});
      loadSquad(searchTerm);
    } catch (e) {
      console.error('Erro ao excluir:', e);
    }
  };

  const hasSquad = squadStats && squadStats.total > 0;

  return (
    <div className="fade-in">
      {/* Dropzone — sempre visível */}
      <div
        className={`csv-dropzone ${dragging ? 'dragging' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleFileDrop}
        onClick={() => document.getElementById('csv-input').click()}
        style={{ marginBottom: 24 }}
      >
        <input
          id="csv-input"
          type="file"
          accept=".csv"
          style={{ display: 'none' }}
          onChange={handleFileDrop}
        />
        <div className="csv-dropzone-icon">📂</div>
        <div className="csv-dropzone-title">
          {hasSquad ? 'Reimportar elenco' : 'Importe seu elenco CSV'}
        </div>
        <div className="csv-dropzone-subtitle">
          Arraste o arquivo CSV aqui ou clique para selecionar
        </div>
      </div>

      {/* Tabela do elenco */}
      {hasSquad && (
        <>
          <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
            <input
              type="text"
              placeholder="🔍 Buscar jogador..."
              value={searchTerm}
              onChange={handleSearch}
              style={{
                flex: 1, padding: '10px 16px', borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border)', background: 'var(--bg-tertiary)',
                color: 'var(--text-primary)', fontFamily: 'var(--font-main)',
                fontSize: '0.9rem', outline: 'none',
              }}
            />
          </div>

          <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)', background: 'var(--bg-tertiary)' }}>
                  <th style={thStyle}>OVR</th>
                  <th style={thStyle}>Nome</th>
                  <th style={thStyle}>Posição</th>
                  <th style={thStyle}>Raridade</th>
                  <th style={thStyle}>Liga</th>
                  <th style={thStyle}>Nação</th>
                  <th style={thStyle}>Status</th>
                  <th style={thStyle}>Ação</th>
                </tr>
              </thead>
              <tbody>
                {squad.slice(0, 100).map(player => (
                  <tr
                    key={player.id}
                    style={{
                      borderBottom: '1px solid var(--border)',
                      opacity: player.is_excluded || player.is_loan ? 0.4 : 1,
                      transition: 'opacity 0.2s',
                    }}
                  >
                    <td style={{ ...tdStyle, fontFamily: 'var(--font-mono)', color: 'var(--accent)', fontWeight: 700 }}>
                      {player.rating}
                    </td>
                    <td style={{ ...tdStyle, fontWeight: 600 }}>{player.name}</td>
                    <td style={tdStyle}>{player.preferred_position}</td>
                    <td style={{ ...tdStyle, fontSize: '0.8rem' }}>{player.rarity}</td>
                    <td style={{ ...tdStyle, fontSize: '0.8rem' }}>{player.league}</td>
                    <td style={tdStyle}>{player.nation}</td>
                    <td style={tdStyle}>
                      {player.is_loan && <span style={{ color: 'var(--danger)', fontSize: '0.75rem' }}>🔒 Empréstimo</span>}
                      {player.is_in_active_11 && !player.is_loan && <span style={{ color: 'var(--warning)', fontSize: '0.75rem' }}>⭐ Titular</span>}
                      {player.is_duplicate && <span style={{ color: 'var(--info)', fontSize: '0.75rem' }}>📋 Duplicata</span>}
                      {!player.is_loan && !player.is_in_active_11 && !player.is_duplicate && <span className="text-muted" style={{ fontSize: '0.75rem' }}>—</span>}
                    </td>
                    <td style={tdStyle}>
                      {!player.is_loan && (
                        <button
                          className={`btn ${player.is_excluded ? 'btn-secondary' : 'btn-danger'}`}
                          style={{ padding: '4px 12px', fontSize: '0.75rem' }}
                          onClick={() => toggleExclude(player.id)}
                        >
                          {player.is_excluded ? 'Incluir' : 'Excluir'}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {squad.length > 100 && (
              <div style={{ padding: 16, textAlign: 'center' }} className="text-muted">
                Exibindo 100 de {squad.length} jogadores. Use a busca para filtrar.
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
