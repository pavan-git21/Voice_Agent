import time
import asyncio
import logging
import tempfile
import os

logger = logging.getLogger(__name__)

class TextToSpeechService:

    VOICE_MAP = {
        "en": "en-US-AriaNeural",
        "hi": "hi-IN-SwaraNeural",
        "ta": "ta-IN-PallaviNeural",
    }

    def synthesize(self, text: str, language: str = "en") -> dict:
        start = time.perf_counter()
        voice = self.VOICE_MAP.get(language, "en-US-AriaNeural")

        async def _synthesize():
            import edge_tts
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                tmp_path = f.name
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(tmp_path)
            with open(tmp_path, "rb") as f:
                audio = f.read()
            os.unlink(tmp_path)
            return audio

        audio_bytes = asyncio.run(_synthesize())
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(f"TTS completed in {elapsed_ms:.1f}ms | lang={language} | voice={voice}")

        return {
            "audio_bytes": audio_bytes,
            "format": "mp3",
            "duration_ms": elapsed_ms
        }