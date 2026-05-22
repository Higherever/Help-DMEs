import express from 'express';
import cors from 'cors';
import { GlobalFonts, createCanvas, loadImage } from '@napi-rs/canvas';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Registrar fontes locais
GlobalFonts.registerFromPath(path.join(__dirname, 'fonts', 'Teko-SemiBold.ttf'), 'Teko');
GlobalFonts.registerFromPath(path.join(__dirname, 'fonts', 'Oswald-Regular.ttf'), 'Oswald');

const app = express();
app.use(cors());
app.use(express.json({ limit: '10mb' }));

// Paths globais de saída
const IMAGES_DIR = path.join(__dirname, '..', '..', 'images');
const FULL_DIR = path.join(IMAGES_DIR, 'cards', 'full');
const SMALL_DIR = path.join(IMAGES_DIR, 'cards', 'small');

// Garantir que as pastas existam
fs.mkdirSync(FULL_DIR, { recursive: true });
fs.mkdirSync(SMALL_DIR, { recursive: true });

/**
 * Função para desenhar com segurança uma imagem se ela existir no disco
 */
async function tryDrawImage(ctx, imagePath, x, y, w, h) {
  if (!imagePath || !fs.existsSync(imagePath)) {
    return false;
  }
  try {
    const img = await loadImage(imagePath);
    ctx.drawImage(img, x, y, w, h);
    return true;
  } catch (err) {
    console.error(`Erro ao carregar imagem em ${imagePath}:`, err.message);
    return false;
  }
}

/**
 * Endpoint de Geração de Card (POST /generate)
 */
app.post('/generate', async (req, res) => {
  try {
    const p = req.body;
    const playerId = p.id || 'unknown';
    const name = p.name || 'Unknown Player';
    const overall = p.overall || 0;
    const position = p.position || 'ST';
    const textColor = p.text_color || '#ffffff';
    const stats = p.stats || [];
    const playstyles = p.playstyles || [];
    const altPositions = p.alt_positions || [];
    const preferredFoot = p.preferred_foot || '';
    const skillsWeakFoot = p.skills_wf || ''; // Ex: "5-5" ou "4-5"

    // Nome de arquivo higienizado
    const nameSlug = (name || '')
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/[^a-z0-9]/g, '_')
      .replace(/_+/g, '_')
      .trim();
    const filename = `fc_player_${playerId}_${nameSlug}.png`;

    // ────────────────────────────────────────────────────────────────────────
    // 1. SUPERSAMPLING PIPELINE 3x (1512 × 2094 px)
    // ────────────────────────────────────────────────────────────────────────
    const canvas3x = createCanvas(1512, 2094);
    const ctx3x = canvas3x.getContext('2d');

    // Camada 1: Template de Fundo
    let bgSuccess = await tryDrawImage(ctx3x, p.bg_template_path, 0, 0, 1512, 2094);
    if (!bgSuccess) {
      const fallbackPath = path.join(IMAGES_DIR, 'cards', 'templates', 'sbc_global_Normal_bg.png');
      await tryDrawImage(ctx3x, fallbackPath, 0, 0, 1512, 2094);
    }

    // Camada 2: Rosto/Face do Jogador
    // Posicionado no canto superior direito exatamente como no gabarito
    await tryDrawImage(ctx3x, p.face_path, 420, 220, 950, 950);

    // Camada 3: Sombra Inferior para legibilidade do nome e stats
    const gradient = ctx3x.createLinearGradient(0, 1100, 0, 2094);
    gradient.addColorStop(0, 'rgba(0, 0, 0, 0)');
    gradient.addColorStop(0.35, 'rgba(0, 0, 0, 0.2)');
    gradient.addColorStop(0.7, 'rgba(0, 0, 0, 0.6)');
    gradient.addColorStop(1, 'rgba(0, 0, 0, 0.85)');
    ctx3x.fillStyle = gradient;
    ctx3x.fillRect(100, 1150, 1312, 850);

    // Camada 4: Rating / Overall (Canto Superior Esquerdo)
    ctx3x.fillStyle = textColor;
    ctx3x.textAlign = 'center';
    ctx3x.font = '280px Teko';
    ctx3x.fillText(overall.toString(), 280, 420);

    // Camada 5: Posição Principal (Abaixo do Rating)
    ctx3x.font = '95px Oswald';
    ctx3x.fillText(position.toUpperCase(), 280, 540);

    // Camada 6: Playstyles+ (Coluna Vertical do Canto Esquerdo)
    // Alinhados abaixo da posição do jogador no canto esquerdo
    if (playstyles && playstyles.length > 0) {
      let psY = 920;
      const psX = 100;
      const psSize = 90;
      for (const ps of playstyles.slice(0, 4)) {
        if (ps.icon_path && fs.existsSync(ps.icon_path)) {
          await tryDrawImage(ctx3x, ps.icon_path, psX, psY, psSize, psSize);
          psY += 130;
        }
      }
    }

    // Camada 7: Posições Alternativas (Canto Direito Superior)
    // Pequeno retângulo arredondado com borda e texto
    if (altPositions && altPositions.length > 0) {
      let apY = 660;
      const apX = 1280;
      const apW = 140;
      const apH = 70;
      
      ctx3x.textAlign = 'center';
      ctx3x.font = 'bold 45px Oswald';
      
      for (const ap of altPositions.slice(0, 2)) {
        // Desenha caixinha
        ctx3x.fillStyle = 'rgba(0, 0, 0, 0.45)';
        ctx3x.strokeStyle = textColor;
        ctx3x.lineWidth = 3;
        ctx3x.beginPath();
        ctx3x.roundRect(apX - apW/2, apY - apH/2, apW, apH, 12);
        ctx3x.fill();
        ctx3x.stroke();
        
        // Desenha texto
        ctx3x.fillStyle = textColor;
        ctx3x.fillText(ap.toUpperCase(), apX, apY + 16);
        apY += 100;
      }
    }

    // Camada 8: Perna Preferida (R/L) e Fintas/Pé Fraco (5-5) no Canto Direito Inferior
    let detailsY = 1200;
    const detailsX = 1280;
    const detW = 140;
    const detH = 70;

    if (preferredFoot) {
      ctx3x.fillStyle = 'rgba(0, 0, 0, 0.45)';
      ctx3x.strokeStyle = textColor;
      ctx3x.lineWidth = 3;
      ctx3x.beginPath();
      ctx3x.roundRect(detailsX - detW/2, detailsY - detH/2, detW, detH, 12);
      ctx3x.fill();
      ctx3x.stroke();

      ctx3x.fillStyle = textColor;
      ctx3x.font = 'bold 45px Oswald';
      ctx3x.textAlign = 'center';
      ctx3x.fillText(preferredFoot.toUpperCase(), detailsX, detailsY + 16);
      detailsY += 90;
    }

    if (skillsWeakFoot) {
      ctx3x.fillStyle = 'rgba(0, 0, 0, 0.45)';
      ctx3x.strokeStyle = textColor;
      ctx3x.lineWidth = 3;
      ctx3x.beginPath();
      ctx3x.roundRect(detailsX - detW/2, detailsY - detH/2, detW, detH, 12);
      ctx3x.fill();
      ctx3x.stroke();

      ctx3x.fillStyle = textColor;
      ctx3x.font = 'bold 40px Oswald';
      ctx3x.textAlign = 'center';
      ctx3x.fillText(skillsWeakFoot, detailsX, detailsY + 14);
    }

    // Camada 9: Nome do Jogador (Centralizado no meio da carta, acima dos atributos)
    ctx3x.fillStyle = textColor;
    ctx3x.textAlign = 'center';
    ctx3x.font = '160px Teko';
    ctx3x.fillText(name.toUpperCase(), 756, 1380);

    // Camada 10: Linha Divisória de Estatísticas
    ctx3x.strokeStyle = textColor;
    ctx3x.lineWidth = 4;
    ctx3x.beginPath();
    ctx3x.moveTo(220, 1420);
    ctx3x.lineTo(1292, 1420);
    ctx3x.stroke();

    // Camada 11: Os 6 Atributos em Linha Horizontal (Gabarito Oficial)
    // PAC | SHO | PAS | DRI | DEF | PHY
    const colXPositions = [240, 446, 652, 858, 1064, 1270];
    ctx3x.textAlign = 'center';

    for (let i = 0; i < 6; i++) {
      const s = stats[i];
      if (s) {
        const x = colXPositions[i];
        
        // Rótulo superior (ex: PAC)
        ctx3x.font = '68px Teko';
        ctx3x.fillStyle = textColor;
        ctx3x.globalAlpha = 0.8;
        ctx3x.fillText(s.name.toUpperCase(), x, 1580);
        ctx3x.globalAlpha = 1.0;
        
        // Valor inferior (ex: 86)
        ctx3x.font = '115px Oswald';
        ctx3x.fillStyle = textColor;
        ctx3x.fillText((s.value || 0).toString(), x, 1710);
      }
    }

    // Camada 12: Badges na Base (Centralizados na Horizontal)
    // Bandeira do País, Logo da Liga e Logo do Clube lado a lado no rodapé
    const badgesToDraw = [];
    if (p.nation_path && fs.existsSync(p.nation_path)) {
      badgesToDraw.push({ path: p.nation_path, isNation: true });
    }
    if (p.league_path && fs.existsSync(p.league_path)) {
      badgesToDraw.push({ path: p.league_path, isNation: false });
    }
    if (p.club_path && fs.existsSync(p.club_path)) {
      badgesToDraw.push({ path: p.club_path, isNation: false });
    }

    const badgeCenterY = 1775;
    const badgeW = 95;
    const badgeH = 95;
    const nationW = 120; // Bandeira da nação é retangular
    const nationH = 80;

    if (badgesToDraw.length === 3) {
      const xPositions = [520, 711, 902];
      for (let i = 0; i < 3; i++) {
        const b = badgesToDraw[i];
        const x = xPositions[i];
        if (b.isNation) {
          await tryDrawImage(ctx3x, b.path, x, badgeCenterY + 7, nationW, nationH);
        } else {
          await tryDrawImage(ctx3x, b.path, x + 12, badgeCenterY, badgeW, badgeH);
        }
      }
    } else if (badgesToDraw.length === 2) {
      const xPositions = [606, 806];
      for (let i = 0; i < 2; i++) {
        const b = badgesToDraw[i];
        const x = xPositions[i];
        if (b.isNation) {
          await tryDrawImage(ctx3x, b.path, x, badgeCenterY + 7, nationW, nationH);
        } else {
          await tryDrawImage(ctx3x, b.path, x + 12, badgeCenterY, badgeW, badgeH);
        }
      }
    } else if (badgesToDraw.length === 1) {
      const b = badgesToDraw[0];
      const x = 706;
      if (b.isNation) {
        await tryDrawImage(ctx3x, b.path, x, badgeCenterY + 7, nationW, nationH);
      } else {
        await tryDrawImage(ctx3x, b.path, x + 12, badgeCenterY, badgeW, badgeH);
      }
    }

    // ────────────────────────────────────────────────────────────────────────
    // 2. LANCZOS DOWNSCALING PARA 1x (504 × 698 px)
    // ────────────────────────────────────────────────────────────────────────
    const canvas1x = createCanvas(504, 698);
    const ctx1x = canvas1x.getContext('2d');
    // Desenha reduzindo em 3x com antialiasing integrado do napi-canvas
    ctx1x.drawImage(canvas3x, 0, 0, 1512, 2094, 0, 0, 504, 698);

    // Salvar o Card Completo HD em /full/
    const fullPath = path.join(FULL_DIR, filename);
    const fullBuffer = canvas1x.toBuffer('image/png');
    fs.writeFileSync(fullPath, fullBuffer);

    // ────────────────────────────────────────────────────────────────────────
    // 3. CROP & MONTAGEM DO SMALL CARD (150 × 169 px)
    // ────────────────────────────────────────────────────────────────────────
    // Altura combinada: Topo (y: 0 a 422px) + Base (y: 558 a 698px)
    const tempCanvas = createCanvas(504, 562);
    const tempCtx = tempCanvas.getContext('2d');

    // Cola Topo (504 × 422px)
    tempCtx.drawImage(canvas1x, 0, 0, 504, 422, 0, 0, 504, 422);
    // Cola Base (504 × 140px)
    tempCtx.drawImage(canvas1x, 0, 558, 504, 140, 0, 422, 504, 140);

    // Redimensiona proporcionalmente para o Small Card final (150 × 169 px)
    const canvasSmall = createCanvas(150, 169);
    const ctxSmall = canvasSmall.getContext('2d');
    ctxSmall.drawImage(tempCanvas, 0, 0, 504, 562, 0, 0, 150, 169);

    // Salvar a Miniatura em /small/
    const smallPath = path.join(SMALL_DIR, filename);
    const smallBuffer = canvasSmall.toBuffer('image/png');
    fs.writeFileSync(smallPath, smallBuffer);

    console.log(`[FC Card Builder] Card premium gerado: ${filename}`);

    res.json({
      success: true,
      filename,
      full_path: fullPath,
      small_path: smallPath,
      card_template_url: `/images/cards/full/${filename}`,
      card_small_url: `/images/cards/small/${filename}`
    });

  } catch (err) {
    console.error('[FC Card Builder] Erro na geração do card:', err);
    res.status(500).json({ success: false, error: err.message });
  }
});

/**
 * Endpoint de Shutdown Seguro (POST /shutdown)
 * Permite ao Python derrubar o microserviço e liberar toda a memória RAM
 */
app.post('/shutdown', (req, res) => {
  res.json({ success: true, message: 'Derrubando microserviço sob demanda...' });
  console.log('[FC Card Builder] Encerrando microserviço a pedido da aplicação...');
  process.exit(0);
});

// Inicializar Servidor na porta 3001
const PORT = 3001;
app.listen(PORT, () => {
  console.log(`[FC Card Builder] Servidor Express de desenho rodando na porta ${PORT}`);
});
