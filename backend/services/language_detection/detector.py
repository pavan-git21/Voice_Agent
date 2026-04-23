import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

SUPPORTED = {"en", "hi", "ta"}


class LanguageDetectionService:
    """
    Detects language from transcribed text.

    Strategy (in order of preference):
    1. If Whisper already returned a language during STT, trust it.
    2. Try langdetect (fast, offline).
    3. Fall back to 'en' if detection fails.

    This keeps the langdetect library as an optional dependency.
    """

    def detect(self, text: str, whisper_language: Optional[str] = None) -> str:
        """
        Returns one of: 'en', 'hi', 'ta'.
        """
        start = time.perf_counter()

        # If STT already told us the language, trust it
        if whisper_language and whisper_language in SUPPORTED:
            logger.info(f"Language from Whisper: {whisper_language}")
            return whisper_language

        detected = self._detect_via_library(text)
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(f"Language detection: {detected} in {elapsed_ms:.1f}ms")
        return detected

    def _detect_via_library(self, text: str) -> str:
        try:
            from langdetect import detect as ld_detect, DetectorFactory
            # make detection deterministic
            DetectorFactory.seed = 42
            lang = ld_detect(text)
            if lang in SUPPORTED:
                return lang
            # langdetect may return 'zh-cn' etc — fall through to heuristics
        except Exception as e:
            logger.debug(f"langdetect failed: {e}")

        return self._heuristic_detect(text)

    def _heuristic_detect(self, text: str) -> str:
        """
        Simple Unicode-range heuristic as last resort.
        Tamil script: U+0B80–U+0BFF
        Devanagari (Hindi): U+0900–U+097F
        """
        tamil_count = sum(1 for c in text if '\u0B80' <= c <= '\u0BFF')
        devanagari_count = sum(1 for c in text if '\u0900' <= c <= '\u097F')

        if tamil_count > 2:
            return "ta"
        if devanagari_count > 2:
            return "hi"
        return "en"
