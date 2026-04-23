import json
import time
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class PatientProfile:
    patient_id: str
    name: str = ""
    phone: str = ""
    preferred_language: str = "en"
    preferred_hospital: str = ""
    past_appointments: List[Dict] = field(default_factory=list)
    preferred_doctors: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def record_appointment(self, appointment: Dict):
        self.past_appointments.append({**appointment, "recorded_at": time.time()})
        # keep last 20 only
        if len(self.past_appointments) > 20:
            self.past_appointments = self.past_appointments[-20:]
        self.updated_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PatientProfile":
        return cls(**data)


class PatientStore:
    """
    Long-term patient memory.
    Backed by Redis with JSON-file fallback for demo purposes.
    In production this would be a PostgreSQL table.
    """

    def __init__(self):
        self._local: Dict[str, PatientProfile] = {}
        self._redis = None
        self._try_connect_redis()
        self._seed_demo_data()

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
            logger.info("PatientStore: connected to Redis")
        except Exception as e:
            logger.warning(f"PatientStore: Redis unavailable ({e}), using in-memory store")

    def _seed_demo_data(self):
        demo_patients = [
            PatientProfile(
                patient_id="P001",
                name="Rahul Sharma",
                phone="+91-9876543210",
                preferred_language="hi",
                preferred_hospital="Apollo",
                preferred_doctors=["Dr. Gupta", "Dr. Sharma"],
                past_appointments=[
                    {"doctor": "Dr. Gupta", "specialty": "cardiologist", "date": "2025-03-15", "status": "completed"}
                ]
            ),
            PatientProfile(
                patient_id="P002",
                name="Priya Venkatesh",
                phone="+91-9123456789",
                preferred_language="ta",
                preferred_hospital="Fortis",
                preferred_doctors=["Dr. Rajesh"],
                past_appointments=[]
            ),
            PatientProfile(
                patient_id="P003",
                name="John Doe",
                phone="+91-9000000001",
                preferred_language="en",
                preferred_hospital="Max",
                past_appointments=[]
            ),
        ]
        for p in demo_patients:
            self._local[p.patient_id] = p

    def get(self, patient_id: str) -> Optional[PatientProfile]:
        if self._redis:
            try:
                raw = self._redis.get(f"patient:{patient_id}")
                if raw:
                    return PatientProfile.from_dict(json.loads(raw))
            except Exception as e:
                logger.error(f"Redis patient get error: {e}")
        return self._local.get(patient_id)

    def save(self, profile: PatientProfile):
        profile.updated_at = time.time()
        if self._redis:
            try:
                self._redis.set(f"patient:{profile.patient_id}", json.dumps(profile.to_dict()))
                return
            except Exception as e:
                logger.error(f"Redis patient save error: {e}")
        self._local[profile.patient_id] = profile

    def get_or_create(self, patient_id: str, name: str = "", phone: str = "") -> PatientProfile:
        existing = self.get(patient_id)
        if existing:
            return existing
        profile = PatientProfile(patient_id=patient_id, name=name, phone=phone)
        self.save(profile)
        return profile

    def update_language(self, patient_id: str, language: str):
        profile = self.get_or_create(patient_id)
        profile.preferred_language = language
        self.save(profile)
