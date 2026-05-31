import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';

export default function TransitionGrid({ pageKey }) {
  const [blocks, setBlocks] = useState([]);

  useEffect(() => {
    // Inicializa a lista de 144 blocos com atrasos aleatórios para efeito orgânico
    const list = Array.from({ length: 144 }).map((_, i) => ({
      id: i,
      delay: Math.random() * 0.45
    }));
    setBlocks(list);
  }, [pageKey]);

  if (blocks.length === 0) return null;

  return (
    <div className="global-transition-grid">
      {blocks.map((block) => (
        <motion.div
          key={block.id}
          className="transition-grid-block"
          initial={{ opacity: 1 }}
          animate={{ opacity: 0 }}
          transition={{
            duration: 0.35,
            delay: block.delay,
            ease: [0.16, 1, 0.3, 1]
          }}
        />
      ))}
    </div>
  );
}
