"""
MÓDULO 6: GERADOR DE SHORTS
Cria automaticamente um YouTube Short a partir do guião do vídeo longo.

Fluxo:
  6a. Seleciona a cena mais impactante via GPT-4o
  6b. Gera narração curta (30-40s) via ElevenLabs
  6c. Descarrega vídeo vertical do Pexels (ou reformata existente)
  6d. Edita em formato 9:16 com legendas Whisper sincronizadas
  6e. Faz upload como YouTube Short
"""

import os
import json
import time
import logging
import textwrap
from pathlib import Path

from openai import OpenAI
from moviepy.editor import (
    VideoFileClip, AudioFileClip, TextClip,
    CompositeVideoClip, ColorClip, concatenate_videoclips
)
from moviepy.video.fx.all import crop
import requests
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings
from googleapiclient.http import MediaFileUpload
from moviepy.config import change_settings
change_settings({"IMAGEMAGICK_BINARY": r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"})

logger = logging.getLogger(__name__)

# Dimensões do Short (vertical 9:16)
SHORT_WIDTH = 1080
SHORT_HEIGHT = 1920
SHORT_MAX_DURATION = 58  # segundos (margem de segurança abaixo dos 60s)
SHORT_FPS = 30


# ─────────────────────────────────────────────
# 6a. SELECIONAR CENA MAIS IMPACTANTE
# ─────────────────────────────────────────────

def select_best_scene(script_data: dict) -> dict:
    """
    Usa GPT-4o para selecionar a cena mais impactante do guião
    e reescrever o texto para formato Short (30-40 segundos).

    Returns:
        dict com: texto_narrado, palavra_chave_visual, titulo_short,
                  texto_gancho (primeiros 3s), hashtags
    """
    logger.info("  Fase 6a: A selecionar a melhor cena para Short...")

    client = OpenAI()

    cenas_resumidas = []
    for i, cena in enumerate(script_data["cenas"]):
        cenas_resumidas.append({
            "numero": i + 1,
            "preview": cena["texto_narrado"][:150] + "...",
            "palavra_chave_visual": cena["palavra_chave_visual"]
        })

    system_prompt = """You are the lead scriptwriter for "@TheSilentSage" — a Dark Stoicism YouTube channel.

PERSONA:
Your voice is solemn, cinematic, and authoritative. You write for an audience seeking resilience and self-control.
You use a "Dark Philosophy" aesthetic: brutal truths, focus on mortality, and the power of the internal mind.
You write for a deep AI voice (ElevenLabs) — slow, pauseful, heavy.
You NEVER use coach-speak or generic motivation.

VOCABULARY — use these words:
Unshakable, Internal Citadel, Ephemeral, Discipline, Chaos, Fate, Virtue, Mortality, Dust, Slave, Sovereign, Retreat, Stone, Silence

BANNED — never use:
wisdom, embrace, journey, life lessons, in today's world, fast-paced, welcome back, ancient wisdom,
motivational, positive, say out loud, write it down, repeat after me, coach, mindset hack, thanks for watching

SCRIPT RULES:
1. HOOK (0-5s): Shocking direct statement. NEVER a question. Use "You" to confront the viewer immediately.
2. RHYTHM: Alternate short punchy sentences (impact) with longer rhythmic ones (reflection).
3. LOOP: The final sentence must lead back to the hook seamlessly. No black screens. No "thanks for watching".
4. CTA: Always end with exactly — "Follow for more Stoic wisdom." No emojis. No variations.

VISUAL CATEGORIES (Stoic/Greco-Roman only — NEVER Zen or Asian):
- Chaos/Subjection:   storm clouds, crashing ocean waves, blurred city crowd, dark forest
- Authority/History:  marble statues, ancient Roman ruins, Greek temple, weathered stone
- Inner Strength:     high mountain peaks, misty mountains, lone rock in storm, stone cliffs
- Ephemerality/Silence: candle flame in dark, match smoke, fire flames, starry night sky

You respond ONLY in valid JSON format. No extra text. No markdown."""

    user_prompt = f"""Channel: "@TheSilentSage" — Dark Stoicism. Stone. Fire. Silence.
Audience: 18-35, overwhelmed, anxious, lost. They want brutal truth, not comfort.

Long video title: {script_data['titulo']}

Available scenes:
{json.dumps(cenas_resumidas, ensure_ascii=False, indent=2)}

Write a 30-second Short script. Make the viewer think: "I have never heard it like this."
Then make them follow — not because you asked, but because they must.

STRUCTURE:

HOOK (0-5s)
- Brutal statement of truth. Never a question.
- Strong: "You are not free. You are a slave to every insult, every fleeting emotion."
- Strong: "You are not stressed. You are addicted to chaos."
- Weak (never): "Are you stressed?" / "Have you ever wondered..."

TEACHING (5-20s)
- One specific real moment from Marcus Aurelius, Seneca, or Epictetus — not a generic quote.
- Show the philosopher as a flawed human who still chose discipline.
- Betrayal, loss, rage, humiliation — things the viewer recognises.
- NEVER invent mysteries. The Meditations exist. The Letters exist. Respect the audience.

PRACTICE (20-28s)
- One internal shift. Not a coaching trick. Not verbal performance.
- Strong: "Retreat inward. Your virtue is the only thing they cannot take. Everything else... is just dust."
- Weak: "Say out loud: this is not mine to carry."

OUTRO (28-30s)
- End in silence and identity. Connect to the channel name: The Silent Sage.
- Strong: "The truth is found in silence, not in the crowd. Follow for more Stoic wisdom."
- Strong: "The path is narrow. Most will stay in the noise. Follow to join the silent."
- The last sentence must loop back to the hook naturally — no black screen, no ending.

WRITING RULES:
- Every sentence under 10 words
- Use "..." for dramatic pauses
- Total: 80-100 words (30s at slow AI voice pace)
- Hook line = base of titulo_short
- End always with exactly: "Follow for more Stoic wisdom."

VISUAL ARC — emotional progression, Greco-Roman only:
  Hook     → Chaos/Subjection   → 'dramatic storm clouds' OR 'ocean waves calm' OR 'dark forest mystical'
  Teaching → Authority/History  → 'ancient rome ruins' OR 'greek temple' OR 'ancient library'
  Practice → Inner Strength     → 'misty mountains' OR 'mountain fog cinematic' OR 'waterfall nature'
  Outro    → Ephemerality/Silence → 'candle flame dark' OR 'fire flames dark' OR 'starry night sky'

Return EXCLUSIVELY this JSON:
{{
  "cena_escolhida": <scene number>,
  "titulo_short": "Hook-based title, punchy, under 55 chars, ends with #Shorts",
  "texto_gancho": "Exact first sentence (max 12 words, brutal statement, never a question)",
  "texto_narrado": "Full narration — 4-part structure, 80-100 words, use ... for pauses",
  "cenas_visuais": [
    {{
      "parte": "hook",
      "texto": "exact sentence(s) from narration for this part",
      "visual": "Choose ONE from: 'dramatic storm clouds', 'ocean waves calm', 'dark forest mystical'"
    }},
    {{
      "parte": "teaching",
      "texto": "exact sentence(s) from narration for this part",
      "visual": "Choose ONE from: 'ancient rome ruins', 'greek temple', 'ancient library'"
    }},
    {{
      "parte": "practice",
      "texto": "exact sentence(s) from narration for this part",
      "visual": "Choose ONE from: 'misty mountains', 'mountain fog cinematic', 'waterfall nature'"
    }},
    {{
      "parte": "outro",
      "texto": "exact sentence(s) from narration for this part",
      "visual": "Choose ONE from: 'candle flame dark', 'fire flames dark', 'starry night sky'"
    }}
  ],
  "palavra_chave_visual": "Choose ONE from: 'ancient rome ruins', 'misty mountains', 'candle flame dark'",
  "hashtags": ["#Shorts", "#Stoicism", "#MarcusAurelius", "#Mindset", "#SelfImprovement"]
}}"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=1500,
            response_format={"type": "json_object"}
        )

        short_data = json.loads(response.choices[0].message.content)

        required = ["titulo_short", "texto_narrado", "palavra_chave_visual", "hashtags", "texto_gancho"]
        for key in required:
            if key not in short_data:
                raise ValueError(f"Campo obrigatório '{key}' em falta no JSON do Short")

        logger.info(f"  ✓ Cena {short_data.get('cena_escolhida')} selecionada | Gancho: '{short_data['texto_gancho']}'")
        return short_data

    except Exception as e:
        logger.error(f"  ❌ Erro ao selecionar cena para Short: {e}")
        raise


# ─────────────────────────────────────────────
# 6b. GERAR NARRAÇÃO DO SHORT
# ─────────────────────────────────────────────

def generate_short_narration(texto: str, output_dir: str, voice_id: str) -> str:
    """
    Gera o áudio MP3 para o Short via ElevenLabs.

    Returns:
        str: Caminho para narração_short.mp3
    """
    logger.info("  Fase 6b: A gerar narração do Short...")

    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise EnvironmentError("ELEVENLABS_API_KEY não encontrada")

    client = ElevenLabs(api_key=api_key)
    output_path = Path(output_dir) / "narração_short.mp3"

    try:
        audio_generator = client.text_to_speech.convert(
            voice_id=voice_id,
            text=texto,
            model_id="eleven_multilingual_v2",
            voice_settings=VoiceSettings(
                stability=0.5,
                similarity_boost=0.90,
                style=0.45,
                use_speaker_boost=True
            )
        )

        with open(output_path, "wb") as f:
            for chunk in audio_generator:
                if chunk:
                    f.write(chunk)

        audio_clip = AudioFileClip(str(output_path))
        duration = audio_clip.duration
        audio_clip.close()

        if duration > SHORT_MAX_DURATION:
            logger.warning(f"  ⚠ Narração tem {duration:.1f}s (máx {SHORT_MAX_DURATION}s) — será cortada")

        logger.info(f"  ✓ Narração do Short: {duration:.1f}s → {output_path}")
        return str(output_path)

    except Exception as e:
        logger.error(f"  ❌ Erro ao gerar narração do Short: {e}")
        raise


# ─────────────────────────────────────────────
# 6c. DESCARREGAR VÍDEO VERTICAL
# ─────────────────────────────────────────────

def download_vertical_video(keyword: str, output_dir: str) -> str:
    """
    Pesquisa e descarrega um vídeo vertical (portrait) do Pexels.
    Se não encontrar vertical, descarrega horizontal e converte depois.

    Returns:
        str: Caminho para o vídeo descarregado
    """
    logger.info(f"  Fase 6c: A descarregar vídeo vertical para '{keyword}'...")

    api_key = os.getenv("PEXELS_API_KEY")
    if not api_key:
        raise EnvironmentError("PEXELS_API_KEY não encontrada")

    headers = {"Authorization": api_key}
    output_path = Path(output_dir) / "video_short_bg.mp4"

    for orientation in ["portrait", "landscape"]:
        params = {
            "query": keyword,
            "per_page": 8,
            "orientation": orientation,
            "size": "medium"
        }

        try:
            response = requests.get(
                "https://api.pexels.com/videos/search",
                headers=headers,
                params=params,
                timeout=15
            )
            response.raise_for_status()
            videos = response.json().get("videos", [])

            for video in videos:
                duration = video.get("duration", 0)
                if duration < 3:
                    continue

                video_files = sorted(
                    video.get("video_files", []),
                    key=lambda x: x.get("width", 0),
                    reverse=True
                )

                for vf in video_files:
                    w = vf.get("width", 0)
                    h = vf.get("height", 0)

                    if orientation == "portrait" and h > w and h >= 1920 and w >= 1080:
                        url = vf.get("link")
                        if url and _download_video_file(url, output_path):
                            logger.info(f"  ✓ Vídeo vertical descarregado ({w}x{h})")
                            return str(output_path)

                    if orientation == "landscape" and w >= 1920:
                        url = vf.get("link")
                        if url and _download_video_file(url, output_path):
                            logger.info(f"  ✓ Vídeo landscape descarregado (será convertido para 9:16)")
                            return str(output_path)

        except Exception as e:
            logger.warning(f"  Erro na pesquisa Pexels ({orientation}): {e}")
            continue

        time.sleep(0.3)

    # Fallback genérico
    logger.warning("  ⚠ Usando fallback genérico 'dark atmosphere'")
    fallback_params = {"query": "dark atmosphere cinematic", "per_page": 3, "orientation": "landscape"}
    try:
        r = requests.get("https://api.pexels.com/videos/search", headers=headers, params=fallback_params, timeout=15)
        r.raise_for_status()
        videos = r.json().get("videos", [])
        if videos:
            vf_list = sorted(videos[0].get("video_files", []), key=lambda x: x.get("width", 0), reverse=True)
            for vf in vf_list:
                if vf.get("width", 0) >= 1920:
                    if _download_video_file(vf["link"], output_path):
                        return str(output_path)
    except Exception as e:
        logger.error(f"  Erro no fallback: {e}")

    raise RuntimeError("Não foi possível descarregar nenhum vídeo de fundo para o Short")


def _download_video_file(url: str, output_path: Path) -> bool:
    """Descarrega um ficheiro de vídeo."""
    try:
        r = requests.get(url, stream=True, timeout=60)
        r.raise_for_status()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        return output_path.stat().st_size > 10_000
    except Exception:
        return False


def download_multi_scene_videos(cenas_visuais: list, fallback_keyword: str, output_dir: str) -> list:
    """
    Descarrega um vídeo de fundo diferente para cada parte do Short.
    Retorna lista de paths na ordem: [hook, teaching, practice, outro]
    Se falhar alguma parte, usa o fallback global.
    """
    logger.info("  🎬 A descarregar vídeos por cena...")
    paths = []
    for i, cena in enumerate(cenas_visuais):
        keyword = cena.get("visual", fallback_keyword)
        output_path = Path(output_dir) / f"video_scene_{i}_{cena.get('parte','part')}.mp4"
        try:
            path = download_vertical_video(keyword, output_dir)
            # renomear para não sobrescrever entre cenas
            import shutil
            shutil.move(path, str(output_path))
            paths.append(str(output_path))
            logger.info(f"  ✓ Cena '{cena.get('parte')}' → {keyword}")
        except Exception as e:
            logger.warning(f"  ⚠ Falhou cena '{cena.get('parte')}': {e} — usando fallback")
            try:
                path = download_vertical_video(fallback_keyword, output_dir)
                import shutil
                shutil.move(path, str(output_path))
                paths.append(str(output_path))
            except Exception:
                paths.append(None)
    return paths


# ─────────────────────────────────────────────
# 6d. EDITAR VÍDEO SHORT (9:16)
# ─────────────────────────────────────────────

def _make_vertical_clip(video_path: str, duration: float) -> VideoFileClip:
    clip = VideoFileClip(video_path, audio=False)

    scale_w = SHORT_WIDTH / clip.w
    scale_h = SHORT_HEIGHT / clip.h
    scale = max(scale_w, scale_h)

    new_w = int(clip.w * scale)
    new_h = int(clip.h * scale)
    scaled = clip.resize((new_w, new_h))

    cropped = crop(
        scaled,
        x_center=scaled.w / 2,
        y_center=scaled.h / 2,
        width=SHORT_WIDTH,
        height=SHORT_HEIGHT
    )

    if cropped.duration < duration:
        loops = int(duration / cropped.duration) + 1
        cropped = concatenate_videoclips([cropped] * loops)

    return cropped.subclip(0, min(duration, SHORT_MAX_DURATION)).set_fps(SHORT_FPS)


def _apply_ken_burns(clip: VideoFileClip, zoom_factor: float = 1.04) -> VideoFileClip:
    """
    Aplica Ken Burns effect — slow zoom sintético para evitar clips estáticos.
    Aumenta zoom de 1.0x para zoom_factor ao longo da duração do clip.
    """
    def zoom_frame(get_frame, t):
        frame = get_frame(t)
        progress = t / clip.duration if clip.duration > 0 else 0
        current_zoom = 1.0 + (zoom_factor - 1.0) * progress
        h, w = frame.shape[:2]
        new_w = int(w / current_zoom)
        new_h = int(h / current_zoom)
        x1 = (w - new_w) // 2
        y1 = (h - new_h) // 2
        cropped_frame = frame[y1:y1+new_h, x1:x1+new_w]
        import cv2
        return cv2.resize(cropped_frame, (w, h), interpolation=cv2.INTER_LINEAR)

    try:
        import cv2
        return clip.fl(zoom_frame, apply_to="mask" if clip.mask else [])
    except Exception:
        return clip  # fallback sem Ken Burns se cv2 não disponível


def _get_cta_text(duration: float) -> str:
    """
    Retorna CTA rotativo entre 3 opções para variar engajamento.
    Alterna baseado no segundo actual para ser determinístico por run.
    """
    import time
    ctas = [
        "Follow for more Stoic wisdom",
        "Which emotion is your master?",
        "Are you building your citadel?",
    ]
    index = int(time.time()) % len(ctas)
    return ctas[index]


def _create_text_overlay(text: str, duration: float, position: str = "bottom") -> TextClip:
    """
    Cria texto animado para sobrepor no vídeo.

    Safe zones YouTube Shorts:
      'top'    → 0.12 (abaixo da barra de pesquisa — safe zone)
      'bottom' → 0.84 (acima dos botões de like/comentário — safe zone)
      Legendas → 0.68 (zona central-baixo — sempre segura)
    """
    wrapped = textwrap.fill(text, width=22)

    if position == "top":
        y_pos = 0.12   # era 0.08 — movido para baixo da barra de pesquisa
    else:
        y_pos = 0.84   # era 0.88 — movido para cima dos botões de like

    try:
        txt = TextClip(
            wrapped,
            fontsize=65,
            font="Arial-Bold",
            color="white",
            stroke_color="black",
            stroke_width=3,
            method="caption",
            size=(SHORT_WIDTH - 80, None),
            align="center"
        ).set_duration(duration).set_position(("center", y_pos), relative=True)
        return txt
    except Exception:
        txt = TextClip(
            wrapped,
            fontsize=58,
            color="white",
            stroke_color="black",
            stroke_width=2,
            method="caption",
            size=(SHORT_WIDTH - 80, None),
            align="center"
        ).set_duration(duration).set_position(("center", y_pos), relative=True)
        return txt


# ─────────────────────────────────────────────
# WHISPER — LEGENDAS SINCRONIZADAS
# ─────────────────────────────────────────────

def _generate_subtitles(audio_path: str) -> list:
    """Gera legendas sincronizadas via Whisper API."""
    logger.info("  🎤 A gerar legendas via Whisper...")
    try:
        client = OpenAI()
        with open(audio_path, "rb") as f:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                response_format="verbose_json",
                timestamp_granularities=["word"]
            )
        words = transcript.words
        logger.info(f"  ✓ {len(words)} palavras transcritas")
        return words
    except Exception as e:
        logger.warning(f"  ⚠ Whisper falhou: {e}")
        return []


def edit_short_video(
    audio_path: str,
    video_bg_path: str,
    short_data: dict,
    output_dir: str,
    scene_video_paths: list = None
) -> str:
    """
    Monta o Short final: vídeo 9:16 + áudio + legendas Whisper + gancho + CTA fixo.

    SOUND DESIGN:
      0-5s    → heavy_wind.wav (hook atmosphere) + música ambiente a 6%
      ~15s    → stoic_bell.wav quando filósofo é mencionado + ducking da música
      últimos 4s → silêncio absoluto (música faz fade out)
      fim     → micro-fade 0.1s para loop imperceptível

    Layout visual (relativo ao ecrã):
      0.08 → Gancho (primeiros 4s)
      0.68 → Legendas Whisper sincronizadas
      0.88 → CTA fixo (últimos 4s)

    Returns:
        str: Caminho para short_final.mp4
    """
    logger.info("  Fase 6d: A editar Short (9:16)...")

    output_path = Path(output_dir) / "short_final.mp4"

    # Carregar narração
    audio = AudioFileClip(audio_path)
    duration = min(audio.duration, SHORT_MAX_DURATION)
    logger.info(f"  Duração do Short: {duration:.1f}s")

    import random
    from moviepy.audio.fx.all import audio_loop, volumex
    from moviepy.editor import CompositeAudioClip

    sounds_dir = Path(__file__).parent.parent / "assets" / "signature_sounds"
    music_dir  = Path(__file__).parent.parent / "assets" / "music"

    audio_layers = [audio]  # narração sempre presente

    # ── Música ambiente (fundo) ──────────────────────────────────────────
    music_files = list(music_dir.glob("*.mp3"))
    if music_files:
        music_path = random.choice(music_files)
        logger.info(f"  🎵 Música: {music_path.name}")
        music = AudioFileClip(str(music_path))
        music = audio_loop(music, duration=duration)
        music = volumex(music, 0.05)          # 5% — abaixo dos efeitos
        music = music.audio_fadein(1.5)
        music = music.audio_fadeout(4.0)      # silêncio nos últimos 4s
        audio_layers.append(music)
    else:
        logger.warning("  ⚠ Nenhuma música encontrada em assets/music/")

    # ── Heavy Wind (hook — primeiros 5s) ────────────────────────────────
    wind_path = sounds_dir / "heavy_wind.wav"
    if wind_path.exists():
        try:
            wind = AudioFileClip(str(wind_path))
            wind_duration = min(5.0, wind.duration)
            wind = wind.subclip(0, wind_duration)
            wind = volumex(wind, 0.35)        # destacado mas não sobrepõe a voz
            wind = wind.audio_fadein(0.3).audio_fadeout(1.5)
            wind = wind.set_start(0)
            audio_layers.append(wind)
            logger.info(f"  💨 Wind: {wind_duration:.1f}s no hook")
        except Exception as e:
            logger.warning(f"  ⚠ Wind falhou: {e}")
    else:
        logger.warning("  ⚠ heavy_wind.wav não encontrado em assets/signature_sounds/")

    # ── Stoic Bell (momento do filósofo — detectado via Whisper) ────────
    bell_path = sounds_dir / "stoic_bell.wav"
    bell_trigger_time = None

    # Detectar timestamp do filósofo via palavras do Whisper
    whisper_words = _generate_subtitles(audio_path)
    philosopher_names = {"marcus", "aurelius", "seneca", "epictetus"}
    if whisper_words:
        for w in whisper_words:
            if hasattr(w, 'word') and w.word.lower().strip(".,") in philosopher_names:
                bell_trigger_time = max(0, w.start - 0.2)  # 0.2s antes da palavra
                logger.info(f"  🔔 Bell trigger: '{w.word}' em {bell_trigger_time:.1f}s")
                break

    if bell_trigger_time is None:
        # Fallback: disparar a 30% da duração
        bell_trigger_time = duration * 0.30
        logger.info(f"  🔔 Bell trigger (fallback): {bell_trigger_time:.1f}s")

    if bell_path.exists():
        try:
            bell = AudioFileClip(str(bell_path))
            bell_use_duration = min(5.0, bell.duration, duration - bell_trigger_time)
            bell = bell.subclip(0, bell_use_duration)
            bell = volumex(bell, 0.28)        # presente mas não abafa a voz
            bell = bell.audio_fadein(0.1).audio_fadeout(2.0)
            bell = bell.set_start(bell_trigger_time)
            audio_layers.append(bell)

            # Ducking da música no momento do bell (baixa para 2% durante 4s)
            if music_files:
                music_duck = AudioFileClip(str(music_path))
                music_duck = audio_loop(music_duck, duration=duration)
                duck_start = bell_trigger_time
                duck_end   = min(bell_trigger_time + 4.0, duration - 4.0)
                if duck_end > duck_start:
                    music_duck = music_duck.subclip(duck_start, duck_end)
                    music_duck = volumex(music_duck, -0.03)  # compensa o 5% base → ~2%
                    music_duck = music_duck.audio_fadein(0.3).audio_fadeout(0.5)
                    music_duck = music_duck.set_start(duck_start)
                    audio_layers.append(music_duck)

            logger.info(f"  🔔 Bell: {bell_use_duration:.1f}s a partir de {bell_trigger_time:.1f}s")
        except Exception as e:
            logger.warning(f"  ⚠ Bell falhou: {e}")
    else:
        logger.warning("  ⚠ stoic_bell.wav não encontrado em assets/signature_sounds/")

    # ── Micro-fade final (0.1s) para loop imperceptível ─────────────────
    try:
        audio = audio.audio_fadeout(0.1)
        audio_layers[0] = audio
    except Exception:
        pass

    # ── Compor todas as camadas de áudio ────────────────────────────────
    final_audio = CompositeAudioClip(audio_layers).subclip(0, duration)
    logger.info(f"  🎚  Audio layers: {len(audio_layers)} (narração + música + wind + bell)")

    layers = []
    from moviepy.video.fx.all import colorx

    # 1. Vídeo de fundo
    cenas_visuais = short_data.get("cenas_visuais", [])
    if scene_video_paths and len(scene_video_paths) == len(cenas_visuais) and len(cenas_visuais) == 4:
        # Usar vídeos diferentes por cena, divididos em 4 partes iguais
        logger.info("  🎬 Montando vídeo de fundo com cenas múltiplas...")
        part_duration = duration / 4
        bg_clips = []
        for i, vpath in enumerate(scene_video_paths):
            if vpath and Path(vpath).exists():
                try:
                    clip = _make_vertical_clip(vpath, part_duration)
                    clip = colorx(clip, 0.7)
                    clip = clip.set_start(i * part_duration)
                    bg_clips.append(clip)
                except Exception as e:
                    logger.warning(f"  ⚠ Cena {i} falhou: {e}")
        if bg_clips:
            layers.extend(bg_clips)
        else:
            bg_clip = _make_vertical_clip(video_bg_path, duration)
            bg_clip = _apply_ken_burns(bg_clip)
            layers.append(colorx(bg_clip, 0.7))
    else:
        # Fallback: vídeo único para o Short todo
        bg_clip = _make_vertical_clip(video_bg_path, duration)
        bg_clip = _apply_ken_burns(bg_clip)
        layers.append(colorx(bg_clip, 0.7))

    # 2. Legendas Whisper sincronizadas — posição 0.68
    # Reutiliza whisper_words já obtido no sound design (sem segunda chamada à API)
    words = whisper_words if whisper_words else []
    if words:
        chunk_size = 4
        chunks = [words[i:i+chunk_size] for i in range(0, len(words), chunk_size)]
        for chunk in chunks:
            if not chunk:
                continue
            chunk_text = " ".join([w.word for w in chunk])
            start = chunk[0].start
            end = chunk[-1].end
            chunk_duration = end - start
            if chunk_duration <= 0:
                continue
            try:
                sub = TextClip(
                    chunk_text,
                    fontsize=65,
                    font="Arial-Bold",
                    color="white",
                    stroke_color="black",
                    stroke_width=3,
                    method="caption",
                    size=(SHORT_WIDTH - 100, None),
                    align="center"
                ).set_start(start).set_duration(chunk_duration).set_position(("center", 0.68), relative=True)
                layers.append(sub)
            except Exception:
                pass

    # 3. Gancho no topo (primeiros 4 segundos) — posição 0.08
    gancho = short_data.get("texto_gancho", "")
    if gancho:
        gancho_clip = _create_text_overlay(gancho, min(4.0, duration), position="top")
        layers.append(gancho_clip)

    # 4. CTA rotativo nos últimos 4 segundos — safe zone 0.84
    cta_text = _get_cta_text(duration)
    logger.info(f"  💬 CTA: '{cta_text}'")
    if duration > 6:
        cta_start = duration - 4
        cta_clip = _create_text_overlay(cta_text, 4.0, position="bottom")
        cta_clip = cta_clip.set_start(cta_start)
        layers.append(cta_clip)

    # Compor o Short — SEM ecrã preto no fim (loop infinito para retenção)
    # O YouTube interpreta ecrã preto como "fim de sessão" e perde retenção
    # Com corte directo, o espectador vê 1.5x o vídeo antes de perceber que repetiu
    final = CompositeVideoClip(layers, size=(SHORT_WIDTH, SHORT_HEIGHT))
    final = final.set_audio(final_audio.subclip(0, duration))
    final = final.set_duration(duration)
    final = final.fadein(0.3)
    # Sem fadeout — corte abrupto para loop perfeito

    logger.info(f"  A renderizar Short → {output_path} ({duration:.1f}s, loop directo)")
    logger.info("  (Short rendering em curso...)")

    try:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        final.write_videofile(
            str(output_path),
            fps=SHORT_FPS,
            codec="libx264",
            audio_codec="aac",
            bitrate="4000k",
            audio_bitrate="192k",
            threads=4,
            preset="medium",
            logger=None
        )
    finally:
        audio.close()
        final.close()

    size_mb = output_path.stat().st_size / (1024 * 1024)
    logger.info(f"  ✓ Short renderizado: {output_path} ({size_mb:.1f} MB)")
    return str(output_path)


# ─────────────────────────────────────────────
# 6e. UPLOAD DO SHORT
# ─────────────────────────────────────────────

def upload_short(youtube, short_data: dict, video_path: str, thumbnail_path: str) -> str:
    """
    Faz upload do Short para o YouTube com metadados otimizados.

    Returns:
        str: URL do Short publicado
    """
    logger.info("  Fase 6e: A fazer upload do Short para YouTube...")

    from googleapiclient.errors import HttpError

    titulo = short_data.get("titulo_short", "")
    if "#Shorts" not in titulo and "#shorts" not in titulo:
        titulo = titulo[:54] + " #Shorts"

    tags = short_data.get("hashtags", ["#Shorts"])
    if "#Shorts" not in tags and "#shorts" not in tags:
        tags.insert(0, "#Shorts")

    descricao = (
        f"{short_data.get('texto_gancho', '')}\n\n"
        f"{'  '.join(tags)}\n\n"
        "👆 Watch the full video on the channel!\n"
        "🔔 Subscribe for more Stoic wisdom\n\n"
        "💬 What Stoic lesson changed your life?"
    )

    request_body = {
        "snippet": {
            "title": titulo[:100],
            "description": descricao[:5000],
            "tags": [t.replace("#", "") for t in tags[:10]],
            "categoryId": "27",
            "defaultLanguage": "en"
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False
        }
    }

    try:
        from googleapiclient.http import MediaFileUpload as MFU
        media = MFU(video_path, mimetype="video/mp4", resumable=True)

        request = youtube.videos().insert(
            part="snippet,status",
            body=request_body,
            media_body=media
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                logger.info(f"  Upload Short: {int(status.progress() * 100)}%...")

        video_id = response["id"]

        try:
            from PIL import Image
            compressed_thumb = thumbnail_path.replace(".jpg", "_short_compressed.jpg")
            img = Image.open(thumbnail_path)
            img.save(compressed_thumb, "JPEG", quality=75, optimize=True)
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MFU(compressed_thumb, mimetype="image/jpeg")
            ).execute()
            logger.info("  ✓ Thumbnail do Short definida")
        except HttpError as e:
            logger.warning(f"  ⚠ Thumbnail do Short falhou: {e}")

        url = f"https://www.youtube.com/shorts/{video_id}"
        logger.info(f"  ✓ Short publicado → {url}")
        return url

    except HttpError as e:
        logger.error(f"  ❌ Erro HTTP no upload do Short: {e}")
        raise
    except Exception as e:
        logger.error(f"  ❌ Erro no upload do Short: {e}")
        raise


# ─────────────────────────────────────────────
# FUNÇÃO PRINCIPAL DO MÓDULO 6
# ─────────────────────────────────────────────

def generate_and_upload_short(
    script_data: dict,
    thumbnail_path: str,
    voice_id: str,
    youtube_service,
    temp_dir: str
) -> str:
    """
    Orquestra todo o fluxo do Módulo 6.

    Args:
        script_data: Guião completo do vídeo longo (Módulo 1)
        thumbnail_path: Path da thumbnail já gerada (reutiliza)
        voice_id: ID da voz ElevenLabs
        youtube_service: Serviço YouTube autenticado (do Módulo 5)
        temp_dir: Pasta temporária

    Returns:
        str: URL do Short publicado
    """
    logger.info("\n" + "=" * 60)
    logger.info("MÓDULO 6: GERADOR DE SHORTS")
    logger.info("=" * 60)

    short_dir = str(Path(temp_dir) / "short")
    Path(short_dir).mkdir(parents=True, exist_ok=True)

    short_data = select_best_scene(script_data)

    audio_path = generate_short_narration(
        short_data["texto_narrado"],
        short_dir,
        voice_id
    )

    # Fallback: vídeo único para todo o Short
    video_bg_path = download_vertical_video(
        short_data["palavra_chave_visual"],
        short_dir
    )

    # Multi-cena: vídeo diferente por parte (hook/teaching/practice/outro)
    scene_video_paths = None
    cenas_visuais = short_data.get("cenas_visuais", [])
    if len(cenas_visuais) == 4:
        logger.info("  🎬 Modo multi-cena activado (4 videos diferentes)")
        scene_video_paths = download_multi_scene_videos(
            cenas_visuais=cenas_visuais,
            fallback_keyword=short_data["palavra_chave_visual"],
            output_dir=short_dir
        )
    else:
        logger.info("  Info: Modo video unico (cenas_visuais nao disponiveis)")

    short_video_path = edit_short_video(
        audio_path=audio_path,
        video_bg_path=video_bg_path,
        short_data=short_data,
        output_dir=short_dir,
        scene_video_paths=scene_video_paths
    )

    short_url = upload_short(
        youtube=youtube_service,
        short_data=short_data,
        video_path=short_video_path,
        thumbnail_path=thumbnail_path
    )

    logger.info(f"✅ Módulo 6 completo: Short publicado → {short_url}")
    return short_url