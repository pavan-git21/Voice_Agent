import json
import time
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)

# TTL for session data: 30 minutes
SESSION_TTL = 60 * 30


@dataclass
class ConversationState:
    session_id: str
    patient_id: Optional[str] = None
    language: str = "en"
    pending_intent: Optional[str] = None
    pending_doctor: Optional[str] = None
    pending_date: Optional[str] = None
    pending_time: Optional[str] = None
    turn_count: int = 0
    history: list = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def add_turn(self, role: str, content: str):
        self.history.append({"role": role, "content": content, "ts": time.time()})
        self.updated_at = time.time()
        self.turn_count += 1

    def clear_pending(self):
        self.pending_intent = None
        self.pending_doctor = None
        self.pending_date = None
        self.pending_time = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationState":
        return cls(**data)


class SessionStore:
    """
    Stores conversation state per session.
    Tries Redis first; falls back to in-process dict if Redis is unavailable.
    """

    def __init__(self):
        self._local: Dict[str, ConversationState] = {}
        self._redis = None
        self._try_connect_redis()

    def _try_connect_redis(self):
        try:
            import redis
            from config import settings
            r = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                decode_responses=True,
                socket_connect_timeout=2
            )
            r.ping()
            self._redis = r
            logger.info("SessionStore: connected to Redis")
        except Exception as e:
            logger.warning(f"SessionStore: Redis unavailable ({e}), using in-memory fallback")

    def get(self, session_id: str) -> Optional[ConversationState]:
        if self._redis:
            try:
                raw = self._redis.get(f"session:{session_id}")
                if raw:
                    return ConversationState.from_dict(json.loads(raw))
            except Exception as e:
                logger.error(f"Redis get error: {e}")

        return self._local.get(session_id)

    def save(self, state: ConversationState):
        if self._redis:
            try:
                self._redis.setex(
                    f"session:{state.session_id}",
                    SESSION_TTL,
                    json.dumps(state.to_dict())
                )
                return
            except Exception as e:
                logger.error(f"Redis save error: {e}")

        self._local[state.session_id] = state

    def get_or_create(self, session_id: str, patient_id: Optional[str] = None) -> ConversationState:
        existing = self.get(session_id)
        if existing:
            return existing
        state = ConversationState(session_id=session_id, patient_id=patient_id)
        self.save(state)
        return state

    def delete(self, session_id: str):
        if self._redis:
            try:
                self._redis.delete(f"session:{session_id}")
            except Exception:
                pass
        self._local.pop(session_id, None)
