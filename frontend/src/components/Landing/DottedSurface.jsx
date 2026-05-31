import React, { useEffect, useRef } from 'react';
import { useTheme } from 'next-themes';
import * as THREE from 'three';

export function DottedSurface({ className, style, ...props }) {
  const { theme } = useTheme();
  const containerRef = useRef(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const SEPARATION = 150;
    const AMOUNTX = 80;
    const AMOUNTY = 60;

    // Scene setup
    const scene = new THREE.Scene();
    scene.fog = new THREE.Fog(0xffffff, 2000, 10000);

    const camera = new THREE.PerspectiveCamera(
      60,
      window.innerWidth / window.innerHeight,
      1,
      10000,
    );
    camera.position.set(0, 355, 1220);

    const renderer = new THREE.WebGLRenderer({
      alpha: true,
      antialias: true,
    });
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setClearColor(0x000000, 0); // transparente

    container.appendChild(renderer.domElement);

    // Build geometry
    const geometry = new THREE.BufferGeometry();
    const positions = [];
    const colors = [];
    const isDark = theme !== 'light';

    for (let ix = 0; ix < AMOUNTX; ix++) {
      for (let iy = 0; iy < AMOUNTY; iy++) {
        positions.push(
          ix * SEPARATION - (AMOUNTX * SEPARATION) / 2,
          0,
          iy * SEPARATION - (AMOUNTY * SEPARATION) / 2,
        );
        if (isDark) {
          colors.push(200, 200, 200);
        } else {
          colors.push(0, 0, 0);
        }
      }
    }

    geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
    // normalize=true: THREE.js divide os valores [0-255] por 255 → [0.0, 1.0]
    geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3, true));

    const material = new THREE.PointsMaterial({
      size: 8,
      vertexColors: true,
      transparent: true,
      opacity: 0.8,
      sizeAttenuation: true,
    });

    const points = new THREE.Points(geometry, material);
    scene.add(points);

    // --- CORREÇÃO DO BUG ---
    // 1. Flag `cancelled` para parar o loop no cleanup, independente do rAF ID
    // 2. `animationId` é fechado pela closure do cleanup (não via snapshot no ref)
    let cancelled = false;
    let animationId;
    let count = 0;

    const animate = () => {
      if (cancelled) return; // para o loop imediatamente se cleanup rodou

      animationId = requestAnimationFrame(animate); // rAF ID sempre atualizado

      const posAttr = geometry.attributes.position;
      const posArr = posAttr.array;

      let i = 0;
      for (let ix = 0; ix < AMOUNTX; ix++) {
        for (let iy = 0; iy < AMOUNTY; iy++) {
          posArr[i * 3 + 1] =
            Math.sin((ix + count) * 0.3) * 50 +
            Math.sin((iy + count) * 0.5) * 50;
          i++;
        }
      }

      posAttr.needsUpdate = true;
      renderer.render(scene, camera);
      count += 0.1; // loop infinito: count cresce sem limite, sin() garante ciclo contínuo
    };

    const handleResize = () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    };

    window.addEventListener('resize', handleResize);
    animate();

    // Cleanup — usa closure sobre variáveis locais, nunca snapshots
    return () => {
      cancelled = true;             // 1. para o loop na próxima checagem
      cancelAnimationFrame(animationId); // 2. cancela o frame pendente atual
      window.removeEventListener('resize', handleResize);

      // Dispose Three.js resources
      geometry.dispose();
      material.dispose();
      renderer.dispose();

      // Remove canvas do DOM
      if (container && renderer.domElement && container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
    };
  }, [theme]);

  return (
    <div
      ref={containerRef}
      className={className}
      style={{
        pointerEvents: 'none',
        position: 'fixed',
        inset: 0,
        zIndex: -1,
        ...style,
      }}
      {...props}
    />
  );
}
