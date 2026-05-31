import React, { useRef } from 'react';
import './FutbinCardTilt.css';

export default function FutbinCardTilt({ children }) {
  const cardRef = useRef(null);

  const handleMouseMove = (e) => {
    const card = cardRef.current;
    if (!card) return;

    const rect = card.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const xc = rect.width / 2;
    const yc = rect.height / 2;
    
    // Limitado a 20 graus de rotação para intensificar o efeito 3D com sofisticação
    const rotateX = ((yc - y) / yc) * 20;
    const rotateY = ((x - xc) / xc) * 20;

    // Injeção de variáveis CSS diretamente no nó do DOM para execução imediata na GPU
    card.style.setProperty('--rx', `${rotateX}deg`);
    card.style.setProperty('--ry', `${rotateY}deg`);
  };

  const handleMouseLeave = () => {
    const card = cardRef.current;
    if (!card) return;

    // Transição suave de volta ao alinhamento reto padrão
    card.style.setProperty('--rx', '0deg');
    card.style.setProperty('--ry', '0deg');
  };

  return (
    <div 
      ref={cardRef}
      className="tilt-card-container"
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
    >
      <div className="tilt-card-content">
        {children}
      </div>
    </div>
  );
}
