import sys
import os
import glob
from pathlib import Path

# Adiciona o diretorio backend ao path do python
sys.path.append(str(Path(__file__).resolve().parent.parent))

from services.scraping_utils import create_thumbnail

def main():
    full_dir = Path("images/cards/full")
    small_dir = Path("images/cards/small")
    
    if not full_dir.exists():
        print(f"Diretorio {full_dir} nao existe.")
        return
        
    small_dir.mkdir(parents=True, exist_ok=True)
    
    # Lista todas as imagens na pasta full
    images = glob.glob(str(full_dir / "*.png"))
    
    if not images:
        print("Nenhuma imagem encontrada na pasta full.")
        return
        
    print(f"Encontradas {len(images)} imagens. Gerando miniaturas...")
    
    success_count = 0
    for img_path in images:
        filename = os.path.basename(img_path)
        out_path = str(small_dir / filename)
        
        if create_thumbnail(img_path, out_path, width=150):
            success_count += 1
            
    print(f"Concluido! {success_count} de {len(images)} miniaturas geradas em {small_dir}")

if __name__ == "__main__":
    main()
