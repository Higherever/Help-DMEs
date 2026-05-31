import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { useApi } from '../../hooks/useApi';
import './ThreeDCard.css';

export default function ThreeDCard({ squadPlayers }) {
  const containerRef = useRef(null);
  const canvasRef = useRef(null);
  const { API_BASE } = useApi();
  
  const [loading, setLoading] = useState(true);

  // Listas de cartas disponíveis para o sorteio
  const availableImagesRef = useRef([]);
  const squadPlayersRef = useRef([]);

  // Sincronizar jogadores do elenco
  useEffect(() => {
    if (squadPlayers && squadPlayers.length > 0) {
      squadPlayersRef.current = squadPlayers;
    }
  }, [squadPlayers]);

  // Carregar lista de imagens do catálogo como fallback/mistura
  useEffect(() => {
    let active = true;
    async function fetchImages() {
      try {
        const res = await fetch(`${API_BASE}/api/cards/all-images`);
        if (!res.ok) throw new Error('Falha ao obter catálogo');
        const data = await res.json();
        if (active && data && data.length > 0) {
          availableImagesRef.current = data;
        }
      } catch (e) {
        console.error('Erro ao carregar catálogo de cartas:', e);
      } finally {
        if (active) setLoading(false);
      }
    }
    fetchImages();
    return () => { active = false; };
  }, [API_BASE]);

  useEffect(() => {
    if (loading || (availableImagesRef.current.length === 0 && squadPlayersRef.current.length === 0)) return;

    const container = containerRef.current;
    const canvas = canvasRef.current;
    if (!container || !canvas) return;

    // --- CONFIGURAÇÃO INICIAL DO RENDERER (TELA CHEIA FIXED BACKGROUND) ---
    let W = window.innerWidth;
    let H = window.innerHeight;
    
    const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(W, H);
    renderer.shadowMap.enabled = true;

    const scene = new THREE.Scene();
    
    // Câmera com ângulo áureo de 45°
    const camera = new THREE.PerspectiveCamera(45, W / H, 0.1, 100);
    camera.position.z = 10;

    const textureLoader = new THREE.TextureLoader();

    // Helper para obter uma imagem de jogador aleatória
    const getRandomPlayerCard = (excludeUrl = '') => {
      const useSquad = squadPlayersRef.current.length > 0 && Math.random() < 0.6;
      
      if (useSquad) {
        const highRated = [...squadPlayersRef.current].sort((a, b) => b.rating - a.rating);
        const pool = highRated.slice(0, 15);
        const player = pool[Math.floor(Math.random() * pool.length)];
        
        if (player.definition_id) {
          const url = `/images/cards/full/fc_player_${player.definition_id}_${player.name.toLowerCase().replace(/\s+/g, '_')}.png`;
          const fullUrl = `${API_BASE}${url}`;
          if (fullUrl !== excludeUrl) {
            return { name: player.name, url: fullUrl };
          }
        }
      }

      const cat = availableImagesRef.current;
      if (cat.length > 0) {
        let attempts = 0;
        let selected = cat[Math.floor(Math.random() * cat.length)];
        let fullUrl = `${API_BASE}${selected.full_image_url}`;
        
        while (fullUrl === excludeUrl && attempts < 10 && cat.length > 1) {
          selected = cat[Math.floor(Math.random() * cat.length)];
          fullUrl = `${API_BASE}${selected.full_image_url}`;
          attempts++;
        }

        const namePart = selected.name
          .replace("fc_player_", "")
          .replace(/\d+_/, "")
          .replace(".png", "")
          .replace(/_/g, " ");
        const friendlyName = namePart.charAt(0).toUpperCase() + namePart.slice(1);

        return { name: friendlyName, url: fullUrl };
      }

      return { name: "Oliver Kahn", url: `${API_BASE}/images/cards/full/fc_player_10_oliver_kahn.png` };
    };

    // --- CONFIGURAÇÃO FÍSICA DOS CORPOS E COLISÕES (EXATAMENTE 2 CARTAS) ---
    const NUM_CARDS = 2;
    
    // Hitbox física milimétrica otimizada na linha do card (reduzido para colisão colada lateral de borda)
    const cardWidth = 1.68; 
    const cardHeight = 2.52;
    const cardRadius = 0.95; // Raio da Bounding Sphere reduzido para colisão colada visual
    const colDiameter = cardRadius * 2.0;

    const cardsData = [];


    const activeUrls = [];

    // Limites de viewport para confinamento e spawning
    const limitX = 7.2;
    const limitY = 4.2;
    const limitZ = 2.0;

    // ALGORITMO DE SPAWNING SETORIAL 100% DISPERSO (NUNCA NO MESMO PONTO)
    const getSectorSpawningPosition = (index) => {
      const pos = new THREE.Vector3();
      const jitterX = (Math.random() - 0.5) * limitX * 0.22;
      const jitterY = (Math.random() - 0.5) * limitY * 0.22;
      const jitterZ = (Math.random() - 0.5) * limitZ * 0.6;

      switch (index) {
        case 0: // Canto superior esquerdo
          pos.set(-limitX * 0.55 + jitterX, limitY * 0.55 + jitterY, jitterZ);
          break;
        case 1: // Canto superior direito
          pos.set(limitX * 0.55 + jitterX, limitY * 0.55 + jitterY, jitterZ);
          break;
        case 2: // Canto inferior esquerdo
          pos.set(-limitX * 0.55 + jitterX, -limitY * 0.55 + jitterY, jitterZ);
          break;
        case 3: // Canto inferior direito
          pos.set(limitX * 0.55 + jitterX, -limitY * 0.55 + jitterY, jitterZ);
          break;
        case 4: // Centro
        default:
          pos.set(jitterX, jitterY, jitterZ);
          break;
      }
      return pos;
    };

    for (let i = 0; i < NUM_CARDS; i++) {
      const cardFront = getRandomPlayerCard();
      const cardBack = getRandomPlayerCard(cardFront.url);
      
      activeUrls.push(cardFront.url, cardBack.url);

      const frontTexture = textureLoader.load(cardFront.url);
      frontTexture.colorSpace = THREE.SRGBColorSpace;

      const backTexture = textureLoader.load(cardBack.url);
      backTexture.colorSpace = THREE.SRGBColorSpace;

      const frontMaterial = new THREE.MeshStandardMaterial({ 
        map: frontTexture, 
        roughness: 0.22,
        metalness: 0.15,
        transparent: true,
        alphaTest: 0.05,
        depthWrite: true,
        side: THREE.FrontSide
      });

      const backMaterial = new THREE.MeshStandardMaterial({ 
        map: backTexture, 
        roughness: 0.22,
        metalness: 0.15,
        transparent: true,
        alphaTest: 0.05,
        depthWrite: true,
        side: THREE.FrontSide
      });

      const cardGroup = new THREE.Group();

      const frontGeo = new THREE.PlaneGeometry(cardWidth, cardHeight);
      const frontMesh = new THREE.Mesh(frontGeo, frontMaterial);
      frontMesh.position.z = 0.008;
      cardGroup.add(frontMesh);

      const backGeo = new THREE.PlaneGeometry(cardWidth, cardHeight);
      const backMesh = new THREE.Mesh(backGeo, backMaterial);
      backMesh.position.z = -0.008;
      backMesh.rotation.y = Math.PI; 
      cardGroup.add(backMesh);

      // Posição inicial perfeitamente dispersa nos cantos opostos do viewport virtual
      const spawnPos = getSectorSpawningPosition(i === 0 ? 0 : 3);
      cardGroup.position.copy(spawnPos);

      // Rotações aleatórias iniciais
      cardGroup.rotation.set(
        Math.random() * Math.PI * 2,
        Math.random() * Math.PI * 2,
        Math.random() * Math.PI * 2
      );

      scene.add(cardGroup);



      // VELOCIDADE REDUZIDA EM MAIS 30% DO QUE ATUALMENTE E DIREÇÕES 100% UNIFORMES
      // Velocidades de trajetória ultra lentas, nobres e sofisticadas (magnitude 1.6 a 2.4)
      const speedMagnitude = THREE.MathUtils.randFloat(1.6, 2.4); 
      
      // Direção esférica uniforme pura calculada manualmente (estabilidade total)
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos((Math.random() * 2) - 1);
      const uniformDirection = new THREE.Vector3(
        Math.sin(phi) * Math.cos(theta),
        Math.sin(phi) * Math.sin(theta),
        Math.cos(phi)
      );
      const initialVelocity = uniformDirection.multiplyScalar(speedMagnitude);

      // Rotação física caótica inicial suave, cadenciada e majestosa
      const initialAngularVelocity = new THREE.Vector3(
        (Math.random() - 0.5) * 0.7,
        (Math.random() - 0.5) * 0.7,
        (Math.random() - 0.5) * 0.5
      );

      cardsData.push({
        group: cardGroup,
        frontMesh,
        backMesh,
        frontName: cardFront.name,
        backName: cardBack.name,
        position: cardGroup.position,
        velocity: initialVelocity,
        angularVelocity: initialAngularVelocity,
        mass: 1.0,
        invMass: 1.0,
        restitution: 0.95, // Rebate com alta restituição elástica no vácuo
        friction: 0.15,
        inertia: (2.0 / 5.0) * 1.0 * cardRadius * cardRadius,
        invInertia: 1.0 / ((2.0 / 5.0) * 1.0 * cardRadius * cardRadius),
        wasSwappingFront: false,
        wasSwappingBack: false
      });
    }

    // --- ILUMINAÇÃO DINÂMICA ---
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.7);
    scene.add(ambientLight);

    const keyLight = new THREE.DirectionalLight(0xffffff, 0.6);
    keyLight.position.set(5, 5, 5);
    scene.add(keyLight);

    const pointLight = new THREE.PointLight(0xffffff, 4.0, 15);
    pointLight.position.set(0, 0, 3);
    scene.add(pointLight);


    // --- ALGORITMO DE SIMULAÇÃO DE FÍSICA E COLISÃO ELÁSTICA EM 3D ---
    // --- ALGORITMO DE SIMULAÇÃO DE FÍSICA E COLISÃO ELÁSTICA EM 3D (SPHERE-COMPOSITE COLLIDER - PRECISA DE BORDA) ---
    function resolvePhysicsCollisions(bodyA, bodyB) {
      // Offsets locais das 3 sub-esferas cobrindo verticalmente a carta de altura 2.52 e largura 1.68
      const offsets = [0.82, 0.0, -0.82];
      const radius = 0.80; // Diâmetro de colisão de sub-esfera é 1.60 (perfeito para largura de 1.68)
      const colDist = radius * 2.0;

      // Testa a colisão entre todas as combinações de sub-esferas das duas cartas
      for (let i = 0; i < 3; i++) {
        for (let j = 0; j < 3; j++) {
          // Calcula posições globais das sub-esferas aplicando a orientação rotacional do grupo
          const posA = new THREE.Vector3(0, offsets[i], 0).applyQuaternion(bodyA.group.quaternion).add(bodyA.position);
          const posB = new THREE.Vector3(0, offsets[j], 0).applyQuaternion(bodyB.group.quaternion).add(bodyB.position);

          const delta = new THREE.Vector3().subVectors(posB, posA);
          const distance = delta.length();

          // Se a distância entre sub-esferas for menor que a soma dos raios, colidiu fisicamente!
          if (distance < colDist && distance > 0) {
            const normal = delta.clone().normalize();

            // Ponto de contato na superfície das sub-esferas
            const contactPointA = normal.clone().multiplyScalar(radius).add(posA).sub(bodyA.position);
            const contactPointB = normal.clone().multiplyScalar(-radius).add(posB).sub(bodyB.position);

            // Resposta física de impulso baseada no ponto de contato preciso da sub-esfera
            const vContactA = new THREE.Vector3()
              .crossVectors(bodyA.angularVelocity, contactPointA)
              .add(bodyA.velocity);

            const vContactB = new THREE.Vector3()
              .crossVectors(bodyB.angularVelocity, contactPointB)
              .add(bodyB.velocity);

            const vRel = new THREE.Vector3().subVectors(vContactB, vContactA);
            const vRelNormal = vRel.dot(normal);

            // Se estão se aproximando, resolve o rebate inercial
            if (vRelNormal < 0) {
              const e = Math.sqrt(bodyA.restitution * bodyB.restitution);

              // Magnitude do Impulso Normal (Jn)
              const normalDenom = bodyA.invMass + bodyB.invMass;
              const jnMagnitude = -(1.0 + e) * vRelNormal / normalDenom;

              const impulseNormal = normal.clone().multiplyScalar(jnMagnitude);

              // Magnitude do Impulso Tangencial (Fricção na superfície)
              const vRelTangent = vRel.clone().addScaledVector(normal, -vRelNormal);
              const tangentSpeed = vRelTangent.length();

              const impulseTangent = new THREE.Vector3();

              if (tangentSpeed > 1e-4) {
                const tangent = vRelTangent.clone().normalize();

                const rSqOverI_A = contactPointA.lengthSq() * bodyA.invInertia;
                const rSqOverI_B = contactPointB.lengthSq() * bodyB.invInertia;
                const tangentDenom = bodyA.invMass + bodyB.invMass + rSqOverI_A + rSqOverI_B;

                const jtIdeal = -tangentSpeed / tangentDenom;
                const mu = Math.sqrt(bodyA.friction * bodyB.friction);

                const jtClamped = Math.max(jtIdeal, -mu * jnMagnitude);
                impulseTangent.copy(tangent).multiplyScalar(jtClamped);
              }

              // Impulso Total
              const totalImpulse = new THREE.Vector3().addVectors(impulseNormal, impulseTangent);

              // Aplicar Impulso às Velocidades Lineares (Translação)
              bodyA.velocity.addScaledVector(totalImpulse, -bodyA.invMass);
              bodyB.velocity.addScaledVector(totalImpulse, bodyB.invMass);

              // Aplicar Impulso às Velocidades Angulares (Torque caótico)
              const torqueA = new THREE.Vector3().crossVectors(contactPointA, totalImpulse.clone().negate());
              bodyA.angularVelocity.addScaledVector(torqueA, bodyA.invInertia);

              const torqueB = new THREE.Vector3().crossVectors(contactPointB, totalImpulse);
              bodyB.angularVelocity.addScaledVector(torqueB, bodyB.invInertia);

              // Correção de Penetração Numérica (Evita afundamento mútuo)
              const percent = 0.55; 
              const slop = 0.005;
              const penetration = colDist - distance;

              if (penetration > slop) {
                const correctionMagnitude = ((penetration - slop) / (bodyA.invMass + bodyB.invMass)) * percent;
                const correctionVector = normal.clone().multiplyScalar(correctionMagnitude);

                bodyA.position.addScaledVector(correctionVector, -bodyA.invMass);
                bodyB.position.addScaledVector(correctionVector, bodyB.invMass);
              }
            }
            return; // Resolve apenas um ponto de sub-esfera por frame para manter o solver estável
          }
        }
      }
    }

    // --- LOOP DE ANIMAÇÃO PRINCIPAL ---
    const clock = new THREE.Clock();
    let animId;

    const animate = () => {
      animId = requestAnimationFrame(animate);
      const dt = Math.min(clock.getDelta(), 0.08); 

      // 1. RESOLVER COLISÃO FÍSICA ENTRE TODOS OS PARES DE CARTAS
      for (let i = 0; i < NUM_CARDS; i++) {
        for (let j = i + 1; j < NUM_CARDS; j++) {
          resolvePhysicsCollisions(cardsData[i], cardsData[j]);
        }
      }

      let closestCard = null;
      let maxZ = -Infinity;

      cardsData.forEach((body, idx) => {
        // Integração Linear Física Pura (Euler-Cromer) - 100% Independente
        body.position.addScaledVector(body.velocity, dt);

        // Integração Rotacional Física Pura via Quaternions - 100% Independente e Robusta
        const angle = body.angularVelocity.length() * dt;
        if (angle > 0) {
          const axis = body.angularVelocity.clone().normalize();
          const qDelta = new THREE.Quaternion().setFromAxisAngle(axis, angle);
          body.group.quaternion.premultiply(qDelta);
        }

        // Limites de Viewport Invisível (Ricochete nas bordas virtuais)
        if (Math.abs(body.position.x) > limitX) {
          body.velocity.x *= -body.restitution;
          body.position.x = Math.sign(body.position.x) * limitX;
        }
        if (Math.abs(body.position.y) > limitY) {
          body.velocity.y *= -body.restitution;
          body.position.y = Math.sign(body.position.y) * limitY;
        }
        if (Math.abs(body.position.z) > limitZ) {
          body.velocity.z *= -body.restitution;
          body.position.z = Math.sign(body.position.z) * limitZ;
        }

        // LIMITAÇÃO DE VELOCIDADE ELEGANTE E SUAVE (MAIS 30% REDUZIDO DO QUE ANTERIORMENTE)
        const minLinearSpeed = 1.0;
        const maxLinearSpeed = 2.2;
        const currentSpeed = body.velocity.length();
        if (currentSpeed < minLinearSpeed && currentSpeed > 0.0001) {
          body.velocity.multiplyScalar(minLinearSpeed / currentSpeed);
        } else if (currentSpeed > maxLinearSpeed) {
          body.velocity.multiplyScalar(maxLinearSpeed / currentSpeed);
        }

        const minRotationalSpeed = 0.2;
        const maxRotationalSpeed = 0.8;
        const currentRotationalSpeed = body.angularVelocity.length();
        if (currentRotationalSpeed < minRotationalSpeed && currentRotationalSpeed > 0.0001) {
          body.angularVelocity.multiplyScalar(minRotationalSpeed / currentRotationalSpeed);
        } else if (currentRotationalSpeed > maxRotationalSpeed) {
          body.angularVelocity.multiplyScalar(maxRotationalSpeed / currentRotationalSpeed);
        }

        // Removido o amortecimento inercial (0.999) para que os cards nunca parem de se mover
        // body.velocity.multiplyScalar(0.999);
        // body.angularVelocity.multiplyScalar(0.999);

        if (body.position.z > maxZ) {
          maxZ = body.position.z;
          closestCard = body;
        }



        // 4. LÓGICA INDEPENDENTE DE TROCA DE TEXTURA TRANSPARENTE
        const angleY = ((body.group.rotation.y % (Math.PI * 2)) + Math.PI * 2) % (Math.PI * 2);
        const frontHidden = angleY > Math.PI / 2 && angleY < Math.PI * 1.5;
        const backHidden = !frontHidden;

        // Troca Frente (+Z)
        if (frontHidden && !body.wasSwappingFront) {
          body.wasSwappingFront = true;
          const currentBackUrl = body.backMesh.material.map?.image?.src || '';
          const newPlayer = getRandomPlayerCard(currentBackUrl);
          
          body.frontName = newPlayer.name;
          
          textureLoader.load(newPlayer.url, (loadedTex) => {
            loadedTex.colorSpace = THREE.SRGBColorSpace;
            const oldTex = body.frontMesh.material.map;
            body.frontMesh.material.map = loadedTex;
            body.frontMesh.material.needsUpdate = true;
            oldTex?.dispose();
          });
        } else if (!frontHidden) {
          body.wasSwappingFront = false;
        }

        // Troca Costas (-Z)
        if (backHidden && !body.wasSwappingBack) {
          body.wasSwappingBack = true;
          const currentFrontUrl = body.frontMesh.material.map?.image?.src || '';
          const newPlayer = getRandomPlayerCard(currentFrontUrl);
          
          body.backName = newPlayer.name;
          
          textureLoader.load(newPlayer.url, (loadedTex) => {
            loadedTex.colorSpace = THREE.SRGBColorSpace;
            const oldTex = body.backMesh.material.map;
            body.backMesh.material.map = loadedTex;
            body.backMesh.material.needsUpdate = true;
            oldTex?.dispose();
          });
        } else if (!backHidden) {
          body.wasSwappingBack = false;
        }
      });

      // 5. ATUALIZAR MOLDURA EDITORIAL DE DESTAQUE COM A CARTA MAIS PRÓXIMA
      // Removido a pedido do usuário (sem textos laterais inferiores)

      renderer.render(scene, camera);
    };

    animate();

    // --- RESIZE OBSERVER (RESPONSIVIDADE FIXED) ---
    const resizeHandler = () => {
      W = window.innerWidth;
      H = window.innerHeight;
      camera.aspect = W / H;
      camera.updateProjectionMatrix();
      renderer.setSize(W, H);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    };

    window.addEventListener('resize', resizeHandler);

    // --- CLEANUP COMPLETO (CONTRA MEMORY LEAKS) ---
    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('resize', resizeHandler);

      // Descarte de cartas
      cardsData.forEach(body => {
        body.frontMesh.geometry.dispose();
        body.frontMesh.material.map?.dispose();
        body.frontMesh.material.dispose();

        body.backMesh.geometry.dispose();
        body.backMesh.material.map?.dispose();
        body.backMesh.material.dispose();
      });



      renderer.dispose();
      renderer.forceContextLoss(); // WebGL GC
    };
  }, [loading, API_BASE]);

  if (loading) {
    return (
      <div className="three-card-loading-overlay">
        <div className="three-card-loader"></div>
        <span className="loading-text">Inicializando Vácuo Físico Independente 3D...</span>
      </div>
    );
  }

  return (
    <div className="three-card-background-canvas-wrapper" ref={containerRef}>
      {/* Molduras editoriais flutuantes de background */}
      <div className="three-card-bg-editorial-header">
        <span className="bg-editorial-tag">// DUAL-ORBITAL BINDING ENVIRONMENT [2 CARDS ACTIVE]</span>
      </div>

      <canvas ref={canvasRef} className="three-card-canvas" />

    </div>
  );
}
