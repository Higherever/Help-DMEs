import React from 'react';
import { LayoutGrid } from 'lucide-react';

/**
 * FutbinCard — Card de jogador premium estilo EA FC.
 * 
 * Usa unidades `em` relativas ao wrapper. Para mudar o tamanho,
 * passe a prop `size`: 'sm' | 'md' | 'lg' | 'xl'
 * 
 * @param {Object} data - Dados do card (bg_url_hd, face_url_hd, rating, position, name, stats[], nation_url, club_url, league_url, playstyles, skill_moves, weak_foot)
 * @param {string} size - Tamanho do card: 'sm' (10px), 'md' (14px), 'lg' (18px), 'xl' (22px)
 * @param {string} className - Classes adicionais no wrapper
 */
const FutbinCard = ({ data, size = 'lg', className = '' }) => {
  if (!data) {
    return (
      <div className={`futbin-card-wrapper card-${size} ${className}`}>
        <div className="futbin-card-placeholder">
          <LayoutGrid size={48} strokeWidth={1} />
        </div>
      </div>
    );
  }

  // Fallbacks para HD ou versão comprimida (quando HD não estiver disponível ainda)
  const bgUrl = data.bg_url_hd || data.bg_url || '';
  const faceUrl = data.face_url_hd || data.face_url || '';
  const stats = data.stats || [];
  const playstyles = data.playstyles || [];

  return (
    <div className={`futbin-card-wrapper card-${size} ${className}`}>
      
      {/* Coluna de Playstyles flutuante à esquerda (se houver) */}
      {playstyles.length > 0 && (
        <div className="futbin-card-playstyles">
          {playstyles.map((ps, idx) => (
            <div key={idx} className={`playstyle-icon-wrapper ${ps.is_plus ? 'plus' : ''}`} title={ps.name}>
              <img src={ps.icon_url} alt={ps.name} loading="lazy" referrerPolicy="no-referrer" />
            </div>
          ))}
        </div>
      )}

      <div className="futbin-card">
        {/* Fundo da carta (template) */}
        {bgUrl && (
          <img 
            src={bgUrl} 
            alt="" 
            className="futbin-card-bg" 
            referrerPolicy="no-referrer"
            draggable="false"
            loading="lazy"
          />
        )}
        
        {/* Face do jogador */}
        {faceUrl && (
          <img 
            src={faceUrl} 
            alt={data.name || ''} 
            className="futbin-card-face" 
            referrerPolicy="no-referrer"
            draggable="false"
            loading="lazy"
          />
        )}

        {/* Sombra inferior para dar contraste ao texto (fica sobre a face) */}
        <div className="futbin-card-bottom-shadow"></div>
        
        {/* Rating + Position (Top Left) */}
        <div className="futbin-card-info">
          <div className="futbin-card-rating">{data.rating}</div>
          <div className="futbin-card-position">{data.position}</div>
        </div>

        {/* Alternate Positions (Top Right) */}
        {data.alt_positions && (
          <div className="futbin-card-alt-pos">
            {data.alt_positions.split(',').map((pos, idx) => (
              <span key={idx}>{pos.trim()}</span>
            ))}
          </div>
        )}
        
        {/* Nome do jogador */}
        <div className="futbin-card-name">{data.name}</div>
        
        {/* Linha divisória */}
        <div className="futbin-card-divider"></div>
        
        {/* 6 Stats (Layout de 1 linha) */}
        {stats.length > 0 && (
          <div className="futbin-card-stats-row">
            {stats.slice(0, 6).map((stat, idx) => (
              <div key={idx} className="futbin-card-stat">
                <span className="stat-lbl">{stat.name}</span>
                <span className="stat-val">{stat.value}</span>
              </div>
            ))}
          </div>
        )}

        {/* Escudos/Bandeiras: Nation, League, Club (Embaixo das stats) */}
        <div className="futbin-card-badges">
          {data.nation_url && <img src={data.nation_url} className="badge-nation" alt="Nation" referrerPolicy="no-referrer" />}
          {data.league_url && <img src={data.league_url} className="badge-league" alt="League" referrerPolicy="no-referrer" />}
          {data.club_url && <img src={data.club_url} className="badge-club" alt="Club" referrerPolicy="no-referrer" />}
        </div>

        {/* Informações Extras (Skill Moves e Weak Foot) - Canto Direito */}
        {(data.skill_moves || data.weak_foot) && (
          <div className="futbin-card-extras">
            <span>R</span>
            <div className="sm-wf">
              {data.skill_moves || '-'}★{data.weak_foot || '-'}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default FutbinCard;
