"""
main_shorts.py — The Silent Sage YouTube Shorts Agent v2.1
Usa banco de temas (themes_bank.json) para garantir histórias únicas e historicamente ricas.
O GPT-4o foca-se apenas na forma (escrita) — não no conteúdo (factos).
"""

import os
import sys
import json
import logging
import shutil
import tempfile
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f"logs/shorts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log", encoding="utf-8")
    ]
)
logger = logging.getLogger(__name__)

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).parent
THEMES_FILE = BASE_DIR / "assets" / "themes_bank.json"
INDEX_FILE  = BASE_DIR / "assets" / "theme_index.json"


# ─────────────────────────────────────────────────────────────────────────────
# BANCO DE TEMAS
# ─────────────────────────────────────────────────────────────────────────────

def _load_themes() -> list:
    if not THEMES_FILE.exists():
        logger.error(f"  ✗ Banco de temas não encontrado: {THEMES_FILE}")
        logger.error("  → Copia themes_bank.json para assets/themes_bank.json")
        sys.exit(1)
    with open(THEMES_FILE, "r", encoding="utf-8") as f:
        themes = json.load(f)
    logger.info(f"  ✓ Banco de temas: {len(themes)} temas disponíveis")
    return themes


def _get_current_index() -> int:
    if INDEX_FILE.exists():
        with open(INDEX_FILE, "r") as f:
            return json.load(f).get("current_index", 0)
    return 0


def _advance_index(themes: list) -> int:
    current = _get_current_index()
    next_index = (current + 1) % len(themes)
    INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(INDEX_FILE, "w") as f:
        json.dump({"current_index": next_index, "last_updated": datetime.now().isoformat()}, f)
    return current


def _get_next_theme(themes: list) -> dict:
    index = _advance_index(themes)
    theme = themes[index]
    logger.info(f"  🎯 Tema #{theme['id']}: '{theme['tema']}' ({theme['filosofo']})")
    return theme


# ─────────────────────────────────────────────────────────────────────────────
# GERAÇÃO DO SCRIPT (GPT-4o com tema injectado)
# ─────────────────────────────────────────────────────────────────────────────

def generate_short_script(theme: dict) -> dict:
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    logger.info("  Fase 1: A gerar script com GPT-4o (tema injectado)...")

    system_prompt = """You are the lead scriptwriter for "@TheSilentSage" — a Dark Stoicism YouTube channel.
Voice: solemn, cinematic, authoritative. Deep AI voice (ElevenLabs).
NEVER coach-speak or generic motivation.

VOCABULARY (use): Unshakable, Internal Citadel, Ephemeral, Discipline, Chaos, Fate,
Virtue, Mortality, Dust, Slave, Sovereign, Retreat, Stone, Silence

BANNED: wisdom, embrace, journey, life lessons, in today's world, fast-paced,
welcome back, ancient wisdom, motivational, positive, say out loud, write it down,
repeat after me, coach, mindset hack, thanks for watching

SCRIPT RULES:
1. HOOK (0-5s): Shocking direct statement. NEVER a question. Use "You".
2. RHYTHM: Alternate short punchy + longer rhythmic sentences.
3. LOOP: Final sentence leads naturally back to hook.
4. CTA: Always end with exactly "Follow for more Stoic wisdom." — no emojis.
5. USE THE EXACT HISTORICAL FACTS provided. DO NOT invent or add new facts.
6. The philosopher's name must appear in the TEACHING section.

VISUAL CATEGORIES (Greco-Roman ONLY — NEVER Zen/Asian):
- Chaos/Subjection: storm clouds, ocean waves calm, dark forest mystical
- Authority/History: ancient rome ruins, greek temple, marble statues
- Inner Strength: misty mountains, mountain fog cinematic, stone cliffs
- Ephemerality/Silence: candle flame dark, fire flames dark, starry night sky

STRICT LENGTH RULE:
- Total narration: EXACTLY 60-70 words. Not 80. Not 100. 60-70.
- This equals exactly 30 seconds at natural speaking pace.
- Count your words before returning. If over 70 — cut. No exceptions.

BLOCK STRUCTURE (internal guide, not in output):
[HOOK]     → 8-10 words. Brutal statement.
[TEACHING] → 25-30 words. Exact historical facts. Philosopher named here.
[PRACTICE] → 15-18 words. One internal shift.
[OUTRO]    → 8-10 words. Ends with "Follow for more Stoic wisdom."

Return ONLY valid JSON, no markdown, no preamble."""

    user_prompt = f"""Write a 30-second Stoicism Short using EXACTLY this historical theme:

PHILOSOPHER: {theme['filosofo']}
HISTORICAL MOMENT (use these exact facts): {theme['momento_historico']}
MODERN PROBLEM this addresses: {theme['problema_moderno']}
PRIMARY EMOTION to trigger: {theme['emocao']}

Return this exact JSON:
{{
  "titulo_short": "Hook-based title under 55 chars ending with #Shorts",
  "texto_gancho": "Exact first sentence (max 12 words, statement not question, uses You)",
  "texto_narrado": "Full narration EXACTLY 60-70 words with ... for dramatic pauses",
  "cenas_visuais": [
    {{"parte": "hook", "texto": "hook narration text", "visual": "ocean waves calm"}},
    {{"parte": "teaching", "texto": "philosopher section text", "visual": "ancient rome ruins"}},
    {{"parte": "practice", "texto": "practice section text", "visual": "misty mountains"}},
    {{"parte": "outro", "texto": "final sentence", "visual": "candle flame dark"}}
  ],
  "palavra_chave_visual": "ancient rome ruins",
  "hashtags": ["#Shorts", "#Stoicism", "#{theme['filosofo'].replace(' ', '')}", "#Mindset", "#SelfImprovement"]
}}"""

    response = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.7,
        max_tokens=1500,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )

    script = json.loads(response.choices[0].message.content)
    script["tema_id"]   = theme["id"]
    script["tema_nome"] = theme["tema"]
    script["filosofo"]  = theme["filosofo"]

    logger.info(f"  ✓ Script: '{script.get('titulo_short', '')}'")
    logger.info(f"  ✓ Narração: {len(script.get('texto_narrado', '').split())} palavras")
    return script


# ─────────────────────────────────────────────────────────────────────────────
# PIPELINE PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

def run_shorts_agent():
    logger.info("=" * 60)
    logger.info("  🏛  THE SILENT SAGE — Shorts Agent v2.1")
    logger.info("=" * 60)

    Path("logs").mkdir(exist_ok=True)

    # 1. Banco de Temas
    themes = _load_themes()
    theme  = _get_next_theme(themes)

    # 2. Script
    script_data = generate_short_script(theme)

    # 3. Voz
    logger.info("  Fase 2: A gerar narração (ElevenLabs)...")
    from modules.voice_generator import generate_narration

    temp_dir = Path(tempfile.mkdtemp(prefix="silent_sage_short_"))

    try:
        cenas_voz = [{"texto_narrado": script_data["texto_narrado"]}]
        audio_path = generate_narration(
            cenas=cenas_voz,
            output_dir=str(temp_dir),
            voice_id=os.getenv("ELEVENLABS_VOICE_ID")
        )
        # generate_narration guarda como narração.mp3
        narration_file = Path(temp_dir) / "narração.mp3"
        audio_path = str(narration_file)
        logger.info(f"  ✓ Áudio: {audio_path}")

        # 4. Vídeos Pexels
        logger.info("  Fase 3: A descarregar vídeos Pexels...")
        from modules.shorts_generator import download_multi_scene_videos, download_vertical_video

        cenas_visuais   = script_data.get("cenas_visuais", [])
        fallback_keyword = script_data.get("palavra_chave_visual", "ancient rome ruins")

        scene_video_paths = download_multi_scene_videos(
            cenas_visuais=cenas_visuais,
            fallback_keyword=fallback_keyword,
            output_dir=str(temp_dir)
        )

        if not scene_video_paths or not any(scene_video_paths):
            logger.warning("  ⚠ Multi-cena falhou — a usar vídeo único")
            video_bg_path = download_vertical_video(
                keyword=fallback_keyword,
                output_dir=str(temp_dir)
            )
        else:
            video_bg_path = scene_video_paths[0]

        # 5. Editar Short
        logger.info("  Fase 4: A editar Short (9:16)...")
        from modules.shorts_generator import edit_short_video

        short_path = edit_short_video(
            audio_path=audio_path,
            video_bg_path=video_bg_path,
            short_data=script_data,
            output_dir=str(temp_dir),
            scene_video_paths=scene_video_paths
        )
        logger.info(f"  ✓ Short: {short_path}")

        # 6. Thumbnail placeholder (PIL — sem DALL-E)
        from PIL import Image, ImageDraw
        import textwrap as _tw
        thumb_path = temp_dir / "thumb_placeholder.jpg"
        img = Image.new("RGB", (1280, 720), color=(10, 15, 25))
        draw = ImageDraw.Draw(img)
        draw.rectangle([10,10,1270,710], outline=(200,168,75), width=3)
        title_text = script_data.get("titulo_short", "The Silent Sage")
        wrapped = _tw.fill(title_text.upper(), width=28)
        draw.text((640, 340), wrapped, fill=(200,168,75), anchor="mm", align="center")
        draw.text((640, 660), "THE SILENT SAGE", fill=(180,140,60), anchor="mm")
        img.save(str(thumb_path), "JPEG", quality=90)
        logger.info("  ✓ Thumbnail placeholder criada")

        # 6. Upload
        logger.info("  Fase 5: A fazer upload para YouTube...")
        from modules.youtube_uploader import _get_authenticated_service
        from modules.shorts_generator import upload_short

        client_secrets = os.getenv("YOUTUBE_CLIENT_SECRETS_FILE", "client_secrets.json")
        youtube_service = _get_authenticated_service(client_secrets)

        short_url = upload_short(
            youtube=youtube_service,
            short_data=script_data,
            video_path=short_path,
            thumbnail_path=str(thumb_path)
        )

        if short_url:
            logger.info(f"  ✅ Publicado: {short_url}")
            logger.info(f"  🎯 Tema #{theme['id']} — {theme['tema']} ({theme['filosofo']})")

            run_log = {
                "timestamp": datetime.now().isoformat(),
                "tema_id":   theme["id"],
                "tema":      theme["tema"],
                "filosofo":  theme["filosofo"],
                "titulo":    script_data.get("titulo_short"),
                "url":       short_url,
                "palavras":  len(script_data.get("texto_narrado", "").split())
            }
            log_path = Path("logs") / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(log_path, "w", encoding="utf-8") as f:
                json.dump(run_log, f, ensure_ascii=False, indent=2)
            logger.info(f"  📄 Log: {log_path}")
        else:
            logger.error("  ✗ Upload falhou")

    except Exception as e:
        logger.error(f"  ✗ Erro: {e}", exc_info=True)
        raise

    finally:
        if temp_dir.exists():
            import time
            time.sleep(2)
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass

    logger.info("  🧹 Temporários removidos")
    logger.info("=" * 60)
    logger.info("  🏛  Concluído.")
    logger.info("=" * 60)


if __name__ == "__main__":
    run_shorts_agent()