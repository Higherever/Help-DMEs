import React, { useMemo } from 'react';

const HERO_IMAGES = [
  '/images/heroes/hero_1.png',
  '/images/heroes/hero_2.png',
  '/images/heroes/hero_3.png',
  '/images/heroes/hero_4.png',
];

export default function LandingPage({ onStart }) {
  const heroImage = useMemo(() => {
    const idx = Math.floor(Math.random() * HERO_IMAGES.length);
    return HERO_IMAGES[idx];
  }, []);

  return (
    <div className="landing-page">
      <div className="landing-bg-glow" />
      <div className="landing-bg-glow-bottom" />

      <div className="hero-container">
        <div className="hero-image-wrapper">
          <img
            src={heroImage}
            alt="EA FC 26 — Help DMEs"
            className="hero-image"
            draggable={false}
          />
        </div>

        <div className="hero-content">
          <div className="landing-logo-wrapper">
            <img src="/logo.svg" alt="Help DMEs Logo" className="landing-logo-img" draggable={false} />
            <span className="landing-logo-text">Help DMEs</span>
          </div>
          <h1 className="hero-title">VAMOS FARMAR</h1>
          <p className="hero-description">
            A ferramenta está pronta. Vamos juntos farmar para o seu DME
            com o assistente de criação de DMEs.
          </p>
          <button className="btn-cta" onClick={onStart}>
            Iniciar montagem de DME
          </button>
        </div>
      </div>
    </div>
  );
}
