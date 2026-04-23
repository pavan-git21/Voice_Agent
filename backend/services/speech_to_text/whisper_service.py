import io
import time
import logging
import tempfile
import os

logger = logging.getLogger(__name__)

class SpeechToTextService:

    LANGUAGE_CODES = {"en": "en", "hi": "hi", "ta": "ta"}

    def __init__(self):
        self._model = None

    def _get_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel
            # Downloads once, runs locally after that
            self._model = WhisperModel("base", device="cpu", compute_type="int8")
            logger.info("Whisper model loaded locally")
        return self._model

    def transcribe(self, audio_bytes: bytes, language_hint=None, audio_format="webm"):
        start = time.perf_counter()
        model = self._get_model()

        with tempfile.NamedTemporaryFile(suffix=f".{audio_format}", delete=False) as f:
            f.write(audio_bytes)
            tmp_path = f.name

        try:
            segments, info = model.transcribe(tmp_path, beam_size=5)
            text = " ".join(s.text for s in segments).strip()
            detected_lang = info.language
        finally:
            os.unlink(tmp_path)

        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(f"STT completed in {elapsed_ms:.1f}ms | lang={detected_lang} | text={text[:60]}")

        return {
            "text": text,
            "language": detected_lang,
            "duration_ms": elapsed_ms
        }