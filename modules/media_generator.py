"""
MÓDULO 3: GERADOR DE MEDIA
Descarrega vídeos B-roll do Pexels e gera thumbnail com DALL-E 3.
"""

import os
import time
import logging
import requests
from pathlib import Path
from openai import OpenAI

logger = logging.getLogger(__name__)

PEXELS_BASE_URL = "https://api.pexels.com/videos"


def _search_pexels_video(keyword: str, api_key: str) -> str | None:
    """
    Pesquisa e descarrega um vídeo curto do Pexels.
    
    Returns:
        URL do ficheiro de vídeo ou None se não encontrado
    """
    headers = {"Authorization": api_key}
    params = {
        "query": keyword,
        "per_page": 5,
        "orientation": "landscape",
        "size": "medium"
    }

    try:
        response = requests.get(
            f"{PEXELS_BASE_URL}/search",
            headers=headers,
            params=params,
            timeout=15
        )
        response.raise_for_status()
        data = response.json()

        videos = data.get("videos", [])
        if not videos:
            logger.warning(f"  Nenhum vídeo encontrado no Pexels para: '{keyword}'")
            return None

        # Escolher o vídeo com duração entre 5-20 segundos
        for video in videos:
            duration = video.get("duration", 0)
            if 3 <= duration <= 25:
                # Pegar ficheiro HD ou SD
                video_files = video.get("video_files", [])
                # Ordenar por qualidade
                video_files.sort(key=lambda x: x.get("width", 0), reverse=True)
                
                for vf in video_files:
                    if vf.get("width", 0) >= 1280:  # Mínimo HD
                        return vf.get("link")
                
                # Se não tiver HD, pegar o melhor disponível
                if video_files:
                    return video_files[0].get("link")

        # Se nenhum tiver a duração ideal, pegar o primeiro
        first_video = videos[0]
        video_files = first_video.get("video_files", [])
        if video_files:
            video_files.sort(key=lambda x: x.get("width", 0), reverse=True)
            return video_files[0].get("link")

    except requests.exceptions.RequestException as e:
        logger.error(f"  Erro na pesquisa Pexels para '{keyword}': {e}")
        return None

    return None


def _download_file(url: str, output_path: Path) -> bool:
    """Descarrega um ficheiro de uma URL para o disco."""
    try:
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        return output_path.stat().st_size > 1000

    except Exception as e:
        logger.error(f"  Erro ao descarregar {url}: {e}")
        return False


def generate_thumbnail(prompt: str, output_dir: str) -> str:
    """
    Gera thumbnail usando DALL-E 3.

    Args:
        prompt: Descrição da imagem
        output_dir: Pasta de destino

    Returns:
        str: Caminho para thumbnail.jpg
    """
    logger.info("  A gerar thumbnail com DALL-E 3...")

    client = OpenAI()
    output_path = Path(output_dir) / "thumbnail.jpg"

    enhanced_prompt = f"""YouTube thumbnail, dark cinematic style, ultra high quality, 
dramatic lighting, {prompt}. 
Style: Dark, mysterious, philosophical, cinematic composition, 
professional YouTube thumbnail, 16:9 ratio, visually striking."""

    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=enhanced_prompt,
            size="1792x1024",
            quality="hd",
            n=1
        )

        image_url = response.data[0].url
        
        if _download_file(image_url, output_path):
            logger.info(f"  Thumbnail gerada: {output_path}")
            return str(output_path)
        else:
            raise ValueError("Falha ao descarregar a imagem gerada pelo DALL-E")

    except Exception as e:
        logger.error(f"  Erro ao gerar thumbnail: {e}")
        raise


def download_background_videos(cenas: list, output_dir: str) -> list[str]:
    """
    Descarrega vídeos de fundo do Pexels para cada cena.

    Args:
        cenas: Lista de cenas com 'palavra_chave_visual'
        output_dir: Pasta de destino

    Returns:
        list[str]: Lista de caminhos dos vídeos descarregados
    """
    logger.info(f"Fase 3: A descarregar {len(cenas)} vídeos de fundo do Pexels...")

    pexels_key = os.getenv("PEXELS_API_KEY")
    if not pexels_key:
        raise EnvironmentError("PEXELS_API_KEY não encontrada no ambiente")

    downloaded_videos = []
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    for i, cena in enumerate(cenas):
        keyword = cena.get("palavra_chave_visual", "dark cinematic landscape")
        output_path = Path(output_dir) / f"video_cena_{i+1:02d}.mp4"

        logger.info(f"  [{i+1}/{len(cenas)}] A pesquisar vídeo para: '{keyword}'")

        video_url = _search_pexels_video(keyword, pexels_key)

        if video_url:
            success = _download_file(video_url, output_path)
            if success:
                downloaded_videos.append(str(output_path))
                logger.info(f"  ✓ Vídeo {i+1} descarregado ({output_path.stat().st_size / 1024:.0f} KB)")
            else:
                # Fallback: tentar keyword genérica
                logger.warning(f"  ⚠ Falha ao descarregar. A tentar keyword genérica...")
                fallback_url = _search_pexels_video("dark cinematic", pexels_key)
                if fallback_url:
                    _download_file(fallback_url, output_path)
                    downloaded_videos.append(str(output_path))
        else:
            # Fallback genérico
            logger.warning(f"  ⚠ Sem resultados para '{keyword}'. A usar fallback...")
            fallback_url = _search_pexels_video("nature dark sky", pexels_key)
            if fallback_url and _download_file(fallback_url, output_path):
                downloaded_videos.append(str(output_path))
            else:
                logger.error(f"  ✗ Impossível obter vídeo para cena {i+1}")

        # Respeitar rate limit do Pexels
        time.sleep(0.5)

    if not downloaded_videos:
        raise RuntimeError("Nenhum vídeo de fundo foi descarregado com sucesso")

    logger.info(f"✅ Fase 3 (vídeos) completa: {len(downloaded_videos)}/{len(cenas)} vídeos descarregados")
    return downloaded_videos


def generate_all_media(script_data: dict, output_dir: str) -> dict:
    """
    Função principal do Módulo 3: coordena o download de vídeos e geração de thumbnail.

    Returns:
        dict com 'videos' (lista de paths) e 'thumbnail' (path)
    """
    logger.info("=" * 50)
    logger.info("MÓDULO 3: GERADOR DE MEDIA")
    logger.info("=" * 50)

    # 1. Descarregar vídeos de fundo
    videos = download_background_videos(script_data["cenas"], output_dir)

    # 2. Gerar thumbnail
    thumbnail_path = generate_thumbnail(
        script_data["prompt_thumbnail"],
        output_dir
    )

    logger.info(f"✅ Fase 3 completa: {len(videos)} vídeos + 1 thumbnail prontos")

    return {
        "videos": videos,
        "thumbnail": thumbnail_path
    }