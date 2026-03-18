"""
MÓDULO 3: GERADOR DE MEDIA v2.1 — The Silent Sage
===================================================
  - 3 clipes por cena (18 total)
  - Keywords variadas: wide / close up / cinematic dark
  - Fallback robusto com 3 tentativas
  - Thumbnail v2: Marco Aurélio mármore dourado + texto sobreposto PIL
"""

import os
import time
import logging
import requests
from pathlib import Path
from openai import OpenAI

logger = logging.getLogger(__name__)

PEXELS_BASE_URL = "https://api.pexels.com/videos"
CLIPS_PER_SCENE = 3

CLIP_MODIFIERS = [
    "",
    "close up",
    "cinematic dark"
]

# ── Thumbnail ──────────────────────────────────────────────────────────────────
THUMBNAIL_W = 1280
THUMBNAIL_H = 720

# Prompt base fixo — identidade visual do canal
THUMBNAIL_BASE_PROMPT = (
    "A hyperrealistic marble bust of Marcus Aurelius, Roman Emperor, "
    "dramatically lit with warm golden light from the left, deep black background, "
    "intricate stone texture, golden reflections on marble, chiaroscuro lighting, "
    "cinematic composition, professional YouTube thumbnail style, "
    "ultra high detail, no text, no watermark, 16:9 ratio"
)


# ─────────────────────────────────────────────────────────────────────────────
# PEXELS
# ─────────────────────────────────────────────────────────────────────────────

def _search_pexels_video(keyword, api_key, exclude_urls=None):
    if exclude_urls is None:
        exclude_urls = set()

    headers = {"Authorization": api_key}
    params  = {
        "query":       keyword,
        "per_page":    10,
        "orientation": "landscape",
        "size":        "medium"
    }

    try:
        response = requests.get(
            f"{PEXELS_BASE_URL}/search",
            headers=headers,
            params=params,
            timeout=15
        )
        response.raise_for_status()
        videos = response.json().get("videos", [])

        if not videos:
            return None

        for video in videos:
            video_files = video.get("video_files", [])
            video_files.sort(key=lambda x: x.get("width", 0), reverse=True)
            for vf in video_files:
                url = vf.get("link")
                if url and url not in exclude_urls and vf.get("width", 0) >= 1280:
                    return url

        for video in videos:
            for vf in video.get("video_files", []):
                url = vf.get("link")
                if url and url not in exclude_urls:
                    return url

    except requests.exceptions.RequestException as e:
        logger.error(f"  Pexels erro para '{keyword}': {e}")

    return None


def _download_file(url, output_path):
    try:
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return output_path.stat().st_size > 1000
    except Exception as e:
        logger.error(f"  Download falhou: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# THUMBNAIL v2 — Marco Aurélio + texto sobreposto
# ─────────────────────────────────────────────────────────────────────────────

def _add_text_overlay(image_path, title_text):
    """
    Adiciona texto sobreposto à thumbnail:
    - Gradiente escuro no lado esquerdo
    - Título em branco/dourado, grande e legível
    - "THE SILENT SAGE" em dourado no canto inferior esquerdo
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
        import numpy as np

        img = Image.open(image_path).convert("RGBA")
        img = img.resize((THUMBNAIL_W, THUMBNAIL_H), Image.LANCZOS)

        # Gradiente escuro no lado esquerdo (onde vai o texto)
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw_overlay = ImageDraw.Draw(overlay)

        for x in range(THUMBNAIL_W // 2):
            alpha = int(200 * (1 - x / (THUMBNAIL_W // 2)))
            draw_overlay.line([(x, 0), (x, THUMBNAIL_H)], fill=(0, 0, 0, alpha))

        img = Image.alpha_composite(img, overlay)
        draw = ImageDraw.Draw(img)

        # Limitar título a 2 linhas de ~20 caracteres
        words  = title_text.upper().split()
        lines  = []
        current = ""
        for word in words:
            test = (current + " " + word).strip()
            if len(test) <= 18:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
            if len(lines) == 2:
                break
        if current and len(lines) < 2:
            lines.append(current)
        lines = lines[:2]

        # Tentar carregar fonte — fallback para default
        font_title  = None
        font_brand  = None
        font_sizes  = [90, 80, 70]

        for size in font_sizes:
            try:
                font_title = ImageFont.truetype("arialbd.ttf", size)
                font_brand = ImageFont.truetype("arialbd.ttf", 32)
                break
            except Exception:
                pass

        if font_title is None:
            font_title = ImageFont.load_default()
            font_brand = ImageFont.load_default()

        # Desenhar título (branco com sombra dourada)
        GOLD  = (212, 175, 55, 255)
        WHITE = (255, 255, 255, 255)
        x_start = 40
        y_start = THUMBNAIL_H // 2 - (len(lines) * 100) // 2

        for i, line in enumerate(lines):
            y = y_start + i * 105
            # Sombra dourada
            draw.text((x_start + 3, y + 3), line, font=font_title, fill=GOLD)
            # Texto branco
            draw.text((x_start, y), line, font=font_title, fill=WHITE)

        # "THE SILENT SAGE" em dourado no canto inferior esquerdo
        draw.text((x_start, THUMBNAIL_H - 55), "THE SILENT SAGE", font=font_brand, fill=GOLD)

        # Linha dourada decorativa
        draw.rectangle([x_start, THUMBNAIL_H - 62, x_start + 220, THUMBNAIL_H - 58], fill=GOLD)

        # Guardar como JPEG
        final = img.convert("RGB")
        final.save(image_path, "JPEG", quality=95)
        logger.info("  Texto sobreposto na thumbnail OK")
        return True

    except Exception as e:
        logger.warning(f"  Texto na thumbnail falhou: {e}")
        return False


def generate_thumbnail(prompt, output_dir, title=""):
    """
    Gera thumbnail com DALL-E 3 (Marco Aurélio mármore dourado)
    e sobrepõe o título do vídeo com PIL.

    Args:
        prompt: prompt do tema (usado como contexto adicional, não substitui o base)
        output_dir: pasta de destino
        title: título do vídeo para sobrepor na imagem

    Returns:
        str: caminho para thumbnail.jpg
    """
    logger.info("  A gerar thumbnail (DALL-E 3 + texto PIL)...")
    client      = OpenAI()
    output_path = Path(output_dir) / "thumbnail.jpg"

    # Combinar prompt base fixo com contexto do tema
    theme_context = prompt[:100] if prompt else ""
    full_prompt   = f"{THUMBNAIL_BASE_PROMPT}. Theme context: {theme_context}"

    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=full_prompt,
            size="1792x1024",
            quality="hd",
            n=1
        )
        image_url = response.data[0].url
        if not _download_file(image_url, output_path):
            raise ValueError("Falha ao descarregar imagem DALL-E 3")

        # Redimensionar para 1280x720 e adicionar texto
        if title:
            _add_text_overlay(str(output_path), title)
        else:
            # Redimensionar apenas
            from PIL import Image
            img = Image.open(output_path)
            img = img.resize((THUMBNAIL_W, THUMBNAIL_H), Image.LANCZOS)
            img.save(str(output_path), "JPEG", quality=95)

        logger.info(f"  Thumbnail: {output_path}")
        return str(output_path)

    except Exception as e:
        logger.error(f"  Thumbnail falhou: {e}")
        raise


# ─────────────────────────────────────────────────────────────────────────────
# VÍDEOS DE FUNDO
# ─────────────────────────────────────────────────────────────────────────────

def download_background_videos(cenas, output_dir):
    total_clips = len(cenas) * CLIPS_PER_SCENE
    logger.info(f"  A descarregar {total_clips} clipes ({len(cenas)} cenas × {CLIPS_PER_SCENE})...")

    pexels_key = os.getenv("PEXELS_API_KEY")
    if not pexels_key:
        raise EnvironmentError("PEXELS_API_KEY não encontrada")

    downloaded = []
    used_urls  = set()
    clip_index = 0
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    for i, cena in enumerate(cenas):
        base_keyword = cena.get("palavra_chave_visual", "dark cinematic landscape")

        for j in range(CLIPS_PER_SCENE):
            clip_index += 1
            modifier = CLIP_MODIFIERS[j]
            keyword  = f"{base_keyword} {modifier}".strip()
            out_path = Path(output_dir) / f"video_{clip_index:02d}_cena{i+1}_clip{j+1}.mp4"

            logger.info(f"  [{clip_index}/{total_clips}] '{keyword}'")

            url = _search_pexels_video(keyword, pexels_key, used_urls)
            if not url and modifier:
                url = _search_pexels_video(base_keyword, pexels_key, used_urls)
            if not url:
                for fb in ["ancient rome dramatic", "dark stone texture", "misty forest dark"]:
                    url = _search_pexels_video(fb, pexels_key, used_urls)
                    if url:
                        break

            if url and _download_file(url, out_path):
                used_urls.add(url)
                downloaded.append(str(out_path))
                logger.info(f"    OK ({out_path.stat().st_size / 1024:.0f} KB)")
            else:
                logger.warning(f"    Falhou — clipe negro no editor")

            time.sleep(0.4)

    if not downloaded:
        raise RuntimeError("Nenhum clipe descarregado")

    logger.info(f"  {len(downloaded)}/{total_clips} clipes OK")
    return downloaded


# ─────────────────────────────────────────────────────────────────────────────
# COORDENADOR
# ─────────────────────────────────────────────────────────────────────────────

def generate_all_media(script_data, output_dir):
    logger.info("=" * 60)
    logger.info("  MÓDULO 3: GERADOR DE MEDIA v2.1")
    logger.info("=" * 60)

    videos    = download_background_videos(script_data["cenas"], output_dir)
    thumbnail = generate_thumbnail(
        prompt=script_data.get("prompt_thumbnail", ""),
        output_dir=output_dir,
        title=script_data.get("titulo", "")
    )

    logger.info(f"  {len(videos)} clipes + thumbnail prontos")
    return {"videos": videos, "thumbnail": thumbnail}