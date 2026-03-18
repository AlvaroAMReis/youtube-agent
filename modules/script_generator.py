"""
MÓDULO 1: GERADOR DE GUIÃO v2.1 — The Silent Sage
===================================================
Usa banco de temas (themes_bank_videos.json) para garantir
histórias únicas e historicamente ricas.
O GPT-4o foca-se apenas na forma (escrita) — não no conteúdo (factos).

Melhorias v2.1:
  - Banco de temas com 15 temas filosóficos profundos
  - Pausas dramáticas [...] e [pausa] para ritmo cinematográfico
  - Contraste narrativo Seneca (rico) vs Epictetus (escravo)
  - Ponte directa para o caos moderno (dopamina/redes sociais)
  - Idioma: sempre inglês
"""

import os
import json
import logging
from pathlib import Path
from openai import OpenAI

logger = logging.getLogger(__name__)

BASE_DIR         = Path(__file__).parent.parent
THEMES_FILE      = BASE_DIR / "assets" / "themes_bank_videos.json"
INDEX_FILE       = BASE_DIR / "assets" / "theme_index_videos.json"


# ─────────────────────────────────────────────────────────────────────────────
# BANCO DE TEMAS
# ─────────────────────────────────────────────────────────────────────────────

def _load_themes() -> list:
    if not THEMES_FILE.exists():
        logger.error(f"  ✗ Banco de temas não encontrado: {THEMES_FILE}")
        raise FileNotFoundError(f"Copia themes_bank_videos.json para assets/themes_bank_videos.json")
    with open(THEMES_FILE, "r", encoding="utf-8") as f:
        themes = json.load(f)
    logger.info(f"  ✓ Banco de temas (vídeos): {len(themes)} temas disponíveis")
    return themes


def _get_current_index() -> int:
    if INDEX_FILE.exists():
        with open(INDEX_FILE, "r") as f:
            return json.load(f).get("current_index", 0)
    return 0


def _advance_index(themes: list) -> int:
    from datetime import datetime
    current = _get_current_index()
    next_index = (current + 1) % len(themes)
    INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(INDEX_FILE, "w") as f:
        json.dump({"current_index": next_index, "last_updated": datetime.now().isoformat()}, f)
    return current


def _get_next_theme(themes: list) -> dict:
    index = _advance_index(themes)
    theme = themes[index]
    logger.info(f"  🎯 Tema #{theme['id']}: '{theme['tema']}' ({', '.join(theme['filosofos'])})")
    return theme


# ─────────────────────────────────────────────────────────────────────────────
# GERAÇÃO DO GUIÃO
# ─────────────────────────────────────────────────────────────────────────────

def generate_script(niche: str, language: str = "en") -> dict:
    """
    Gera um guião completo com tema histórico injectado.

    Args:
        niche:    Nicho do canal (ignorado — substituído pelo banco de temas)
        language: Idioma (forçado para "en" — The Silent Sage é em inglês)

    Returns:
        dict: JSON com titulo, descricao, tags, prompt_thumbnail e cenas[]
    """
    logger.info("Fase 1: A gerar guião (tema injectado do banco)...")

    themes = _load_themes()
    theme  = _get_next_theme(themes)

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # Construir arco narrativo do tema como contexto para o GPT-4o
    arco_formatado = ""
    for parte in theme["arco_narrativo"]:
        arco_formatado += f"\n[{parte['parte'].upper()}] {parte['titulo']}\n"
        arco_formatado += f"Core idea: {parte['conteudo']}\n"
        arco_formatado += f"Visual keyword: {parte['palavra_chave_visual']}\n"

    system_prompt = """You are the lead writer for "@TheSilentSage" — a Dark Stoicism YouTube channel.
You write long-form scripts (7-9 minutes) that feel like documentary narration: cinematic, profound, authoritative.

VOICE: Deep, slow, deliberate. Like a stone tablet being read aloud.
NEVER: coach-speak, motivational clichés, "life lessons", "welcome back", "in today's world", "journey"
ALWAYS: solemn weight, historical precision, existential confrontation

VOCABULARY (use freely): Citadel, Sovereign, Ephemeral, Discipline, Chaos, Fate, Virtue,
Mortality, Dust, Slave, Stone, Silence, Forge, Ruin, Unshakable, Retreat

DRAMATIC PAUSES — use these markers in the narration text:
  "..." → brief pause (0.5s) — use for emphasis between short sentences
  "[pausa]" → long pause (2-3s) — use before major revelations or after powerful statements
  Use at least 1 "[pausa]" per scene. This is what makes 900 words fill 9 minutes.

NARRATIVE CONTRAST RULE:
  When both Seneca and Epictetus appear in the same video:
  Always contrast them explicitly — Seneca (wealthiest man in Rome, chose poverty voluntarily)
  vs Epictetus (born a slave, had poverty forced upon him). Same philosophy. Opposite circumstances.
  This contrast is your most powerful narrative tool. Use it.

MODERN DOPAMINE BRIDGE:
  In at least one scene, draw an explicit connection between the ancient problem and its modern equivalent:
  - "distraction" → social media, infinite scroll, notification addiction
  - "the crowd" → algorithm-driven outrage and tribal thinking
  - "the arena" → TikTok, Instagram Reels, the new Colosseum of cheap dopamine
  Name it directly. The audience will feel seen.

SEO RULES:
  - Title: under 70 characters, no clickbait, historically grounded
  - Description: minimum 300 words, includes keywords, timestamps suggestion, CTA
  - Tags: 10 tags mixing broad (Stoicism) and specific (Marcus Aurelius Meditations)

Return ONLY valid JSON. No markdown. No preamble."""

    # Construir template JSON com todas as cenas explícitas
    cenas_json_parts = []
    for i, parte in enumerate(theme["arco_narrativo"]):
        scene_obj = (
            '{"numero": ' + str(i+1) +
            ', "texto_narrado": "Write the ' + parte["parte"] + ' scene. Core idea: ' + parte["conteudo"][:80] + '. Minimum 150 words. Use [...] and [pausa]."' +
            ', "palavra_chave_visual": "' + parte["palavra_chave_visual"] + '"' +
            ', "citacao_destaque": "The single most powerful sentence from this scene — under 15 words, no quotation marks"}'
        )
        cenas_json_parts.append(scene_obj)
    cenas_json = ",\n    ".join(cenas_json_parts)

    user_prompt = f"""Write a complete 7-9 minute Dark Stoicism video script using EXACTLY this theme:

THEME: {theme['tema']}
PHILOSOPHERS: {', '.join(theme['filosofos'])}
CENTRAL THESIS: {theme['tese_central']}
MODERN PROBLEM: {theme['problema_moderno']}
CENTRAL EMOTION: {theme['emocao_central']}
THUMBNAIL PROMPT: {theme['prompt_thumbnail']}

NARRATIVE ARC TO FOLLOW (use these exact ideas, expand with dramatic prose):
{arco_formatado}

PACING RULES — CRITICAL, DO NOT IGNORE:
- Total narration: MINIMUM 900 words. Target 1000 words. Count before returning.
- Each scene: MINIMUM 150 words. If a scene is under 150 words, expand it before returning.
- Use "[pausa]" at least once per scene — this is mandatory, not optional.
- Alternate rhythm: short punchy sentence (5-8 words). Then longer, weighted sentence that builds and lands with force.
- If your total word count is under 900 words — rewrite and expand every scene before returning the JSON.

Return a JSON object with this structure. You MUST write ALL {len(theme['arco_narrativo'])} scenes — one per narrative arc part above.
Each texto_narrado MUST be minimum 150 words. No exceptions.

{{
  "titulo": "SEO title under 70 chars",
  "descricao": "YouTube description minimum 300 words with keywords, timestamps and CTA",
  "tags": ["Stoicism", "Marcus Aurelius", "{theme['filosofos'][0].replace(' ', '')}", "Philosophy", "Dark Philosophy", "StoicWisdom", "Mindset", "AncientWisdom", "MarcusAurelius", "SelfDiscipline"],
  "prompt_thumbnail": "{theme['prompt_thumbnail']}",
  "tema_id": {theme['id']},
  "tema_nome": "{theme['tema']}",
  "cenas": [
    {cenas_json}
  ]
}}"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt}
            ],
            temperature=0.75,
            max_tokens=6000,
            response_format={"type": "json_object"}
        )

        raw_content = response.choices[0].message.content
        script_data = json.loads(raw_content)

        # Injectar metadados do tema
        script_data["nicho"]      = niche
        script_data["tema_id"]    = theme["id"]
        script_data["tema_nome"]  = theme["tema"]
        script_data["filosofos"]  = theme["filosofos"]

        # Garantir campos obrigatórios
        required_keys = ["titulo", "descricao", "tags", "prompt_thumbnail", "cenas"]
        for key in required_keys:
            if key not in script_data:
                raise ValueError(f"JSON inválido: campo obrigatório '{key}' em falta")

        if not isinstance(script_data["cenas"], list) or len(script_data["cenas"]) == 0:
            raise ValueError("JSON inválido: 'cenas' deve ser uma lista não vazia")

        for i, cena in enumerate(script_data["cenas"]):
            if "texto_narrado" not in cena or "palavra_chave_visual" not in cena:
                raise ValueError(f"Cena {i+1} inválida: campos em falta")

        total_words = sum(len(c["texto_narrado"].split()) for c in script_data["cenas"])
        logger.info(f"  ✓ Guião gerado: '{script_data['titulo']}'")
        logger.info(f"  ✓ Cenas: {len(script_data['cenas'])} | Palavras: {total_words} (~{total_words//130} min)")
        logger.info(f"  ✓ Tema: #{theme['id']} — {theme['tema']}")

        return script_data

    except json.JSONDecodeError as e:
        logger.error(f"  ✗ Resposta da OpenAI não é JSON válido: {e}")
        raise
    except ValueError as e:
        logger.error(f"  ✗ Estrutura JSON inválida: {e}")
        raise
    except Exception as e:
        logger.error(f"  ✗ Erro na API OpenAI: {e}")
        raise
