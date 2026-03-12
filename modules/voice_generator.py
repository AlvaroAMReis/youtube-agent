"""
MÓDULO 2: GERADOR DE VOZ
Usa a API ElevenLabs para converter o guião em narração MP3.
"""

import os
import logging
from pathlib import Path
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings

logger = logging.getLogger(__name__)


def generate_narration(cenas: list, output_dir: str, voice_id: str) -> str:
    """
    Converte o texto narrado de todas as cenas em áudio MP3 via ElevenLabs.

    Args:
        cenas: Lista de cenas do guião (cada uma com 'texto_narrado')
        output_dir: Pasta onde guardar o ficheiro de áudio
        voice_id: ID da voz ElevenLabs a usar

    Returns:
        str: Caminho absoluto para o ficheiro narração.mp3

    Raises:
        Exception: Para erros de comunicação com a API
    """
    logger.info("Fase 2: A gerar narração com ElevenLabs...")

    # Juntar todo o texto numa única narração fluida
    full_narration = ""
    for i, cena in enumerate(cenas):
        texto = cena.get("texto_narrado", "").strip()
        if texto:
            full_narration += texto + "\n\n"
            logger.debug(f"  Cena {i+1}: {len(texto)} caracteres")

    if not full_narration.strip():
        raise ValueError("Nenhum texto para narrar encontrado nas cenas")

    logger.info(f"  Total de texto: {len(full_narration)} caracteres")

    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise EnvironmentError("ELEVENLABS_API_KEY não encontrada no ambiente")

    client = ElevenLabs(api_key=api_key)

    output_path = Path(output_dir) / "narração.mp3"

    try:
        logger.info(f"  A enviar texto para ElevenLabs (voz: {voice_id})...")

        audio_generator = client.text_to_speech.convert(
            voice_id=voice_id,
            text=full_narration,
            model_id="eleven_multilingual_v2",
            voice_settings=VoiceSettings(
                stability=0.6,
                similarity_boost=0.85,
                style=0.3,
                use_speaker_boost=True
            )
        )

        # Guardar o stream de áudio no ficheiro
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            for chunk in audio_generator:
                if chunk:
                    f.write(chunk)

        file_size = output_path.stat().st_size
        if file_size < 1000:
            raise ValueError(f"Ficheiro de áudio suspeito: apenas {file_size} bytes")

        logger.info(f"✅ Fase 2 completa: Narração gerada → {output_path} ({file_size / 1024:.1f} KB)")
        return str(output_path)

    except Exception as e:
        logger.error(f"❌ Fase 2 FALHOU: Erro na API ElevenLabs: {e}")
        raise