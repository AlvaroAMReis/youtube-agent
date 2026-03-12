"""
MÓDULO 5: UPLOADER YOUTUBE
Usa a YouTube Data API v3 com OAuth2 para fazer upload do vídeo e thumbnail.
"""

import os
import time
import logging
from pathlib import Path

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

# Permissões necessárias
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube"
]

TOKEN_FILE = "token.json"


def _get_authenticated_service(client_secrets_file: str):
    """
    Autentica com OAuth2 e retorna o serviço YouTube API.
    Guarda o token para evitar re-autenticação em execuções futuras.
    """
    credentials = None

    # Carregar token existente
    if Path(TOKEN_FILE).exists():
        try:
            credentials = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
            logger.info("  Token OAuth2 carregado do ficheiro.")
        except Exception as e:
            logger.warning(f"  Token inválido, será regenerado: {e}")
            credentials = None

    # Renovar ou criar novo token
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            logger.info("  A renovar token OAuth2 expirado...")
            credentials.refresh(Request())
        else:
            logger.info("  A iniciar fluxo OAuth2 (abre o browser)...")
            flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, SCOPES)
            credentials = flow.run_local_server(port=0)

        # Guardar token para uso futuro
        with open(TOKEN_FILE, "w") as token_file:
            token_file.write(credentials.to_json())
        logger.info(f"  Token OAuth2 guardado em '{TOKEN_FILE}'")

    return build("youtube", "v3", credentials=credentials)


def _upload_video_with_retry(youtube, video_path: str, metadata: dict, max_retries: int = 3) -> str:
    """
    Faz upload do vídeo com retry automático em caso de falha.
    
    Returns:
        str: ID do vídeo no YouTube
    """
    request_body = {
        "snippet": {
            "title": metadata["titulo"][:100],  # Máximo 100 chars
            "description": metadata["descricao"],
            "tags": metadata["tags"][:500],  # Máximo 500 tags
            "categoryId": "27",  # Educação
            "defaultLanguage": "pt",
            "defaultAudioLanguage": "pt"
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False
        }
    }

    media = MediaFileUpload(
        video_path,
        mimetype="video/mp4",
        resumable=True,
        chunksize=50 * 1024 * 1024  # Chunks de 50MB
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=request_body,
        media_body=media
    )

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"  A fazer upload do vídeo (tentativa {attempt}/{max_retries})...")
            logger.info(f"  Tamanho: {Path(video_path).stat().st_size / (1024*1024):.1f} MB")

            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    logger.info(f"  Upload: {progress}% concluído...")

            video_id = response["id"]
            logger.info(f"  ✓ Upload concluído! ID do vídeo: {video_id}")
            return video_id

        except HttpError as e:
            if e.resp.status in [500, 502, 503, 504] and attempt < max_retries:
                wait_time = 2 ** attempt
                logger.warning(f"  Erro HTTP {e.resp.status}. A aguardar {wait_time}s antes de retry...")
                time.sleep(wait_time)
            else:
                logger.error(f"  Erro HTTP fatal no upload: {e}")
                raise

        except Exception as e:
            if attempt < max_retries:
                logger.warning(f"  Erro no upload (tentativa {attempt}): {e}. A tentar novamente...")
                time.sleep(5)
            else:
                raise

    raise RuntimeError(f"Upload falhou após {max_retries} tentativas")


def _upload_thumbnail(youtube, video_id: str, thumbnail_path: str) -> bool:
    """Faz upload da thumbnail para o vídeo."""
    try:
        logger.info(f"  A fazer upload da thumbnail para vídeo {video_id}...")

        # Comprimir thumbnail se for maior que 2MB
        from PIL import Image
        import io
        img = Image.open(thumbnail_path)
        compressed_path = thumbnail_path.replace(".jpg", "_compressed.jpg")
        img.save(compressed_path, "JPEG", quality=75, optimize=True)

        youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(compressed_path, mimetype="image/jpeg")
        ).execute()

        logger.info("  ✓ Thumbnail definida com sucesso")
        return True

    except HttpError as e:
        logger.error(f"  ❌ Erro ao fazer upload da thumbnail: {e}")
        return False

def upload_to_youtube(video_path: str, thumbnail_path: str, script_data: dict, client_secrets_file: str) -> str:
    logger.info("Fase 5: A autenticar com YouTube API...")

    if not Path(client_secrets_file).exists():
        raise FileNotFoundError(f"Ficheiro não encontrado: '{client_secrets_file}'")

    youtube = _get_authenticated_service(client_secrets_file)
    logger.info("  ✓ Autenticação bem-sucedida")

    video_id = _upload_video_with_retry(youtube, video_path, script_data)
    _upload_thumbnail(youtube, video_id, thumbnail_path)

    url = f"https://www.youtube.com/watch?v={video_id}"
    logger.info(f"✅ Fase 5 completa: {url}")
    return url