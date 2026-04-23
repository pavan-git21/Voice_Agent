"""
VoicePipeline: the main entry point that connects all components.

Flow:
    Audio bytes
      → SpeechToText        (target: 120ms)
      → LanguageDetection   (near-zero, piggybacks on Whisper)
      → AgentReasoner       (target: 200ms)
      → TextToSpeech        (target: 100ms)
      → Audio bytes

Total target: < 450ms
All stage timings are logged.
"""
import time
import logging
from typing import Optional

from services.speech_to_text.whisper_service import SpeechToTextService
from services.text_to_speech.tts_service import TextToSpeechService
from services.language_detection.detector import LanguageDetectionService
from agent.reasoning.reasoner import AgentReasoner
from memory.session_memory.session_store import SessionStore
from memory.persistent_memory.patient_store import PatientStore

logger = logging.getLogger(__name__)


class VoicePipeline:

    def __init__(self, session_store: SessionStore, patient_store: PatientStore):
        self.session_store = session_store
        self.patient_store = patient_store
        self.stt = SpeechToTextService()
        self.tts = TextToSpeechService()
        self.lang_detector = LanguageDetectionService()
        self.reasoner = AgentReasoner()

    def process_audio(
        self,
        session_id: str,
        patient_id: str,
        audio_bytes: bytes,
        audio_format: str = "webm"
    ) -> dict:
        """
        Full pipeline: audio → audio.

        Returns:
            {
                "audio_bytes": bytes,
                "text_response": str,
                "language": str,
                "latency": {
                    "stt_ms": float,
                    "agent_ms": float,
                    "tts_ms": float,
                    "total_ms": float
                },
                "within_budget": bool
            }
        """
        pipeline_start = time.perf_counter()

        # Load/create session and patient context
        session = self.session_store.get_or_create(session_id, patient_id)
        patient = self.patient_store.get_or_create(patient_id)

        # ── Stage 1: Speech to Text ──────────────────────────────────────────
        stt_result = self.stt.transcribe(
            audio_bytes=audio_bytes,
            language_hint=session.language,
            audio_format=audio_format
        )
        user_text = stt_result["text"]
        stt_ms = stt_result["duration_ms"]

        # ── Stage 2: Language Detection ──────────────────────────────────────
        language = self.lang_detector.detect(user_text, stt_result.get("language"))
        if language != session.language:
            logger.info(f"Language switched: {session.language} → {language}")
            session.language = language
            self.patient_store.update_language(patient_id, language)

        # ── Stage 3: Agent Reasoning ─────────────────────────────────────────
        session.add_turn("user", user_text)

        agent_result = self.reasoner.reason(
            user_text=user_text,
            session=session,
            patient=patient
        )
        response_text = agent_result["response_text"]
        agent_ms = agent_result["duration_ms"]

        session.add_turn("assistant", response_text)
        self.session_store.save(session)

        # ── Stage 4: Text to Speech ──────────────────────────────────────────
        tts_result = self.tts.synthesize(text=response_text, language=language)
        tts_ms = tts_result["duration_ms"]

        total_ms = (time.perf_counter() - pipeline_start) * 1000
        within_budget = total_ms < 450

        self._log_latency(stt_ms, agent_ms, tts_ms, total_ms, within_budget)

        return {
            "audio_bytes": tts_result["audio_bytes"],
            "audio_format": tts_result["format"],
            "text_response": response_text,
            "user_text": user_text,
            "language": language,
            "latency": {
                "stt_ms": round(stt_ms, 1),
                "agent_ms": round(agent_ms, 1),
                "tts_ms": round(tts_ms, 1),
                "total_ms": round(total_ms, 1)
            },
            "within_budget": within_budget,
            "tool_calls": agent_result.get("tool_calls_made", [])
        }

    def process_text(
        self,
        session_id: str,
        patient_id: str,
        user_text: str
    ) -> dict:
        """
        Text-only pipeline (skip STT/TTS) — useful for testing agent logic.
        """
        session = self.session_store.get_or_create(session_id, patient_id)
        patient = self.patient_store.get_or_create(patient_id)

        language = self.lang_detector.detect(user_text, session.language)
        session.language = language

        session.add_turn("user", user_text)

        agent_result = self.reasoner.reason(
            user_text=user_text,
            session=session,
            patient=patient
        )

        session.add_turn("assistant", agent_result["response_text"])
        self.session_store.save(session)

        return {
            "response_text": agent_result["response_text"],
            "language": language,
            "agent_ms": round(agent_result["duration_ms"], 1),
            "tool_calls": agent_result.get("tool_calls_made", [])
        }

    def _log_latency(self, stt_ms, agent_ms, tts_ms, total_ms, within_budget):
        status = "✓ WITHIN BUDGET" if within_budget else "✗ OVER BUDGET"
        logger.info(
            f"Pipeline latency | STT={stt_ms:.1f}ms | "
            f"Agent={agent_ms:.1f}ms | TTS={tts_ms:.1f}ms | "
            f"Total={total_ms:.1f}ms | {status}"
        )
