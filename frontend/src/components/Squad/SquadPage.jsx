import React, { useState, useEffect } from 'react';
import { useApi } from '../../hooks/useApi';
import GooeySearch from '../Search/GooeySearch';


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

  const handleSearch = (val) => {
    setSearchTerm(val);
    loadSquad(val);
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
          <div style={{ display: 'flex', gap: 12, marginBottom: 16, width: '100%', maxWidth: '320px' }}>
            <GooeySearch
              value={searchTerm}
              onChange={handleSearch}
              placeholder="Buscar jogador..."
              suggestions={['Ouro', 'Especial', 'ATA', 'MEI', 'DFE', 'GOL']}
            />
          </div>


          <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
            <table className="premium-table">
              <thead>
                <tr>
                  <th>OVR</th>
                  <th>Nome</th>
                  <th>Posição</th>
                  <th>Raridade</th>
                  <th>Liga</th>
                  <th>Nação</th>
                  <th>Status</th>
                  <th>Ação</th>
                </tr>
              </thead>
              <tbody>
                {squad.slice(0, 100).map(player => (
                  <tr
                    key={player.id}
                    className="table-row-hover"
                    style={{
                      opacity: player.is_excluded || player.is_loan ? 0.45 : 1,
                      transition: 'opacity 0.2s',
                    }}
                  >
                    <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-primary)', fontWeight: 800 }}>
                      {player.rating}
                    </td>
                    <td style={{ fontWeight: 600 }}>{player.name}</td>
                    <td>
                      <span className="badge-position">{player.preferred_position}</span>
                    </td>
                    <td style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{player.rarity}</td>
                    <td style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{player.league}</td>
                    <td>{player.nation}</td>
                    <td>
                      {player.is_loan && (
                        <span className="badge-reason" style={{ color: 'var(--danger)', borderColor: 'rgba(223, 58, 58, 0.15)', background: 'rgba(223, 58, 58, 0.06)' }}>
                          🔒 Empréstimo
                        </span>
                      )}
                      {player.is_in_active_11 && !player.is_loan && (
                        <span className="badge-reason" style={{ color: 'var(--warning)', borderColor: 'rgba(245, 159, 10, 0.15)', background: 'rgba(245, 159, 10, 0.06)' }}>
                          ⭐ Titular
                        </span>
                      )}
                      {player.is_duplicate && (
                        <span className="badge-reason duplicate">
                          📋 Duplicata
                        </span>
                      )}
                      {!player.is_loan && !player.is_in_active_11 && !player.is_duplicate && (
                        <span className="text-muted">—</span>
                      )}
                    </td>
                    <td>
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
