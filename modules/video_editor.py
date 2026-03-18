"""
MÓDULO 4: EDITOR DE VÍDEO v2.1 — The Silent Sage
==================================================
  - Música por secção: calma (cenas 1-2) → épica (3-5) → reflexiva (cena 6)
  - Loop suave com crossfade de 5s entre iterações
  - Audio ducking: 8% com voz, fade out 4s no final
  - Ken Burns zoom 1.0x → 1.1x
  - 18 clipes (3 por cena × 6 cenas)
  - Citações do guião (citacao_destaque) no ecrã
  - Fade to black 0.5s entre cenas
  - Brightness 70%
"""

import os
import random
import logging
from pathlib import Path
from moviepy.editor import (
    VideoFileClip, AudioFileClip, concatenate_videoclips,
    CompositeVideoClip, CompositeAudioClip, ColorClip, TextClip, VideoClip
)
from moviepy.audio.fx.all import audio_fadeout, audio_fadein, volumex

logger = logging.getLogger(__name__)

TARGET_WIDTH     = 1920
TARGET_HEIGHT    = 1080
TARGET_FPS       = 24

MUSIC_VOL        = 0.08    # 8% — tapete sonoro
MUSIC_FADEIN     = 3.0
MUSIC_FADEOUT    = 4.0
MUSIC_CROSSFADE  = 5.0     # crossfade entre iterações do loop

BRIGHTNESS       = 0.70
KEN_BURNS_ZOOM   = 1.10
FADE_DURATION    = 0.5

QUOTE_FONTSIZE   = 50
QUOTE_COLOR      = "white"
QUOTE_STROKE     = "black"
QUOTE_STROKE_W   = 2
QUOTE_Y_POS      = 0.76
QUOTE_DURATION   = 4.5
QUOTE_FADEIN     = 0.6
QUOTE_FADEOUT    = 0.6


# ─────────────────────────────────────────────────────────────────────────────
# VÍDEO
# ─────────────────────────────────────────────────────────────────────────────

def _resize_and_crop(clip):
    ratio_clip   = clip.w / clip.h
    ratio_target = TARGET_WIDTH / TARGET_HEIGHT
    if ratio_clip > ratio_target:
        clip = clip.resize(height=TARGET_HEIGHT)
    else:
        clip = clip.resize(width=TARGET_WIDTH)
    return clip.crop(
        x_center=clip.w / 2,
        y_center=clip.h / 2,
        width=TARGET_WIDTH,
        height=TARGET_HEIGHT
    )


def _apply_ken_burns(clip, zoom_end=KEN_BURNS_ZOOM):
    try:
        import cv2
        duration = clip.duration
        w, h     = clip.w, clip.h

        def make_frame(t):
            frame    = clip.get_frame(t)
            progress = t / duration if duration > 0 else 0
            zoom     = 1.0 + (zoom_end - 1.0) * progress
            nw       = int(w / zoom)
            nh       = int(h / zoom)
            x1       = (w - nw) // 2
            y1       = (h - nh) // 2
            cropped  = frame[y1:y1 + nh, x1:x1 + nw]
            return cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)

        return VideoClip(make_frame, duration=duration).set_fps(TARGET_FPS)
    except Exception as e:
        logger.warning(f"    Ken Burns falhou: {e}")
        return clip


def _apply_brightness(clip, factor=BRIGHTNESS):
    return clip.fl_image(lambda f: (f * factor).astype("uint8"))


# ─────────────────────────────────────────────────────────────────────────────
# MÚSICA POR SECÇÃO
# ─────────────────────────────────────────────────────────────────────────────

def _pick_music_files(assets_dir):
    """
    Devolve dict com 3 faixas para as 3 secções do vídeo.
    Se houver menos de 3 ficheiros, reutiliza aleatoriamente.
    Secções: intro (cenas 1-2), climax (cenas 3-5), outro (cena 6)
    """
    music_dir = assets_dir / "music"
    if not music_dir.exists():
        return {"intro": None, "climax": None, "outro": None}

    files = sorted(list(music_dir.glob("*.mp3")) + list(music_dir.glob("*.wav")))
    if not files:
        return {"intro": None, "climax": None, "outro": None}

    # Atribuir faixas por "vibe" baseado no nome do ficheiro
    calm_files  = [f for f in files if any(w in f.name.lower() for w in ["sunrise", "acoustic", "dust", "ambient"])]
    epic_files  = [f for f in files if any(w in f.name.lower() for w in ["colosseum", "dramatic", "epic", "power"])]
    other_files = [f for f in files if f not in calm_files and f not in epic_files]

    def pick(pool, fallback):
        return str(random.choice(pool)) if pool else (str(random.choice(fallback)) if fallback else None)

    intro  = pick(calm_files,  files)
    climax = pick(epic_files,  files)
    outro  = pick(other_files + calm_files, files)

    logger.info(f"  Música Intro:  {Path(intro).name if intro else 'N/A'}")
    logger.info(f"  Música Clímax: {Path(climax).name if climax else 'N/A'}")
    logger.info(f"  Música Outro:  {Path(outro).name if outro else 'N/A'}")

    return {"intro": intro, "climax": climax, "outro": outro}


def _make_section_audio(music_path, duration, fadein=MUSIC_FADEIN, fadeout=MUSIC_FADEOUT):
    """
    Cria uma faixa de música com loop suave (crossfade 5s) para uma duração alvo.
    """
    if not music_path or not Path(music_path).exists():
        return None

    try:
        base   = AudioFileClip(music_path)
        clips  = []
        total  = 0.0

        while total < duration:
            remaining = duration - total
            chunk     = base.subclip(0, min(remaining, base.duration))
            if clips:
                chunk = audio_fadein(chunk, MUSIC_CROSSFADE)
            clips.append(chunk)
            total += chunk.duration

        music = concatenate_audioclips_safe(clips)
        music = audio_fadein(music, fadein)
        music = audio_fadeout(music, fadeout)
        music = music.volumex(MUSIC_VOL)
        return music
    except Exception as e:
        logger.warning(f"    Música falhou ({Path(music_path).name}): {e}")
        return None


def concatenate_audioclips_safe(clips):
    from moviepy.editor import concatenate_audioclips
    return concatenate_audioclips(clips)


def _build_music_track(music_files, total_duration, n_scenes):
    """
    Constrói a faixa de música completa com 3 secções.
    Intro: cenas 1-2 | Clímax: cenas 3-5 | Outro: cena 6
    """
    if n_scenes == 0:
        return None

    scene_dur   = total_duration / n_scenes
    intro_dur   = scene_dur * 2
    climax_dur  = scene_dur * 3
    outro_dur   = scene_dur * 1

    # Ajuste se o número de cenas for diferente de 6
    if n_scenes != 6:
        intro_dur  = total_duration * 0.30
        climax_dur = total_duration * 0.55
        outro_dur  = total_duration * 0.15

    sections = []
    # Intro
    intro = _make_section_audio(music_files["intro"], intro_dur, fadein=MUSIC_FADEIN, fadeout=MUSIC_CROSSFADE)
    if intro:
        sections.append(intro)
        logger.info(f"  Secção Intro: {intro_dur:.1f}s")

    # Clímax
    climax = _make_section_audio(music_files["climax"], climax_dur, fadein=MUSIC_CROSSFADE, fadeout=MUSIC_CROSSFADE)
    if climax:
        sections.append(climax)
        logger.info(f"  Secção Clímax: {climax_dur:.1f}s")

    # Outro
    outro = _make_section_audio(music_files["outro"], outro_dur, fadein=MUSIC_CROSSFADE, fadeout=MUSIC_FADEOUT)
    if outro:
        sections.append(outro)
        logger.info(f"  Secção Outro: {outro_dur:.1f}s")

    if not sections:
        return None

    try:
        full_music = concatenate_audioclips_safe(sections)
        # Ajuste fino de duração
        if full_music.duration > total_duration:
            full_music = full_music.subclip(0, total_duration)
        return full_music
    except Exception as e:
        logger.warning(f"  Montagem de música falhou: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# CITAÇÕES
# ─────────────────────────────────────────────────────────────────────────────

def _build_quote_overlay(quote_text, start_time, video_w, video_h):
    """Cria TextClip com citação em destaque."""
    try:
        txt = None
        for font in ["Cinzel-Regular", "Cinzel", "Georgia-Bold", "Arial-Bold", "Arial"]:
            try:
                txt = TextClip(
                    f'"{quote_text}"',
                    fontsize=QUOTE_FONTSIZE,
                    font=font,
                    color=QUOTE_COLOR,
                    stroke_color=QUOTE_STROKE,
                    stroke_width=QUOTE_STROKE_W,
                    method="caption",
                    size=(int(video_w * 0.82), None),
                    align="center"
                )
                break
            except Exception:
                continue
        if txt is None:
            return None

        y_pos = int(video_h * QUOTE_Y_POS)
        txt   = txt.set_position(("center", y_pos))
        txt   = txt.set_start(start_time)
        txt   = txt.set_duration(QUOTE_DURATION)
        txt   = txt.crossfadein(QUOTE_FADEIN).crossfadeout(QUOTE_FADEOUT)
        return txt
    except Exception as e:
        logger.warning(f"    Citação falhou: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# FUNÇÃO PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

def create_final_video(audio_path, video_paths, output_dir, script_data=None):
    """
    Monta o vídeo final com todas as melhorias v2.1.

    Args:
        audio_path:   narração.mp3
        video_paths:  lista de 18 clipes de fundo
        output_dir:   pasta de destino
        script_data:  guião (para citações e número de cenas)

    Returns:
        str: caminho para video_final.mp4
    """
    logger.info("=" * 60)
    logger.info("  EDITOR DE VÍDEO v2.1 — The Silent Sage")
    logger.info("=" * 60)

    output_path = Path(output_dir) / "video_final.mp4"
    assets_dir  = Path(__file__).parent.parent / "assets"

    # Narração
    audio_clip     = AudioFileClip(audio_path)
    total_duration = audio_clip.duration
    logger.info(f"  Duração: {total_duration:.1f}s ({total_duration/60:.1f} min)")

    n_clips = len(video_paths)
    if n_clips == 0:
        raise ValueError("Nenhum clipe de fundo")
    duration_per_clip = total_duration / n_clips
    logger.info(f"  {n_clips} clipes × {duration_per_clip:.1f}s")

    # Processar clipes
    processed = []
    t_cursor  = 0.0

    for i, path in enumerate(video_paths):
        logger.info(f"  [{i+1}/{n_clips}] {Path(path).name}")
        try:
            clip = VideoFileClip(path, audio=False)
            clip = _resize_and_crop(clip)

            if clip.duration < duration_per_clip:
                loops = int(duration_per_clip / clip.duration) + 1
                clip  = concatenate_videoclips([clip] * loops)
            clip = clip.subclip(0, duration_per_clip)
            clip = _apply_ken_burns(clip)
            clip = _apply_brightness(clip)

            if i > 0:
                clip = clip.fadein(FADE_DURATION)
            if i < n_clips - 1:
                clip = clip.fadeout(FADE_DURATION)

            clip = clip.set_fps(TARGET_FPS).set_start(t_cursor)
            processed.append(clip)

        except Exception as e:
            logger.warning(f"    Erro ({e}) — clipe negro")
            fallback = ColorClip(
                size=(TARGET_WIDTH, TARGET_HEIGHT),
                color=(0, 0, 0),
                duration=duration_per_clip
            ).set_fps(TARGET_FPS).set_start(t_cursor)
            processed.append(fallback)

        t_cursor += duration_per_clip

    # Concatenar
    logger.info("  A concatenar...")
    final_video = concatenate_videoclips(processed, method="compose")
    if final_video.duration > total_duration:
        final_video = final_video.subclip(0, total_duration)

    # Citações do guião
    overlays   = []
    n_scenes   = len(script_data["cenas"]) if script_data and "cenas" in script_data else 6
    scene_dur  = total_duration / n_scenes

    if script_data and "cenas" in script_data:
        for i, cena in enumerate(script_data["cenas"]):
            quote = cena.get("citacao_destaque", "").strip()
            if quote and len(quote.split()) <= 20:
                # Mostrar a 40% do tempo da cena
                start_t = i * scene_dur + scene_dur * 0.40
                overlay = _build_quote_overlay(quote, start_t, TARGET_WIDTH, TARGET_HEIGHT)
                if overlay:
                    overlays.append(overlay)
                    logger.info(f"  Citação cena {i+1}: \"{quote[:55]}\"")

    if overlays:
        final_video = CompositeVideoClip([final_video] + overlays)
        logger.info(f"  {len(overlays)} citações adicionadas")

    # Música por secção
    music_files  = _pick_music_files(assets_dir)
    audio_layers = [audio_clip]
    music_track  = _build_music_track(music_files, total_duration, n_scenes)

    if music_track:
        audio_layers.append(music_track)
        logger.info("  Música por secção adicionada")

    final_audio = CompositeAudioClip(audio_layers) if len(audio_layers) > 1 else audio_clip
    final_video = final_video.set_audio(final_audio)

    # Renderizar
    logger.info(f"  A renderizar → {output_path}")
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
            logger=None
        )
    except Exception as e:
        logger.error(f"  Erro: {e}")
        raise
    finally:
        audio_clip.close()
        for c in processed:
            try:
                c.close()
            except Exception:
                pass
        try:
            final_video.close()
        except Exception:
            pass

    size_mb = output_path.stat().st_size / (1024 * 1024)
    logger.info(f"  Vídeo final: {output_path} ({size_mb:.1f} MB)")
    return str(output_path)