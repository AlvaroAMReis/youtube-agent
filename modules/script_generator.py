"""
MÓDULO 1: GERADOR DE GUIÃO
Usa GPT-4o para gerar um guião estruturado em JSON para um vídeo Dark/Faceless.
"""

import json
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)


def generate_script(niche: str, language: str = "pt") -> dict:
    """
    Gera um guião completo para um vídeo faceless baseado no nicho fornecido.

    Args:
        niche: O nicho do canal (ex: "Estoicismo", "Produtividade")
        language: Idioma do guião ("pt", "en", "es")

    Returns:
        dict: JSON com titulo, descricao, tags, prompt_thumbnail e cenas[]
    
    Raises:
        ValueError: Se a resposta da API não for JSON válido
        Exception: Para erros de comunicação com a API
    """
    logger.info(f"Fase 1: A gerar guião para o nicho '{niche}'...")

    client = OpenAI()

    language_map = {
        "pt": "português europeu",
        "en": "English",
        "es": "español"
    }
    lang_name = language_map.get(language, "português europeu")

    system_prompt = """És um especialista em criação de conteúdo para canais Dark/Faceless no YouTube.
Crias guiões envolventes, filosóficos e inspiradores que prendem o espectador do início ao fim.
Respondes SEMPRE e APENAS em formato JSON válido, sem qualquer texto extra antes ou depois do JSON.
Nunca usas markdown code blocks na tua resposta."""

    user_prompt = f"""Cria um guião completo para um vídeo de YouTube no nicho de '{niche}' em {lang_name}.

O vídeo deve ter entre 5 a 8 minutos de duração (aproximadamente 700-900 palavras de narração no total).
Deve ter um tom sério, profundo e inspirador — estilo canal dark/filosófico.

Devolve EXCLUSIVAMENTE o seguinte JSON (sem markdown, sem texto extra):

{{
  "titulo": "Título SEO otimizado e chamativo (máximo 70 caracteres)",
  "descricao": "Descrição completa para YouTube com keywords, emojis e call-to-action (mínimo 300 palavras)",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6", "tag7", "tag8", "tag9", "tag10"],
  "prompt_thumbnail": "Prompt detalhado em inglês para gerar uma thumbnail impactante com DALL-E 3, estilo dark e cinematográfico",
  "cenas": [
    {{
      "numero": 1,
      "texto_narrado": "Texto exato a ser narrado nesta cena (mínimo 80 palavras por cena)",
      "palavra_chave_visual": "keyword em inglês para pesquisar vídeo de fundo no Pexels (ex: 'dark storm clouds', 'ancient rome')"
    }}
  ]
}}

Cria entre 6 a 8 cenas. Cada cena deve ser uma parte lógica da narrativa.
As palavras_chave_visuais devem ser descritivas e adequadas para encontrar B-roll cinematográfico."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.8,
            max_tokens=3000,
            response_format={"type": "json_object"}
        )

        raw_content = response.choices[0].message.content
        logger.debug(f"Resposta bruta da OpenAI recebida ({len(raw_content)} chars)")

        script_data = json.loads(raw_content)

        # Validação da estrutura obrigatória
        required_keys = ["titulo", "descricao", "tags", "prompt_thumbnail", "cenas"]
        for key in required_keys:
            if key not in script_data:
                raise ValueError(f"JSON inválido: campo obrigatório '{key}' em falta")

        if not isinstance(script_data["cenas"], list) or len(script_data["cenas"]) == 0:
            raise ValueError("JSON inválido: 'cenas' deve ser uma lista não vazia")

        for i, cena in enumerate(script_data["cenas"]):
            if "texto_narrado" not in cena or "palavra_chave_visual" not in cena:
                raise ValueError(f"Cena {i+1} inválida: campos 'texto_narrado' ou 'palavra_chave_visual' em falta")

        logger.info(f"✅ Fase 1 completa: Guião gerado com {len(script_data['cenas'])} cenas | Título: '{script_data['titulo']}'")
        return script_data

    except json.JSONDecodeError as e:
        logger.error(f"❌ Fase 1 FALHOU: Resposta da OpenAI não é JSON válido: {e}")
        raise
    except ValueError as e:
        logger.error(f"❌ Fase 1 FALHOU: Estrutura JSON inválida: {e}")
        raise
    except Exception as e:
        logger.error(f"❌ Fase 1 FALHOU: Erro na API OpenAI: {e}")
        raise