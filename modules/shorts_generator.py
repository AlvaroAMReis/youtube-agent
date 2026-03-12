"""
MÓDULO 6: GERADOR DE SHORTS
Cria automaticamente um YouTube Short a partir do guião do vídeo longo.

Fluxo:
  6a. Seleciona a cena mais impactante via GPT-4o
  6b. Gera narração curta (45-55s) via ElevenLabs
  6c. Descarrega vídeo vertical do Pexels (ou reformata existente)
  6d. Edita em formato 9:16 com texto de legenda animado
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
    e reescrever o texto para formato Short (45-55 segundos).

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

    system_prompt = """És um especialista em YouTube Shorts virais.
Analisas guiões e identificas o momento mais impactante para criar um Short.
Respondes SEMPRE e APENAS em formato JSON válido, sem texto extra nem markdown."""

    user_prompt = f"""Analisa este guião do canal sobre '{script_data.get("nicho", "filosofia")}':

Título do vídeo longo: {script_data['titulo']}

Cenas disponíveis:
{json.dumps(cenas_resumidas, ensure_ascii=False, indent=2)}

Cria um YouTube Short viral baseado na cena mais impactante. O Short deve:
- Estar SEMPRE em inglês (título, gancho, narração e CTA)
- Ter entre 30 e 40 segundos de narração
- Começar com um gancho FORTE nos primeiros 3 segundos que crie curiosidade ou choque
- Usar frases curtas e impactantes — máximo 10 palavras por frase
- Ter um ritmo rápido — cada ideia em 1-2 frases
- Incluir uma reviravolta ou facto surpreendente a meio do vídeo
- Referenciar filósofos Estoicos pelo nome (Marcus Aurelius, Epictetus, Seneca)
- Conectar a sabedoria antiga com problemas modernos (stress, ansiedade, trabalho, relações)
- Ser independente (funcionar sem ver o vídeo longo)
- Terminar com uma pergunta retórica poderosa antes do CTA
- Ter uma chamada à ação no final ("Follow for more" ou similar)
- O título deve ter números ou palavras de impacto como "NEVER", "ALWAYS", "SECRET", "TRUTH"
- As hashtags devem incluir #Stoicism #MarcusAurelius #Philosophy #Mindset #SelfImprovement

Devolve EXCLUSIVAMENTE este JSON:
{{
  "cena_escolhida": <número da cena>,
  "titulo_short": "Título do Short com #Shorts no final (máximo 60 chars)",
  "texto_gancho": "Frase de gancho brutal dos primeiros 3 segundos (máximo 12 palavras)",
  "texto_narrado": "Texto completo do Short para narrar (45-55 segundos ≈ 120-150 palavras)",
  "palavra_chave_visual": "keyword em inglês para vídeo de fundo vertical no Pexels",
  "hashtags": ["#Shorts", "#tag2", "#tag3", "#tag4", "#tag5"],
  "legenda_cta": "Texto curto para mostrar no final do vídeo (ex: 'Segue para mais 🔥')"
}}"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=1000,
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
                style=0.45,          # Mais expressivo para Shorts
                use_speaker_boost=True
            )
        )

        with open(output_path, "wb") as f:
            for chunk in audio_generator:
                if chunk:
                    f.write(chunk)

        # Validar duração
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

    # Tentar primeiro vídeo portrait/vertical
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

                    # Preferir vídeos já verticais
                    if orientation == "portrait" and h > w:
                        url = vf.get("link")
                        if url and _download_video_file(url, output_path):
                            logger.info(f"  ✓ Vídeo vertical descarregado ({w}x{h})")
                            return str(output_path)

                    # Fallback: landscape para converter
                    if orientation == "landscape" and w >= 1280:
                        url = vf.get("link")
                        if url and _download_video_file(url, output_path):
                            logger.info(f"  ✓ Vídeo landscape descarregado (será convertido para 9:16)")
                            return str(output_path)

        except Exception as e:
            logger.warning(f"  Erro na pesquisa Pexels ({orientation}): {e}")
            continue

        time.sleep(0.3)

    # Último fallback genérico
    logger.warning("  ⚠ Usando fallback genérico 'dark atmosphere'")
    fallback_params = {"query": "dark atmosphere cinematic", "per_page": 3, "orientation": "landscape"}
    try:
        r = requests.get("https://api.pexels.com/videos/search", headers=headers, params=fallback_params, timeout=15)
        r.raise_for_status()
        videos = r.json().get("videos", [])
        if videos:
            vf = sorted(videos[0].get("video_files", []), key=lambda x: x.get("width", 0), reverse=True)
            if vf and _download_video_file(vf[0]["link"], output_path):
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


# ─────────────────────────────────────────────
# 6d. EDITAR VÍDEO SHORT (9:16)
# ─────────────────────────────────────────────

def _make_vertical_clip(video_path: str, duration: float) -> VideoFileClip:
    clip = VideoFileClip(video_path, audio=False)

    # Escalar para preencher completamente o ecrã (sem barras pretas)
    scale_w = SHORT_WIDTH / clip.w
    scale_h = SHORT_HEIGHT / clip.h
    scale = max(scale_w, scale_h)

    new_w = int(clip.w * scale)
    new_h = int(clip.h * scale)
    scaled = clip.resize((new_w, new_h))

    # Crop ao centro
    cropped = crop(
        scaled,
        x_center=scaled.w / 2,
        y_center=scaled.h / 2,
        width=SHORT_WIDTH,
        height=SHORT_HEIGHT
    )

    # Loop ou cortar para duração exata
    if cropped.duration < duration:
        loops = int(duration / cropped.duration) + 1
        cropped = concatenate_videoclips([cropped] * loops)

    return cropped.subclip(0, min(duration, SHORT_MAX_DURATION)).set_fps(SHORT_FPS)


def _create_text_overlay(text: str, duration: float, position: str = "bottom") -> TextClip:
    """
    Cria uma legenda/texto animado para sobrepor no vídeo.
    """
    # Quebrar texto em linhas curtas (max 25 chars por linha)
    wrapped = textwrap.fill(text, width=22)

    y_pos = 0.75 if position == "bottom" else 0.10

    try:
        txt = TextClip(
            wrapped,
            fontsize=72,
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
        # Fallback se Arial-Bold não disponível
        txt = TextClip(
            wrapped,
            fontsize=65,
            color="white",
            stroke_color="black",
            stroke_width=2,
            method="caption",
            size=(SHORT_WIDTH - 80, None),
            align="center"
        ).set_duration(duration).set_position(("center", y_pos), relative=True)
        return txt


def edit_short_video(
    audio_path: str,
    video_bg_path: str,
    short_data: dict,
    output_dir: str
) -> str:
    """
    Monta o Short final: vídeo 9:16 + áudio + legendas + CTA.

    Returns:
        str: Caminho para short_final.mp4
    """
    logger.info("  Fase 6d: A editar Short (9:16)...")

    output_path = Path(output_dir) / "short_final.mp4"

    # Carregar áudio
    audio = AudioFileClip(audio_path)
    duration = min(audio.duration, SHORT_MAX_DURATION)
    logger.info(f"  Duração do Short: {duration:.1f}s")

    layers = []

    # 1. Vídeo de fundo vertical
    bg_clip = _make_vertical_clip(video_bg_path, duration)

    # Escurecer ligeiramente para melhor legibilidade
    from moviepy.video.fx.all import colorx
    bg_clip = colorx(bg_clip, 0.7)
    layers.append(bg_clip)

    # 2. Overlay escuro semi-transparente no terço inferior (para legibilidade)
    dark_bar = ColorClip(
        size=(SHORT_WIDTH, 500),
        color=(0, 0, 0),
        duration=duration
    ).set_opacity(0.5).set_position(("center", SHORT_HEIGHT - 550))
    layers.append(dark_bar)

    # 3. Texto do gancho (primeiros 4 segundos, no topo)
    gancho = short_data.get("texto_gancho", "")
    if gancho:
        gancho_clip = _create_text_overlay(gancho, min(4.0, duration), position="top")
        layers.append(gancho_clip)

    # 4. Legenda CTA (últimos 4 segundos, em baixo)
    cta_text = short_data.get("legenda_cta", "Segue para mais 🔥")
    if duration > 6:
        cta_start = duration - 4
        cta_clip = _create_text_overlay(cta_text, 4.0, position="bottom")
        cta_clip = cta_clip.set_start(cta_start)
        layers.append(cta_clip)

    # Compor todos os layers
    final = CompositeVideoClip(layers, size=(SHORT_WIDTH, SHORT_HEIGHT))
    final = final.set_audio(audio.subclip(0, duration))
    final = final.set_duration(duration)

    logger.info(f"  A renderizar Short → {output_path}")
    logger.info("  (Short rendering em curso...)")

    try:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        final.write_videofile(
            str(output_path),
            fps=SHORT_FPS,
            codec="libx264",
            audio_codec="aac",
            bitrate="2000k",
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

    # Título com #Shorts obrigatório
    titulo = short_data.get("titulo_short", "")
    if "#Shorts" not in titulo and "#shorts" not in titulo:
        titulo = titulo[:54] + " #Shorts"

    # Tags com #Shorts obrigatório
    tags = short_data.get("hashtags", ["#Shorts"])
    if "#Shorts" not in tags and "#shorts" not in tags:
        tags.insert(0, "#Shorts")

    # Descrição otimizada para Shorts
    descricao = (
        f"{short_data.get('texto_gancho', '')}\n\n"
        f"{'  '.join(tags)}\n\n"
        "👆 Vê o vídeo completo no canal!\n"
        "🔔 Subscreve para mais conteúdo diário"
    )

    request_body = {
        "snippet": {
            "title": titulo[:100],
            "description": descricao[:5000],
            "tags": [t.replace("#", "") for t in tags[:10]],
            "categoryId": "27",
            "defaultLanguage": "pt"
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

        # Thumbnail
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

    # Pasta separada para ficheiros do Short
    short_dir = str(Path(temp_dir) / "short")
    Path(short_dir).mkdir(parents=True, exist_ok=True)

    # 6a. Selecionar melhor cena e reescrever para formato Short
    short_data = select_best_scene(script_data)

    # 6b. Gerar narração
    audio_path = generate_short_narration(
        short_data["texto_narrado"],
        short_dir,
        voice_id
    )

    # 6c. Descarregar vídeo vertical
    video_bg_path = download_vertical_video(
        short_data["palavra_chave_visual"],
        short_dir
    )

    # 6d. Editar vídeo Short
    short_video_path = edit_short_video(
        audio_path=audio_path,
        video_bg_path=video_bg_path,
        short_data=short_data,
        output_dir=short_dir
    )

    # 6e. Upload
    short_url = upload_short(
        youtube=youtube_service,
        short_data=short_data,
        video_path=short_video_path,
        thumbnail_path=thumbnail_path
    )

    logger.info(f"✅ Módulo 6 completo: Short publicado → {short_url}")
    return short_url