---
name: ui_coolhunter
description: Busca autônoma de inspirações visuais, micro-interactions e animações premium usando browser-use
---

# Workflow: ui_coolhunter

**INSTRUÇÃO PARA A INTELIGÊNCIA ARTIFICIAL (VOCÊ):**
Este workflow é projetado para ser executado **EXCLUSIVAMENTE POR VOCÊ (O Agente de IA)** sob demanda do usuário. 
O usuário NUNCA deve rodar este comando manualmente no terminal.

Quando o usuário acionar este workflow ou solicitar a busca de uma inspiração de design/animação:
1. Receba o termo de busca do usuário (ou pergunte o que ele deseja buscar, caso não tenha especificado).
2. Utilize a ferramenta `run_command` para invocar o script local no terminal:
   ```bash
   ./scripts/ui_coolhunter.py "TERMO DE BUSCA"
   ```
3. Aguarde a finalização do processo assíncrono do browser-use no background (você será notificado do output do comando).
4. Assim que finalizado, avise ao usuário que a nota foi salva no Obsidian com sucesso e apresente um breve resumo do que encontrou, com os links relevantes, ou convide-o a visualizar a nova Nota de Inteligência gerada no Obsidian.

Certifique-se de que o sistema possui as variáveis de ambiente necessárias (como `GEMINI_API_KEY`). Se o script falhar por ausência de chaves, alerte o usuário.
