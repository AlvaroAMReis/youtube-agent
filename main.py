"""
YOUTUBE AUTONOMOUS AGENT v2.1 — The Silent Sage
=================================================
Cria e publica automaticamente 1 Vídeo Longo (monetização AdSense).

Fluxo:
  1. Gerar guião (GPT-4o + banco de temas)
  2. Gerar narração (ElevenLabs)
  3. Descarregar media (Pexels + DALL-E 3)
  4. Editar vídeo longo (MoviePy/FFmpeg)
  5. Publicar vídeo longo (YouTube Data API v3)

Shorts: pipeline independente → main_shorts.py
"""

import os
import sys
import json
import shutil
import logging
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

from modules.script_generator import generate_script
from modules.voice_generator import generate_narration
from modules.media_generator import generate_all_media
from modules.video_editor import create_final_video
from modules.youtube_uploader import upload_to_youtube, _get_authenticated_service


# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────

def setup_logging() -> None:
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"agent_{timestamp}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding="utf-8")
        ]
    )
    for noisy in ["httpx", "httpcore", "moviepy", "googleapiclient", "urllib3"]:
        logging.getLogger(noisy).setLevel(logging.WARNING)
    logging.info(f"📋 Log: {log_file}")


# ─────────────────────────────────────────────
# AUXILIARES
# ─────────────────────────────────────────────

def load_environment() -> dict:
    load_dotenv()
    required = {
        "OPENAI_API_KEY":      "Chave API da OpenAI",
        "ELEVENLABS_API_KEY":  "Chave API do ElevenLabs",
        "ELEVENLABS_VOICE_ID": "ID da voz ElevenLabs",
        "PEXELS_API_KEY":      "Chave API do Pexels",
    }
    missing = [f"  - {k} ({v})" for k, v in required.items() if not os.getenv(k)]
    if missing:
        raise EnvironmentError("Variáveis em falta:\n" + "\n".join(missing))
    config = {
        "niche":          os.getenv("CHANNEL_NICHE", "Stoicism"),
        "language":       "en",
        "voice_id":       os.getenv("ELEVENLABS_VOICE_ID"),
        "client_secrets": os.getenv("YOUTUBE_CLIENT_SECRETS_FILE", "client_secrets.json"),
    }
    logging.info(f"✓ Config carregada | Nicho: '{config['niche']}'")
    return config


def setup_temp_dir() -> str:
    temp_dir = Path("temp")
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(exist_ok=True)
    logging.info("📁 Pasta /temp criada")
    return str(temp_dir)


def save_script(script_data: dict, temp_dir: str) -> None:
    path = Path(temp_dir) / "guião.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(script_data, f, ensure_ascii=False, indent=2)
    logging.info(f"  Guião guardado: {path}")


def cleanup_temp(temp_dir: str) -> None:
    import time
    time.sleep(2)
    try:
        shutil.rmtree(temp_dir)
        logging.info("🧹 Temporários removidos")
    except Exception as e:
        logging.warning(f"⚠ Limpeza falhou: {e}")


def print_banner() -> None:
    print("""
╔══════════════════════════════════════════════════════════╗
║   🏛  THE SILENT SAGE — Video Agent v2.1                 ║
║       Vídeo Longo Autónomo                               ║
╚══════════════════════════════════════════════════════════╝
    """)


def section(title: str) -> None:
    logging.info("\n" + "═" * 60)
    logging.info(f"  {title}")
    logging.info("═" * 60)


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    print_banner()
    setup_logging()
    logger = logging.getLogger(__name__)

    start_time = datetime.now()
    logger.info(f"🚀 Agente iniciado: {start_time.strftime('%d/%m/%Y %H:%M:%S')}")

    try:
        config = load_environment()
    except EnvironmentError as e:
        logger.critical(f"ERRO DE CONFIGURAÇÃO:\n{e}")
        sys.exit(1)

    temp_dir = setup_temp_dir()
    results = {}

    # ── FASE 1: GUIÃO ─────────────────────────────────────────
    section("FASE 1 — GUIÃO (GPT-4o + Banco de Temas)")
    try:
        script_data = generate_script(config["niche"], config["language"])
        save_script(script_data, temp_dir)
        results["script"] = script_data
    except Exception as e:
        logger.critical(f"💥 FALHA FATAL Fase 1: {e}")
        cleanup_temp(temp_dir)
        sys.exit(1)

    # ── FASE 2: VOZ ───────────────────────────────────────────
    section("FASE 2 — VOZ (ElevenLabs)")
    try:
        audio_path = generate_narration(
            script_data["cenas"], temp_dir, config["voice_id"]
        )
        results["audio"] = audio_path
    except Exception as e:
        logger.critical(f"💥 FALHA FATAL Fase 2: {e}")
        cleanup_temp(temp_dir)
        sys.exit(1)

    # ── FASE 3: MEDIA ─────────────────────────────────────────
    section("FASE 3 — MEDIA (Pexels + DALL-E 3)")
    try:
        media = generate_all_media(script_data, temp_dir)
        results["videos"]    = media["videos"]
        results["thumbnail"] = media["thumbnail"]
    except Exception as e:
        logger.critical(f"💥 FALHA FATAL Fase 3: {e}")
        cleanup_temp(temp_dir)
        sys.exit(1)

    # ── FASE 4: EDIÇÃO ────────────────────────────────────────
    section("FASE 4 — EDIÇÃO (MoviePy/FFmpeg)")
    try:
        final_video_path = create_final_video(
            audio_path=results["audio"],
            video_paths=results["videos"],
            output_dir=temp_dir,
            script_data=script_data
        )
        results["final_video"] = final_video_path
    except Exception as e:
        logger.critical(f"💥 FALHA FATAL Fase 4: {e}")
        cleanup_temp(temp_dir)
        sys.exit(1)

    # ── FASE 5: UPLOAD ────────────────────────────────────────
    section("FASE 5 — UPLOAD YOUTUBE")
    try:
        video_url = upload_to_youtube(
            video_path=results["final_video"],
            thumbnail_path=results["thumbnail"],
            script_data=script_data,
            client_secrets_file=config["client_secrets"]
        )
        results["video_url"] = video_url
    except Exception as e:
        logger.critical(f"💥 FALHA FATAL Fase 5: {e}")
        logger.warning("📁 Ficheiros mantidos em /temp para upload manual")
        sys.exit(1)

    # ── RELATÓRIO FINAL ───────────────────────────────────────
    elapsed = datetime.now() - start_time
    mins = int(elapsed.total_seconds() // 60)
    secs = int(elapsed.total_seconds() % 60)

    logger.info("\n" + "═" * 60)
    logger.info("🎉  CONCLUÍDO COM SUCESSO!")
    logger.info("═" * 60)
    logger.info(f"  📹  Título:      {script_data['titulo']}")
    logger.info(f"  🔗  URL:         {results.get('video_url', 'N/A')}")
    logger.info(f"  🎯  Tema:        #{script_data.get('tema_id', '?')} — {script_data.get('tema_nome', '?')}")
    logger.info(f"  ⏱   Tempo total: {mins}m {secs}s")
    logger.info("═" * 60)

    report_path = Path("logs") / f"report_video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({
            "data":             datetime.now().isoformat(),
            "tema_id":          script_data.get("tema_id"),
            "tema_nome":        script_data.get("tema_nome"),
            "titulo":           script_data["titulo"],
            "video_url":        results.get("video_url"),
            "duracao_segundos": elapsed.total_seconds()
        }, f, ensure_ascii=False, indent=2)
    logger.info(f"📊  Relatório: {report_path}")

    cleanup_temp(temp_dir)
    return results


if __name__ == "__main__":
    main()
