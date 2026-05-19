import React from 'react';

const FutbinCard = ({ data }) => {
  if (!data) return null;

  const bgUrl = data.bg_url || '';
  const faceUrl = data.face_url || '';
  const stats = data.stats || [];

  return (
    <div className="futbin-card">
      {/* Fundo da carta */}
      {bgUrl && (
        <img 
          src={bgUrl} 
          alt="" 
          className="futbin-card-bg" 
          referrerPolicy="no-referrer"
          draggable="false"
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
        />
      )}
      
      {/* Rating + Position */}
      <div className="futbin-card-info">
        <div className="futbin-card-rating">{data.rating}</div>
        <div className="futbin-card-position">{data.position}</div>
      </div>
      
      {/* Nome do jogador */}
      <div className="futbin-card-name">{data.name}</div>
      
      {/* Linha divisória */}
      <div className="futbin-card-divider"></div>
      
      {/* 6 Stats */}
      <div className="futbin-card-stats">
        <div className="futbin-card-stats-col">
          {stats.slice(0, 3).map((stat, idx) => (
            <div key={idx} className="futbin-card-stat">
              <span className="stat-val">{stat.value}</span>
              <span className="stat-lbl">{stat.name}</span>
            </div>
          ))}
        </div>
        <div className="futbin-card-stats-col">
          {stats.slice(3, 6).map((stat, idx) => (
            <div key={idx} className="futbin-card-stat">
              <span className="stat-val">{stat.value}</span>
              <span className="stat-lbl">{stat.name}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default FutbinCard;
