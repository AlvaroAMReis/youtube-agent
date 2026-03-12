"""
YOUTUBE AUTONOMOUS AGENT v2.0
==============================
Cria e publica automaticamente:
  → 1 Vídeo Longo (monetização AdSense)
  → 1 Short derivado (crescimento de audiência)

Fluxo:
  1. Gerar guião (OpenAI GPT-4o)
  2. Gerar narração longa (ElevenLabs)
  3. Descarregar media (Pexels + DALL-E 3)
  4. Editar vídeo longo (MoviePy/FFmpeg)
  5. Publicar vídeo longo (YouTube Data API v3)
  6. Gerar + publicar Short derivado (Módulo 6)
"""

import os
import sys
import json
import shutil
import logging
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Módulos internos
from modules.script_generator import generate_script
from modules.voice_generator import generate_narration
from modules.media_generator import generate_all_media
from modules.video_editor import create_final_video
from modules.youtube_uploader import upload_to_youtube, _get_authenticated_service
from modules.shorts_generator import generate_and_upload_short


# ─────────────────────────────────────────────
# CONFIGURAÇÃO DE LOGGING
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

    for noisy_lib in ["httpx", "httpcore", "moviepy", "googleapiclient", "urllib3"]:
        logging.getLogger(noisy_lib).setLevel(logging.WARNING)

    logging.info(f"📋 Logs em: {log_file}")


# ─────────────────────────────────────────────
# FUNÇÕES AUXILIARES
# ─────────────────────────────────────────────

def load_environment() -> dict:
    load_dotenv()

    required_vars = {
        "OPENAI_API_KEY": "Chave API da OpenAI",
        "ELEVENLABS_API_KEY": "Chave API do ElevenLabs",
        "ELEVENLABS_VOICE_ID": "ID da voz ElevenLabs",
        "PEXELS_API_KEY": "Chave API do Pexels",
    }

    missing = []
    for var, desc in required_vars.items():
        if not os.getenv(var):
            missing.append(f"  - {var} ({desc})")

    if missing:
        raise EnvironmentError(
            "Variáveis de ambiente em falta no .env:\n" + "\n".join(missing)
        )

    config = {
        "niche": os.getenv("CHANNEL_NICHE", "Estoicismo"),
        "language": os.getenv("SCRIPT_LANGUAGE", "pt"),
        "voice_id": os.getenv("ELEVENLABS_VOICE_ID"),
        "client_secrets": os.getenv("YOUTUBE_CLIENT_SECRETS_FILE", "client_secrets.json"),
        "create_short": os.getenv("CREATE_SHORT", "true").lower() == "true",
    }

    logging.info(
        f"✓ Config carregada | Nicho: '{config['niche']}' | "
        f"Short: {'✅' if config['create_short'] else '❌'}"
    )
    return config


def setup_temp_dir() -> str:
    temp_dir = Path("temp")
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(exist_ok=True)
    logging.info(f"📁 Pasta /temp criada")
    return str(temp_dir)


def save_script_to_file(script_data: dict, temp_dir: str) -> None:
    path = Path(temp_dir) / "guião.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(script_data, f, ensure_ascii=False, indent=2)
    logging.info(f"  Guião guardado: {path}")


def cleanup_temp(temp_dir: str) -> None:
    try:
        shutil.rmtree(temp_dir)
        logging.info(f"🧹 Pasta /temp removida com sucesso")
    except Exception as e:
        logging.warning(f"⚠ Limpeza falhou: {e}")


def print_banner() -> None:
    print("""
╔══════════════════════════════════════════════════════════╗
║       YOUTUBE AUTONOMOUS AGENT  v2.0                     ║
║       Vídeo Longo  +  Short Automático                   ║
╚══════════════════════════════════════════════════════════╝
    """)


def section(title: str) -> None:
    logging.info("\n" + "═" * 60)
    logging.info(f"  {title}")
    logging.info("═" * 60)


# ─────────────────────────────────────────────
# FUNÇÃO PRINCIPAL
# ─────────────────────────────────────────────

def main():
    print_banner()
    setup_logging()
    logger = logging.getLogger(__name__)

    start_time = datetime.now()
    logger.info(f"🚀 Agente iniciado: {start_time.strftime('%d/%m/%Y %H:%M:%S')}")

    # ── Configuração ───────────────────────────────────────────
    try:
        config = load_environment()
    except EnvironmentError as e:
        logger.critical(f"ERRO DE CONFIGURAÇÃO:\n{e}")
        sys.exit(1)

    temp_dir = setup_temp_dir()
    results = {}  # Guardar resultados de cada fase

    # ─────────────────────────────────────────────────────────
    # FASE 1: GUIÃO
    # ─────────────────────────────────────────────────────────
    section("FASE 1 — GERADOR DE GUIÃO (GPT-4o)")
    try:
        script_data = generate_script(config["niche"], config["language"])
        script_data["nicho"] = config["niche"]  # Injetar nicho para uso no Módulo 6
        save_script_to_file(script_data, temp_dir)
        results["script"] = script_data
    except Exception as e:
        logger.critical(f"💥 FALHA FATAL Fase 1: {e}")
        cleanup_temp(temp_dir)
        sys.exit(1)

    # ─────────────────────────────────────────────────────────
    # FASE 2: VOZ
    # ─────────────────────────────────────────────────────────
    section("FASE 2 — GERADOR DE VOZ (ElevenLabs)")
    try:
        audio_path = generate_narration(
            script_data["cenas"], temp_dir, config["voice_id"]
        )
        results["audio"] = audio_path
    except Exception as e:
        logger.critical(f"💥 FALHA FATAL Fase 2: {e}")
        cleanup_temp(temp_dir)
        sys.exit(1)

    # ─────────────────────────────────────────────────────────
    # FASE 3: MEDIA
    # ─────────────────────────────────────────────────────────
    section("FASE 3 — GERADOR DE MEDIA (Pexels + DALL-E 3)")
    try:
        media = generate_all_media(script_data, temp_dir)
        results["videos"] = media["videos"]
        results["thumbnail"] = media["thumbnail"]
    except Exception as e:
        logger.critical(f"💥 FALHA FATAL Fase 3: {e}")
        cleanup_temp(temp_dir)
        sys.exit(1)

    # ─────────────────────────────────────────────────────────
    # FASE 4: EDIÇÃO
    # ─────────────────────────────────────────────────────────
    section("FASE 4 — EDITOR DE VÍDEO (MoviePy/FFmpeg)")
    try:
        final_video_path = create_final_video(
            audio_path=results["audio"],
            video_paths=results["videos"],
            output_dir=temp_dir
        )
        results["final_video"] = final_video_path
    except Exception as e:
        logger.critical(f"💥 FALHA FATAL Fase 4: {e}")
        cleanup_temp(temp_dir)
        sys.exit(1)

    # ─────────────────────────────────────────────────────────
    # FASE 5: UPLOAD VÍDEO LONGO
    # ─────────────────────────────────────────────────────────
    section("FASE 5 — UPLOAD YOUTUBE (Vídeo Longo)")
    try:
        # Obter serviço autenticado (será reutilizado para o Short)
        youtube_service = _get_authenticated_service(config["client_secrets"])

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

    # ─────────────────────────────────────────────────────────
    # FASE 6: SHORT (opcional, controlado por CREATE_SHORT no .env)
    # ─────────────────────────────────────────────────────────
    if config["create_short"]:
        section("FASE 6 — GERADOR DE SHORTS (Módulo 6)")
        try:
            # Reutilizar o serviço YouTube já autenticado
            youtube_service = _get_authenticated_service(config["client_secrets"])

            short_url = generate_and_upload_short(
                script_data=script_data,
                thumbnail_path=results["thumbnail"],
                voice_id=config["voice_id"],
                youtube_service=youtube_service,
                temp_dir=temp_dir
            )
            results["short_url"] = short_url

        except Exception as e:
            # Short falha de forma não-fatal — o vídeo longo já foi publicado
            logger.error(f"⚠ Fase 6 FALHOU (não fatal): {e}")
            logger.warning("O vídeo longo foi publicado com sucesso. O Short não foi criado.")
            results["short_url"] = None
    else:
        logger.info("Fase 6 desativada (CREATE_SHORT=false no .env)")

    # ─────────────────────────────────────────────────────────
    # RELATÓRIO FINAL
    # ─────────────────────────────────────────────────────────
    elapsed = datetime.now() - start_time
    mins = int(elapsed.total_seconds() // 60)
    secs = int(elapsed.total_seconds() % 60)

    logger.info("\n" + "═" * 60)
    logger.info("🎉  AGENTE CONCLUÍDO COM SUCESSO!")
    logger.info("═" * 60)
    logger.info(f"  📹  Título:       {script_data['titulo']}")
    logger.info(f"  🔗  Vídeo longo:  {results.get('video_url', 'N/A')}")
    if results.get("short_url"):
        logger.info(f"  ⚡  Short:        {results['short_url']}")
    logger.info(f"  ⏱   Tempo total:  {mins}m {secs}s")
    logger.info("═" * 60)

    # Salvar relatório JSON
    report_path = Path("logs") / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report = {
        "data": datetime.now().isoformat(),
        "nicho": config["niche"],
        "titulo": script_data["titulo"],
        "video_url": results.get("video_url"),
        "short_url": results.get("short_url"),
        "duracao_segundos": elapsed.total_seconds()
    }
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    logger.info(f"📊  Relatório guardado: {report_path}")

    # Limpeza
    cleanup_temp(temp_dir)

    return results


if __name__ == "__main__":
    main()