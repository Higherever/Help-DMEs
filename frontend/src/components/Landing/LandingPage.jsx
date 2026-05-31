import React, { useEffect, useState } from 'react';
import { DottedSurface } from './DottedSurface';
import { StarButton } from './StarButton';
import { RippleButton } from './RippleButton';

export default function LandingPage({ onStart }) {
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    // A animação do background já inicia imediatamente
    // Os textos e interface aparecem suavemente depois de 1.2s para causar impacto visual inicial
    const timer = setTimeout(() => {
      setLoaded(true);
    }, 1200);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div
      className="landing-page-container"
      style={{
        background: '#000000',
        width: '100vw',
        height: '100vh',
        position: 'relative',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        overflow: 'hidden',
        color: '#ffffff',
        fontFamily: 'var(--font-sans), system-ui, -apple-system, sans-serif',
      }}
    >
      {/* Background animado (sempre renderizado) */}
      <DottedSurface style={{ zIndex: 1 }} />

      {/* Camada da Interface (Fade In) */}
      <div
        className="landing-interface"
        style={{
          position: 'absolute',
          inset: 0,
          zIndex: 10,
          display: 'flex',
          flexDirection: 'column',
          opacity: loaded ? 1 : 0,
          transition: 'opacity 1.5s ease-out',
          pointerEvents: loaded ? 'auto' : 'none', // Só permite cliques quando visível
        }}
      >
        {/* Navbar Superior */}
        <header
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: '1.5rem 3rem',
            width: '100%',
            boxSizing: 'border-box',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            {/* Logo do projeto */}
            <img
              src="/logo.png"
              alt="Help SBC Logo"
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '8px',
                objectFit: 'cover',
                filter: 'invert(1)',
              }}
            />
            <span style={{ fontWeight: 700, fontSize: '1.25rem', letterSpacing: '-0.02em' }}>Help SBC</span>
          </div>

          <StarButton
            backgroundColor="#000000"
            lightColor="#ffffff"
            onClick={() => {}}
          >
            Sobre o Projeto
          </StarButton>
        </header>

        {/* Conteúdo Central (Hero) */}
        <main
          style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            alignItems: 'center',
            textAlign: 'center',
            padding: '0 2rem 15vh 2rem',
          }}
        >
          {/* Chip de Status */}
          <div
            style={{
              background: 'rgba(255, 255, 255, 0.03)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              borderRadius: '9999px',
              padding: '0.4rem 1rem',
              fontSize: '0.8125rem',
              color: 'rgba(255, 255, 255, 0.7)',
              marginBottom: '1.5rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              backdropFilter: 'blur(8px)',
            }}
          >
            <span style={{ display: 'inline-block', width: '6px', height: '6px', borderRadius: '50%', background: '#4f46e5' }}></span>
            Em fase inicial de testes, bugs podem aparecer
          </div>

          {/* Título Principal */}
          <h1
            style={{
              fontSize: 'clamp(3rem, 6vw, 5rem)',
              fontWeight: 800,
              lineHeight: 1.1,
              letterSpacing: '-0.04em',
              margin: '0 0 1.5rem 0',
              maxWidth: '800px',
              background: 'linear-gradient(180deg, #ffffff 0%, rgba(255, 255, 255, 0.7) 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}
          >
            Help SBC
          </h1>

          {/* Subtítulo */}
          <p
            style={{
              fontSize: 'clamp(1.125rem, 2vw, 1.25rem)',
              color: 'rgba(255, 255, 255, 0.6)',
              margin: '0 0 2.5rem 0',
              maxWidth: '600px',
              lineHeight: 1.6,
              fontWeight: 400,
            }}
          >
            Seu clube. Seu plano. Sem gastar coins. <br />
            Antes de queimar qualquer carta, veja exatamente o que vai perder — e se vale a pena.
          </p>

          {/* Botões de Ação */}
          <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
            <StarButton
              backgroundColor="#000000"
              lightColor="#ffffff"
              onClick={onStart}
            >
              Vamos Começar
            </StarButton>

            <button
              className="hero-btn-secondary"
              onClick={() => {}}
              style={{
                background: 'transparent',
                border: 'none',
                padding: '0.875rem 1.5rem',
                color: '#ffffff',
                fontSize: '1rem',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                opacity: 0.8,
                transition: 'opacity 0.2s ease',
              }}
            >
              Learn more <span aria-hidden="true">&rarr;</span>
            </button>
          </div>
        </main>
      </div>

      {/* Estilos para Hover via CSS clássico */}
      <style>{`
        .navbar-btn:hover {
          background: rgba(255, 255, 255, 0.1) !important;
          border-color: rgba(255, 255, 255, 0.2) !important;
        }
        .hero-btn-primary:hover {
          transform: translateY(-2px);
          box-shadow: 0 6px 20px rgba(79, 70, 229, 0.45) !important;
          background: #4338ca !important;
        }
        .hero-btn-primary:active {
          transform: translateY(0);
        }
        .hero-btn-secondary:hover {
          opacity: 1 !important;
        }
      `}</style>
    </div>
  );
}
