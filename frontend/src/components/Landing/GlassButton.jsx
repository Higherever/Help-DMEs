import React from 'react';
import styles from './GlassButton.module.css';

export const GlassButton = ({ children, onClick, className = '' }) => {
  return (
    <button className={`${styles.button} ${className}`} onClick={onClick}>
      {children}
    </button>
  );
};
