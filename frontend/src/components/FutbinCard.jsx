import React, { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';

/**
 * FutbinCard — Card de jogador EA FC 26 via CSS Puro.
 *
 * Composição de 12 camadas absolutas:
 *   1. Background template (card art)
 *   2. Face render do jogador (PNG transparente)
 *   3. Sombra inferior (gradiente para legibilidade)
 *   4. Rating (canto sup. esquerdo)
 *   5. Posição principal (abaixo do rating)
 *   6. Posições alternativas (canto sup. direito)
 *   7. SM★WF (direita, abaixo das alt pos)
 *   8. Nome do jogador (centro)
 *   9. Linha divisória
 *  10. 6 Face Stats (PAC/SHO/PAS/DRI/DEF/PHY)
 *  11. Badges (nação, liga, clube)
 *  12. Playstyles (coluna flutuante esquerda)
 *
 * @param {Object} data - Dados do card
 * @param {string} size - 'sm' | 'md' | 'lg' | 'xl'
 * @param {boolean} showDetails - Mostra sub-atributos
 */
const FutbinCard = ({ data, size = 'lg', className = '', showDetails = false }) => {
  const [expanded, setExpanded] = useState(showDetails);
  const [hovered, setHovered] = useState(false);

  if (!data) {
    return (
      <div className={`futbin-card-wrapper card-${size} ${className}`}>
        <div className="futbin-card-placeholder">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" opacity="0.2">
            <rect x="3" y="3" width="18" height="18" rx="2" />
            <path d="M3 9h18M9 21V9" />
          </svg>
        </div>
      </div>
    );
  }

  // ── URLs com fallback ──
  const bgUrl = data.bg_url_hd || data.bg_url || '';

  // Estado resiliente para gerenciar a imagem de background e fallbacks
  const [imgSrc, setImgSrc] = useState(bgUrl);

  React.useEffect(() => {
    setImgSrc(bgUrl);
  }, [bgUrl]);

  const handleImageError = () => {
    // Se a imagem de card HD completo falhar, tentamos carregar a render/face original
    if (imgSrc !== data.face_url && data.face_url) {
      setImgSrc(data.face_url);
    } else {
      // Fallback absoluto: ocultar a tag img
      setImgSrc('');
    }
  };

  const formatName = (str) => {
    if (!str) return '';
    return str.split(' ').map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()).join(' ');
  };
  const name = formatName(data.name);

  // ── Playstyles ──
  let playstyles = data.playstyles || [];
  if (typeof data.playstyles_json === 'string' && !playstyles.length) {
    try { playstyles = JSON.parse(data.playstyles_json); } catch { playstyles = []; }
  }

  // ── Sub-atributos ──
  const subStats = buildSubStats(data);
  const hasSubStats = subStats.some(g => g.stats.some(s => s.value != null));

  return (
    <div className={`futbin-card-wrapper card-${size} ${className}`}>

      {/* ═══ Card Visual ═══ */}
      <div 
        className="futbin-card"
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
      >
        {imgSrc && (
          <img
            className="futbin-card-bg"
            src={imgSrc}
            alt={name}
            onError={handleImageError}
            loading="eager"
            referrerPolicy="no-referrer"
            draggable={false}
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'contain',
              borderRadius: 'inherit',
            }}
          />
        )}
      </div>

      {/* ═══ Camada 12: Playstyles (fora do card, flutuante esquerda) ═══ */}
      {playstyles.length > 0 && (
        <div className="futbin-card-playstyles">
          {playstyles.map((ps, i) => (
            <div key={i} className={`playstyle-icon-wrapper ${ps.is_plus ? 'plus' : ''}`} title={ps.name}>
              <img src={ps.icon_url} alt={ps.name} loading="lazy" referrerPolicy="no-referrer" />
            </div>
          ))}
        </div>
      )}

      {/* ═══ Sub-atributos expandíveis ═══ */}
      {hasSubStats && (
        <div className="futbin-card-details">
          <button className="futbin-details-toggle" onClick={() => setExpanded(!expanded)}>
            <span>Sub-Atributos</span>
            {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          </button>

          {expanded && (
            <div className="futbin-substats-grid">
              {subStats.map((group, gi) => (
                <div key={gi} className="substats-group">
                  <div className="substats-group-header">
                    <span className="substats-group-name">{group.name}</span>
                    <span className="substats-group-value">{group.faceValue ?? '-'}</span>
                  </div>
                  {group.stats.map((s, si) => (
                    <div key={si} className="substat-row">
                      <span className="substat-name">{s.label}</span>
                      <div className="substat-bar-container">
                        <div className={`substat-bar ${s.value >= 80 ? 'high' : s.value >= 60 ? 'mid' : 'low'}`}
                          style={{ width: `${Math.min(s.value || 0, 99)}%` }} />
                      </div>
                      <span className={`substat-value ${s.value >= 80 ? 'high' : s.value >= 60 ? 'mid' : 'low'}`}>
                        {s.value ?? '-'}
                      </span>
                    </div>
                  ))}
                </div>
              ))}

              {/* Bio */}
              {(data.height || data.weight || data.foot || data.workrates) && (
                <div className="substats-group substats-bio">
                  <div className="substats-group-header">
                    <span className="substats-group-name">Bio</span>
                  </div>
                  {data.height && <div className="substat-row bio"><span>Altura</span><span>{data.height} cm</span></div>}
                  {data.weight && <div className="substat-row bio"><span>Peso</span><span>{data.weight} kg</span></div>}
                  {data.age && <div className="substat-row bio"><span>Idade</span><span>{data.age}</span></div>}
                  {data.foot && <div className="substat-row bio"><span>Pé</span><span>{data.foot}</span></div>}
                  {data.workrates && <div className="substat-row bio"><span>Workrates</span><span>{data.workrates}</span></div>}
                  {data.accelerate_type && (
                    <div className="substat-row bio">
                      <span>AcceleRATE</span>
                      <span className={`accel-text accel-${data.accelerate_type.toLowerCase()}`}>{data.accelerate_type}</span>
                    </div>
                  )}
                </div>
              )}

              {/* Meta */}
              {data.meta_rating && (
                <div className="substats-group substats-meta">
                  <div className="substats-group-header">
                    <span className="substats-group-name">Meta</span>
                  </div>
                  <div className="substat-row bio">
                    <span>Meta Rating</span>
                    <span className="meta-rating-value">{data.meta_rating}</span>
                  </div>
                  {data.meta_tier && (
                    <div className="substat-row bio">
                      <span>Tier</span>
                      <span className={`meta-tier-badge tier-${data.meta_tier.replace('+','plus').toLowerCase()}`}>{data.meta_tier}</span>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};


function buildSubStats(data) {
  return [
    { name: 'PAC', faceValue: data.pace ?? fv(data, 'PAC'),
      stats: [
        { label: 'Aceleração', value: data.acceleration },
        { label: 'Vel. Sprint', value: data.sprint_speed },
      ]},
    { name: 'SHO', faceValue: data.shooting ?? fv(data, 'SHO'),
      stats: [
        { label: 'Finalização', value: data.finishing },
        { label: 'Pot. Chute', value: data.shot_power },
        { label: 'Chute Longo', value: data.long_shots },
        { label: 'Voleios', value: data.volleys },
        { label: 'Posicional', value: data.positioning_att },
        { label: 'Pênaltis', value: data.penalties },
      ]},
    { name: 'PAS', faceValue: data.passing ?? fv(data, 'PAS'),
      stats: [
        { label: 'Passe Curto', value: data.short_passing },
        { label: 'Passe Longo', value: data.long_passing },
        { label: 'Cruzamento', value: data.crossing },
        { label: 'Curva', value: data.curve },
        { label: 'Falta', value: data.free_kick },
        { label: 'Visão', value: data.vision },
      ]},
    { name: 'DRI', faceValue: data.dribbling_stat ?? fv(data, 'DRI'),
      stats: [
        { label: 'Agilidade', value: data.agility },
        { label: 'Equilíbrio', value: data.balance },
        { label: 'Reações', value: data.reactions },
        { label: 'Controle', value: data.ball_control },
        { label: 'Compostura', value: data.composure },
        { label: 'Drible', value: data.skill_dribbling },
      ]},
    { name: 'DEF', faceValue: data.defending ?? fv(data, 'DEF'),
      stats: [
        { label: 'Intercep.', value: data.interceptions },
        { label: 'Cabeceio', value: data.heading },
        { label: 'Marcação', value: data.marking },
        { label: 'Carrinho', value: data.standing_tackle },
        { label: 'Deslize', value: data.sliding_tackle },
      ]},
    { name: 'PHY', faceValue: data.physic ?? fv(data, 'PHY'),
      stats: [
        { label: 'Salto', value: data.jumping },
        { label: 'Estamina', value: data.stamina },
        { label: 'Força', value: data.strength },
        { label: 'Agressão', value: data.aggression },
      ]},
  ];
}

function fv(data, name) {
  if (!data.stats) return null;
  const s = data.stats.find(s => s.name === name);
  return s ? parseInt(s.value) : null;
}

export default FutbinCard;
