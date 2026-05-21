import os
import sys
import asyncio
from pathlib import Path

# Configurar path para importar módulos do backend
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from services.image_processor import download_and_process_card_bg

# Você pode colar URLs diretas aqui
URLS_TO_PROCESS = [
    # "https://cdn.fut.gg/content/fifa26/img/cards/26/gold_rare.avif",
]

# Ou colocar arquivos .avif baixados manualmente nesta pasta
RAW_DIR = BASE_DIR.parent / "images" / "raw_cards"

async def process_local_file(filepath: Path, sbc_id: str):
    """Processa um arquivo local usando ImageMagick"""
    import tempfile
    import shutil
    
    dest_dir = BASE_DIR.parent / "images" / "cards" / "templates"
    dest_dir.mkdir(parents=True, exist_ok=True)
    final_path = dest_dir / f"sbc_{sbc_id}_bg.png"
    
    fd_out, temp_out = tempfile.mkstemp(suffix=".png")
    os.close(fd_out)
    
    cmd = [
        "magick",
        str(filepath),
        "-fuzz", "4%",
        "-fill", "none",
        "-draw", "color 0,0 floodfill",
        "-gravity", "NorthEast", "-draw", "color 0,0 floodfill",
        "-gravity", "SouthWest", "-draw", "color 0,0 floodfill",
        "-gravity", "SouthEast", "-draw", "color 0,0 floodfill",
        temp_out
    ]
    
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    
    if process.returncode == 0:
        shutil.move(temp_out, final_path)
        print(f"✅ Processado arquivo local: {filepath.name} -> {final_path.name}")
    else:
        print(f"❌ Erro processando {filepath.name}: {stderr.decode()}")
        if os.path.exists(temp_out):
            os.remove(temp_out)

async def main():
    print("Iniciando processamento em lote de backgrounds (AVIF -> PNG Transparente)...")
    
    # 1. Processar URLs da lista
    if URLS_TO_PROCESS:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            for url in URLS_TO_PROCESS:
                # Usa o último segmento da URL como ID temporário (ex: gold_rare)
                fake_id = url.split("/")[-1].split(".")[0]
                print(f"Processando URL: {url}")
                path = await download_and_process_card_bg(url, fake_id, session)
                if path:
                    print(f"✅ URL salva em: {path}")
                    
    # 2. Processar arquivos locais baixados manualmente
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    local_files = list(RAW_DIR.glob("*.avif")) + list(RAW_DIR.glob("*.webp")) + list(RAW_DIR.glob("*.png"))
    
    if local_files:
        print(f"\nEncontrados {len(local_files)} arquivos locais em {RAW_DIR}")
        for file in local_files:
            fake_id = file.stem
            await process_local_file(file, fake_id)
            
    print("\nProcessamento concluído! As cartas limpas estão em: images/cards/templates/")

if __name__ == "__main__":
    asyncio.run(main())
