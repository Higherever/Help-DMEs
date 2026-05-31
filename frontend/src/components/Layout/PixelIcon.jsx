import React from 'react';

/**
 * Componente PixelIcon
 * Renderiza ícones em estética Pixel Art de 8-bit premium (Streamline Pixel style).
 * Utiliza shape-rendering="crispEdges" para garantir que os pixels fiquem 100% nítidos em qualquer tela.
 */
export default function PixelIcon({ name, size = 22, className = '', active = false }) {
  const color = active ? 'var(--accent)' : 'var(--text-secondary)';

  // Cada ícone é desenhado em uma grade lógica de 16x16
  const renderIcon = () => {
    switch (name) {
      case 'dashboard':
        return (
          // Grade de painéis (Dashboard)
          <g>
            {/* Contorno / Painel 1 (Grande Esquerda) */}
            <rect x="1" y="1" width="6" height="14" fill="none" stroke="currentColor" strokeWidth="1" />
            <rect x="3" y="3" width="2" height="4" fill="currentColor" opacity="0.6" />
            <rect x="3" y="9" width="2" height="2" fill="currentColor" opacity="0.6" />
            
            {/* Painel 2 (Direita Superior) */}
            <rect x="9" y="1" width="6" height="6" fill="none" stroke="currentColor" strokeWidth="1" />
            <rect x="11" y="3" width="2" height="2" fill="currentColor" opacity="0.6" />

            {/* Painel 3 (Direita Inferior) */}
            <rect x="9" y="9" width="6" height="6" fill="none" stroke="currentColor" strokeWidth="1" />
            <rect x="11" y="11" width="2" height="2" fill="currentColor" opacity="0.6" />
          </g>
        );

      case 'sbcs':
      case 'trophy':
        return (
          // Troféu 8-bit clássico (SBCs / DMEs)
          <g>
            {/* Taça superior */}
            <path d="M2,2 h12 v6 h-2 v2 h-8 v-2 h-2 z" fill="none" stroke="currentColor" strokeWidth="1" />
            <rect x="4" y="4" width="8" height="2" fill="currentColor" opacity="0.4" />
            
            {/* Alças laterais */}
            <path d="M1,3 h1 v3 h-1 z" fill="currentColor" />
            <path d="M14,3 h1 v3 h-1 z" fill="currentColor" />
            
            {/* Haste central */}
            <rect x="7" y="10" width="2" height="3" fill="currentColor" />
            
            {/* Base */}
            <rect x="4" y="13" width="8" height="2" fill="none" stroke="currentColor" strokeWidth="1" />
            <rect x="5" y="13" width="6" height="1" fill="currentColor" opacity="0.6" />
          </g>
        );

      case 'squad':
      case 'users':
        return (
          // Dois bonecos pixel art (Elenco / Time)
          <g>
            {/* Boneco 1 (Esquerda) */}
            {/* Cabeça */}
            <rect x="3" y="2" width="4" height="4" fill="none" stroke="currentColor" strokeWidth="1" />
            <rect x="4" y="3" width="2" height="2" fill="currentColor" opacity="0.5" />
            {/* Ombros/Busto */}
            <path d="M1,9 h8 v4 h-8 z" fill="none" stroke="currentColor" strokeWidth="1" />
            <rect x="2" y="10" width="6" height="2" fill="currentColor" opacity="0.3" />

            {/* Boneco 2 (Direita) */}
            {/* Cabeça */}
            <rect x="9" y="5" width="4" height="4" fill="none" stroke="currentColor" strokeWidth="1" />
            <rect x="10" y="6" width="2" height="2" fill="currentColor" opacity="0.5" />
            {/* Ombros/Busto */}
            <path d="M8,11 h7 v3 h-7 z" fill="none" stroke="currentColor" strokeWidth="1" />
            <rect x="9" y="12" width="5" height="1" fill="currentColor" opacity="0.3" />
          </g>
        );

      case 'calculator':
        return (
          // Calculadora 8-bit
          <g>
            {/* Corpo */}
            <rect x="2" y="1" width="12" height="14" fill="none" stroke="currentColor" strokeWidth="1" />
            
            {/* Tela */}
            <rect x="4" y="3" width="8" height="3" fill="none" stroke="currentColor" strokeWidth="1" />
            <rect x="5" y="4" width="6" height="1" fill="currentColor" opacity="0.4" />
            
            {/* Botões */}
            <rect x="4" y="8" width="2" height="2" fill="currentColor" />
            <rect x="7" y="8" width="2" height="2" fill="currentColor" opacity="0.7" />
            <rect x="10" y="8" width="2" height="2" fill="currentColor" />
            
            <rect x="4" y="11" width="2" height="2" fill="currentColor" opacity="0.7" />
            <rect x="7" y="11" width="2" height="2" fill="currentColor" />
            <rect x="10" y="11" width="2" height="2" fill="currentColor" opacity="0.7" />
          </g>
        );

      case 'settings':
        return (
          // Engrenagem 8-bit
          <g>
            {/* Núcleo Central */}
            <rect x="5" y="5" width="6" height="6" fill="none" stroke="currentColor" strokeWidth="1" />
            <rect x="7" y="7" width="2" height="2" fill="none" stroke="currentColor" strokeWidth="1" />
            
            {/* Dentes da engrenagem (Dentes Pixelados nas direções cardinais) */}
            {/* Cima */}
            <rect x="7" y="2" width="2" height="2" fill="currentColor" />
            {/* Baixo */}
            <rect x="7" y="12" width="2" height="2" fill="currentColor" />
            {/* Esquerda */}
            <rect x="2" y="7" width="2" height="2" fill="currentColor" />
            {/* Direita */}
            <rect x="12" y="7" width="2" height="2" fill="currentColor" />

            {/* Dentes diagonais (mais sutis para manter a grade) */}
            <rect x="4" y="4" width="1" height="1" fill="currentColor" />
            <rect x="11" y="4" width="1" height="1" fill="currentColor" />
            <rect x="4" y="11" width="1" height="1" fill="currentColor" />
            <rect x="11" y="11" width="1" height="1" fill="currentColor" />
          </g>
        );

      default:
        return null;
    }
  };

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      style={{
        shapeRendering: 'crispEdges',
        color: color,
        display: 'inline-block',
        verticalAlign: 'middle',
      }}
    >
      {renderIcon()}
    </svg>
  );
}
