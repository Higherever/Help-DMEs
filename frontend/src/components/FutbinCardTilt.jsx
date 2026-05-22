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
    
    // Limitado a 10 graus de rotação para manter elegância e legibilidade
    const rotateX = ((yc - y) / yc) * 10;
    const rotateY = ((x - xc) / xc) * 10;

    // Percentual do cursor para controlar a varredura de luz holográfica
    const percentX = (x / rect.width) * 100;
    const percentY = (y / rect.height) * 100;

    // Injeção de variáveis CSS diretamente no nó do DOM
    // Isso é executado de forma imediata na GPU sem provocar renderizações do React
    card.style.setProperty('--rx', `${rotateX}deg`);
    card.style.setProperty('--ry', `${rotateY}deg`);
    card.style.setProperty('--mx', `${percentX}%`);
    card.style.setProperty('--my', `${percentY}%`);
  };

  const handleMouseLeave = () => {
    const card = cardRef.current;
    if (!card) return;

    // Transição suave de volta ao alinhamento reto padrão
    card.style.setProperty('--rx', '0deg');
    card.style.setProperty('--ry', '0deg');
    card.style.setProperty('--mx', '50%');
    card.style.setProperty('--my', '50%');
  };

  return (
    <div 
      ref={cardRef}
      className="tilt-card-container"
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
    >
      <div className="tilt-card-shine" />
      <div className="tilt-card-content">
        {children}
      </div>
    </div>
  );
}
