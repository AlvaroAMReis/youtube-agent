"""
YOUTUBE AUTONOMOUS AGENT v2.0 — MODO SHORTS
=============================================
Cria e publica automaticamente apenas 1 Short.
Usa os módulos existentes mas salta as Fases 1-5.

Custo por execução: ~$0.25
  → GPT-4o (seleção de tema): ~$0.05
  → ElevenLabs (narração curta): ~$0.20
  → Pexels: Grátis
  → DALL-E 3: NÃO usado (sem thumbnail)
"""

import os
import sys
import json
import shutil
import logging
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

from openai import OpenAI
from modules.youtube_uploader import _get_authenticated_service
from modules.shorts_generator import generate_and_upload_short


# ─────────────────────────────────────────────
# CONFIGURAÇÃO DE LOGGING
# ─────────────────────────────────────────────

def setup_logging() -> None:
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"shorts_{timestamp}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding="utf-8")
        ]
    )

    for noisy_lib in ["httpx", "httpcore", "moviepy", "googleapiclient", "urllib3"]:
        logging.getLogger(noisy_lib).setLevel(logging.WARNING)

    logging.info(f"📋 Logs em: {log_file}")


# ─────────────────────────────────────────────
# GERAR GUIÃO MÍNIMO PARA O SHORT
# ─────────────────────────────────────────────

def generate_short_script(niche: str) -> dict:
    """
    Gera um guião mínimo com 1 cena para o Short.
    Muito mais barato que o guião completo do main.py.
    """
    logger = logging.getLogger(__name__)
    logger.info(f"  A gerar tema para Short sobre '{niche}'...")

    client = OpenAI()

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "You are an expert in Stoic philosophy YouTube content. Always respond in valid JSON only."
            },
            {
                "role": "user",
                "content": f"""Create a single powerful Stoic lesson for a YouTube Short about '{niche}'.

Return ONLY this JSON:
{{
  "titulo": "Compelling video title in English",
  "nicho": "{niche}",
  "cenas": [
    {{
      "texto_narrado": "Full narration text for the Short (80-100 words, entirely in English)",
      "palavra_chave_visual": "english keyword for Pexels background video"
    }}
  ]
}}"""
            }
        ],
        temperature=0.8,
        max_tokens=600,
        response_format={"type": "json_object"}
    )

    script_data = json.loads(response.choices[0].message.content)
    logger.info(f"  ✓ Tema gerado: '{script_data['titulo']}'")
    return script_data


# ─────────────────────────────────────────────
# GERAR THUMBNAIL SIMPLES (SEM DALL-E)
# ─────────────────────────────────────────────

def create_simple_thumbnail(temp_dir: str, title: str) -> str:
    """
    Cria uma thumbnail simples com texto usando PIL.
    Evita gastar créditos do DALL-E 3.
    """
    logger = logging.getLogger(__name__)

    try:
        from PIL import Image, ImageDraw, ImageFont
        import textwrap

        # Fundo escuro
        img = Image.new("RGB", (1280, 720), color=(10, 15, 25))
        draw = ImageDraw.Draw(img)

        # Gradiente simulado com retângulos
        for i in range(720):
            alpha = i / 720
            r = int(10 + 20 * alpha)
            g = int(15 + 10 * alpha)
            b = int(25 + 30 * alpha)
            draw.line([(0, i), (1280, i)], fill=(r, g, b))

        # Borda dourada
        draw.rectangle([10, 10, 1270, 710], outline=(200, 168, 75), width=4)
        draw.rectangle([20, 20, 1260, 700], outline=(200, 168, 75, 80), width=1)

        # Texto do título
        wrapped = textwrap.fill(title.upper(), width=25)
        try:
            font = ImageFont.truetype("arial.ttf", 72)
            font_small = ImageFont.truetype("arial.ttf", 36)
        except Exception:
            font = ImageFont.load_default()
            font_small = font

        # Sombra
        draw.text((645, 365), wrapped, font=font, fill=(0, 0, 0), anchor="mm", align="center")
        # Texto principal dourado
        draw.text((640, 360), wrapped, font=font, fill=(200, 168, 75), anchor="mm", align="center")

        # "THE SILENT SAGE" em baixo
        draw.text((640, 650), "THE SILENT SAGE", font=font_small, fill=(180, 140, 60), anchor="mm")

        thumbnail_path = str(Path(temp_dir) / "thumbnail_short.jpg")
        img.save(thumbnail_path, "JPEG", quality=90)
        logger.info(f"  ✓ Thumbnail criada: {thumbnail_path}")
        return thumbnail_path

    except Exception as e:
        logger.warning(f"  ⚠ Erro ao criar thumbnail: {e}")
        # Fallback: thumbnail preta simples
        img = Image.new("RGB", (1280, 720), color=(10, 15, 25))
        thumbnail_path = str(Path(temp_dir) / "thumbnail_short.jpg")
        img.save(thumbnail_path, "JPEG")
        return thumbnail_path


# ─────────────────────────────────────────────
# FUNÇÃO PRINCIPAL
# ─────────────────────────────────────────────

def main():
    print("""
╔══════════════════════════════════════════════════════════╗
║       YOUTUBE AUTONOMOUS AGENT  v2.0                     ║
║       Modo: SHORTS ONLY  ⚡                              ║
╚══════════════════════════════════════════════════════════╝
    """)

    setup_logging()
    logger = logging.getLogger(__name__)

    start_time = datetime.now()
    logger.info(f"🚀 Agente Shorts iniciado: {start_time.strftime('%d/%m/%Y %H:%M:%S')}")

    # Carregar configuração
    load_dotenv()
    config = {
        "niche": os.getenv("CHANNEL_NICHE", "Stoicism"),
        "voice_id": os.getenv("ELEVENLABS_VOICE_ID"),
        "client_secrets": os.getenv("YOUTUBE_CLIENT_SECRETS_FILE", "client_secrets.json"),
    }
    logger.info(f"✓ Config carregada | Nicho: '{config['niche']}'")

    # Pasta temp
    temp_dir = Path("temp_shorts")
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(exist_ok=True)

    try:
        # 1. Gerar guião mínimo
        logger.info("\n" + "═" * 60)
        logger.info("  FASE 1 — GERAR TEMA DO SHORT")
        logger.info("═" * 60)
        script_data = generate_short_script(config["niche"])

        # 2. Criar thumbnail simples (sem DALL-E)
        thumbnail_path = create_simple_thumbnail(str(temp_dir), script_data["titulo"])

        # 3. Autenticar YouTube
        logger.info("\n" + "═" * 60)
        logger.info("  FASE 2 — AUTENTICAÇÃO YOUTUBE")
        logger.info("═" * 60)
        youtube_service = _get_authenticated_service(config["client_secrets"])
        logger.info("  ✓ Autenticação bem-sucedida")

        # 4. Gerar e publicar Short
        logger.info("\n" + "═" * 60)
        logger.info("  FASE 3 — GERAR E PUBLICAR SHORT")
        logger.info("═" * 60)
        short_url = generate_and_upload_short(
            script_data=script_data,
            thumbnail_path=thumbnail_path,
            voice_id=config["voice_id"],
            youtube_service=youtube_service,
            temp_dir=str(temp_dir)
        )

        # Relatório final
        elapsed = datetime.now() - start_time
        mins = int(elapsed.total_seconds() // 60)
        secs = int(elapsed.total_seconds() % 60)

        logger.info("\n" + "═" * 60)
        logger.info("🎉  SHORT PUBLICADO COM SUCESSO!")
        logger.info("═" * 60)
        logger.info(f"  ⚡  Short: {short_url}")
        logger.info(f"  ⏱  Tempo: {mins}m {secs}s")
        logger.info("═" * 60)

        # Relatório JSON
        report_path = Path("logs") / f"report_short_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump({
                "data": datetime.now().isoformat(),
                "tipo": "shorts_only",
                "titulo": script_data["titulo"],
                "short_url": short_url,
                "duracao_segundos": elapsed.total_seconds()
            }, f, ensure_ascii=False, indent=2)
        logger.info(f"📊  Relatório guardado: {report_path}")

    except Exception as e:
        logger.critical(f"💥 FALHA FATAL: {e}")
        sys.exit(1)

    finally:
        # Limpeza
        try:
            shutil.rmtree(temp_dir)
            logger.info("🧹 Pasta /temp_shorts removida")
        except Exception as e:
            logger.warning(f"⚠ Limpeza falhou: {e}")


if __name__ == "__main__":
    main()