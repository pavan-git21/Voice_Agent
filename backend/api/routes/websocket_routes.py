import base64
import json
import logging
import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/voice/{patient_id}")
async def voice_websocket(websocket: WebSocket, patient_id: str):
    """
    WebSocket endpoint for real-time voice interaction.

    Client sends:
        {
            "type": "audio",
            "data": "<base64-encoded audio>",
            "format": "webm",          // optional, default webm
            "session_id": "..."        // optional, will be generated if missing
        }

    OR for text-only mode (testing):
        {
            "type": "text",
            "data": "Book appointment with cardiologist",
            "session_id": "..."
        }

    Server responds:
        {
            "type": "response",
            "audio": "<base64-encoded mp3>",
            "text": "Your appointment is confirmed...",
            "language": "en",
            "latency": { "stt_ms": 110, "agent_ms": 190, "tts_ms": 95, "total_ms": 410 },
            "within_budget": true
        }
    """
    await websocket.accept()
    session_id = str(uuid.uuid4())
    logger.info(f"WebSocket opened: patient={patient_id} session={session_id}")

    app = websocket.app
    pipeline = _get_pipeline(websocket)

    try:
        while True:
            raw = await websocket.receive_text()
            payload = json.loads(raw)

            # Allow client to reuse session
            if payload.get("session_id"):
                session_id = payload["session_id"]

            msg_type = payload.get("type", "audio")

            if msg_type == "text":
                # Text-only mode (no STT/TTS, good for development)
                result = pipeline.process_text(
                    session_id=session_id,
                    patient_id=patient_id,
                    user_text=payload["data"]
                )
                await websocket.send_json({
                    "type": "response",
                    "text": result["response_text"],
                    "language": result["language"],
                    "agent_ms": result["agent_ms"],
                    "tool_calls": result["tool_calls"],
                    "session_id": session_id
                })

            elif msg_type == "audio":
                audio_bytes = base64.b64decode(payload["data"])
                audio_format = payload.get("format", "webm")

                result = pipeline.process_audio(
                    session_id=session_id,
                    patient_id=patient_id,
                    audio_bytes=audio_bytes,
                    audio_format=audio_format
                )

                audio_b64 = base64.b64encode(result["audio_bytes"]).decode()

                await websocket.send_json({
                    "type": "response",
                    "audio": audio_b64,
                    "audio_format": result["audio_format"],
                    "text": result["text_response"],
                    "user_text": result["user_text"],
                    "language": result["language"],
                    "latency": result["latency"],
                    "within_budget": result["within_budget"],
                    "tool_calls": result["tool_calls"],
                    "session_id": session_id
                })

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        logger.info(f"WebSocket closed: patient={patient_id} session={session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        try:
            await websocket.send_json({
                "type": "error",
                "message": "Internal error. Please try again."
            })
        except Exception:
            pass


def _get_pipeline(websocket: WebSocket):
    from pipeline import VoicePipeline
    app = websocket.app
    return VoicePipeline(
        session_store=app.state.session_store,
        patient_store=app.state.patient_store
    )
