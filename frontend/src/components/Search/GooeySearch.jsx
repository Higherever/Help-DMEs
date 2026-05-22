import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

export default function GooeySearch({ value, onChange, placeholder = 'Buscar...', suggestions = [] }) {
  const [isActive, setIsActive] = useState(false);
  const inputRef = useRef(null);
  const containerRef = useRef(null);

  // Se houver valor externo (ex: reset ou busca iniciada), expandir automaticamente
  useEffect(() => {
    if (value) {
      setIsActive(true);
    }
  }, [value]);

  const handleButtonClick = (e) => {
    e.stopPropagation();
    if (!isActive) {
      setIsActive(true);
      setTimeout(() => {
        inputRef.current?.focus();
      }, 100);
    } else {
      // Se já estiver ativo, limpa e fecha
      onChange('');
      setIsActive(false);
      inputRef.current?.blur();
    }
  };

  const handleInputBlur = () => {
    // Se o campo estiver vazio, fecha a barra automaticamente
    if (!value || value.trim() === '') {
      setTimeout(() => {
        setIsActive(false);
      }, 180);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Escape') {
      onChange('');
      setIsActive(false);
      inputRef.current?.blur();
    }
  };

  // Fecha a barra se o usuário clicar fora do container e o campo estiver vazio
  useEffect(() => {
    const handleOutsideClick = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target) && (!value || value.trim() === '')) {
        setIsActive(false);
      }
    };
    document.addEventListener('click', handleOutsideClick);
    return () => document.removeEventListener('click', handleOutsideClick);
  }, [value]);

  const showSuggestions = isActive && suggestions && suggestions.length > 0;

  return (
    <div className="neon-search-outer-container" ref={containerRef}>
      {/* Container principal que aplica as classes de ativação baseadas no React */}
      <div className={`neon-search-container ${isActive ? 'active' : ''}`}>
        <input
          ref={inputRef}
          type="text"
          className="neon-search-input"
          placeholder={placeholder}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onBlur={handleInputBlur}
          onKeyDown={handleKeyDown}
        />
        <div className="neon-search-btn-trigger" onClick={handleButtonClick}></div>
      </div>

      {/* Painel de sugestões rápidas flutuando logo abaixo de forma nítida e refinada */}
      <AnimatePresence>
        {showSuggestions && (
          <motion.div
            className="gooey-search-suggestions-panel"
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ type: 'spring', stiffness: 220, damping: 22 }}
            style={{
              position: 'absolute',
              top: '75px',
              left: 0,
              width: '300px',
              zIndex: 100
            }}
          >
            <span className="gooey-search-suggestions-title">Atalhos:</span>
            <div className="gooey-search-suggestions-list">
              {suggestions.map((tag) => (
                <button
                  key={tag}
                  className="gooey-search-suggestion-pill"
                  onClick={() => {
                    onChange(tag);
                    inputRef.current?.focus();
                  }}
                >
                  {tag}
                </button>
              ))}
            </div>
            {value && (
              <button 
                className="gooey-search-clear-btn"
                onClick={() => {
                  onChange('');
                  inputRef.current?.focus();
                }}
              >
                Limpar
              </button>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
