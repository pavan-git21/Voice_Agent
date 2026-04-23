"""
Latency tracker — logs per-request pipeline timings and flags budget breaches.
"""
import time
import logging
from dataclasses import dataclass, field
from typing import Dict, Optional

logger = logging.getLogger("latency")

BUDGET = {
    "stt":   120,   # ms
    "agent": 200,   # ms
    "tts":   100,   # ms
    "total": 450,   # ms
}


@dataclass
class LatencyReport:
    session_id: str
    stt_ms:   float = 0.0
    agent_ms: float = 0.0
    tts_ms:   float = 0.0
    total_ms: float = 0.0
    breaches: list = field(default_factory=list)

    @property
    def within_budget(self) -> bool:
        return self.total_ms < BUDGET["total"]

    def check_budgets(self):
        checks = {
            "stt":   self.stt_ms,
            "agent": self.agent_ms,
            "tts":   self.tts_ms,
            "total": self.total_ms,
        }
        for stage, actual in checks.items():
            budget = BUDGET[stage]
            if actual > budget:
                self.breaches.append({
                    "stage": stage,
                    "actual_ms": round(actual, 1),
                    "budget_ms": budget,
                    "over_by_ms": round(actual - budget, 1)
                })

    def log(self):
        self.check_budgets()
        status = "✓ OK" if self.within_budget else "✗ OVER BUDGET"
        logger.info(
            f"[{self.session_id}] {status} | "
            f"STT={self.stt_ms:.0f}ms/{BUDGET['stt']}ms  "
            f"Agent={self.agent_ms:.0f}ms/{BUDGET['agent']}ms  "
            f"TTS={self.tts_ms:.0f}ms/{BUDGET['tts']}ms  "
            f"Total={self.total_ms:.0f}ms/{BUDGET['total']}ms"
        )
        if self.breaches:
            for b in self.breaches:
                logger.warning(
                    f"  ⚠ {b['stage'].upper()} over budget by {b['over_by_ms']}ms"
                )

    def to_dict(self) -> Dict:
        return {
            "stt_ms":   round(self.stt_ms, 1),
            "agent_ms": round(self.agent_ms, 1),
            "tts_ms":   round(self.tts_ms, 1),
            "total_ms": round(self.total_ms, 1),
            "within_budget": self.within_budget,
            "breaches": self.breaches,
            "budgets": BUDGET
        }


class StageTimer:
    """Context manager for timing individual pipeline stages."""

    def __init__(self, name: str):
        self.name = name
        self.elapsed_ms: float = 0.0
        self._start: float = 0.0

    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, *_):
        self.elapsed_ms = (time.perf_counter() - self._start) * 1000
