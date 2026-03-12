"""
MÓDULO 4: EDITOR DE VÍDEO
Usa MoviePy para montar os clipes de vídeo com a narração áudio.
"""

import logging
from pathlib import Path
from moviepy.editor import (
    VideoFileClip, AudioFileClip, concatenate_videoclips,
    CompositeVideoClip, ColorClip
)

logger = logging.getLogger(__name__)

# Resolução alvo (YouTube HD)
TARGET_WIDTH = 1920
TARGET_HEIGHT = 1080
TARGET_FPS = 24


def _resize_and_crop_clip(clip: VideoFileClip, target_w: int, target_h: int) -> VideoFileClip:
    """
    Redimensiona e corta um clipe para preencher o ecrã (crop center).
    """
    # Calcular aspect ratios
    clip_ratio = clip.w / clip.h
    target_ratio = target_w / target_h

    if clip_ratio > target_ratio:
        # Clip é mais largo — ajustar pela altura
        new_clip = clip.resize(height=target_h)
    else:
        # Clip é mais alto — ajustar pela largura
        new_clip = clip.resize(width=target_w)

    # Cortar ao centro
    x_center = new_clip.w / 2
    y_center = new_clip.h / 2
    cropped = new_clip.crop(
        x_center=x_center,
        y_center=y_center,
        width=target_w,
        height=target_h
    )

    return cropped


def create_final_video(
    audio_path: str,
    video_paths: list[str],
    output_dir: str
) -> str:
    """
    Monta o vídeo final sincronizando os clipes com a narração.

    Args:
        audio_path: Caminho para narração.mp3
        video_paths: Lista de caminhos dos vídeos de fundo
        output_dir: Pasta de destino

    Returns:
        str: Caminho para video_final.mp4

    Raises:
        Exception: Se a edição de vídeo falhar
    """
    logger.info("=" * 50)
    logger.info("MÓDULO 4: EDITOR DE VÍDEO")
    logger.info("=" * 50)
    logger.info("Fase 4: A montar o vídeo final com MoviePy...")

    output_path = Path(output_dir) / "video_final.mp4"

    # --- Carregar e medir o áudio ---
    logger.info(f"  A carregar áudio: {audio_path}")
    try:
        audio_clip = AudioFileClip(audio_path)
        total_duration = audio_clip.duration
        logger.info(f"  Duração total do áudio: {total_duration:.2f}s ({total_duration/60:.1f} min)")
    except Exception as e:
        logger.error(f"❌ Erro ao carregar áudio: {e}")
        raise

    # --- Calcular duração por clipe ---
    n_clips = len(video_paths)
    if n_clips == 0:
        raise ValueError("Nenhum vídeo de fundo disponível para editar")

    duration_per_clip = total_duration / n_clips
    logger.info(f"  {n_clips} clipes × {duration_per_clip:.2f}s cada")

    # --- Processar cada clipe ---
    processed_clips = []

    for i, video_path in enumerate(video_paths):
        logger.info(f"  [{i+1}/{n_clips}] A processar: {Path(video_path).name}")

        try:
            clip = VideoFileClip(video_path, audio=False)

            # Redimensionar e cortar para 1920x1080
            clip = _resize_and_crop_clip(clip, TARGET_WIDTH, TARGET_HEIGHT)

            # Ajustar duração: loop se necessário, cortar se muito longo
            if clip.duration < duration_per_clip:
                # Loop do clipe
                loops_needed = int(duration_per_clip / clip.duration) + 1
                from moviepy.editor import concatenate_videoclips as concat
                looped = concat([clip] * loops_needed)
                clip = looped.subclip(0, duration_per_clip)
            else:
                clip = clip.subclip(0, duration_per_clip)

            # Definir FPS
            clip = clip.set_fps(TARGET_FPS)

            processed_clips.append(clip)
            logger.info(f"    ✓ Clipe {i+1} processado ({duration_per_clip:.1f}s, {TARGET_WIDTH}x{TARGET_HEIGHT})")

        except Exception as e:
            logger.warning(f"    ⚠ Erro ao processar clipe {i+1} ({video_path}): {e}")
            # Fallback: clipe negro
            logger.info(f"    Usando clipe negro como substituto...")
            fallback = ColorClip(
                size=(TARGET_WIDTH, TARGET_HEIGHT),
                color=(0, 0, 0),
                duration=duration_per_clip
            ).set_fps(TARGET_FPS)
            processed_clips.append(fallback)

    # --- Concatenar todos os clipes ---
    logger.info("  A concatenar clipes...")
    try:
        final_video = concatenate_videoclips(processed_clips, method="compose")

        # Ajuste fino: garantir que o vídeo tem exatamente a duração do áudio
        if final_video.duration > total_duration:
            final_video = final_video.subclip(0, total_duration)

    except Exception as e:
        logger.error(f"❌ Erro ao concatenar clipes: {e}")
        raise

    # --- Adicionar áudio ---
    logger.info("  A adicionar faixa de áudio...")
    final_video = final_video.set_audio(audio_clip)

    # --- Renderizar ---
    logger.info(f"  A renderizar vídeo final → {output_path}")
    logger.info("  (Este processo pode demorar vários minutos...)")

    try:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        final_video.write_videofile(
            str(output_path),
            fps=TARGET_FPS,
            codec="libx264",
            audio_codec="aac",
            bitrate="4000k",
            audio_bitrate="192k",
            threads=4,
            preset="medium",
            logger=None  # Silenciar output verbose do ffmpeg
        )
    except Exception as e:
        logger.error(f"❌ Erro na renderização do vídeo: {e}")
        raise
    finally:
        # Libertar memória
        audio_clip.close()
        for clip in processed_clips:
            clip.close()
        final_video.close()

    file_size_mb = output_path.stat().st_size / (1024 * 1024)
    logger.info(f"✅ Fase 4 completa: Vídeo final renderizado → {output_path} ({file_size_mb:.1f} MB)")

    return str(output_path)