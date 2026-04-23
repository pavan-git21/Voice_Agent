import uuid
import time
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory data store (replace with PostgreSQL in production)
# ---------------------------------------------------------------------------

_appointments: Dict[str, Dict] = {}

_doctor_schedule: Dict[str, Dict[str, List[str]]] = {
    "Dr. Sharma": {
        "cardiologist": True,
        "slots": {
            "2026-04-23": ["09:00", "10:30", "14:00", "16:30"],
            "2026-04-24": ["09:00", "11:00", "15:00"],
            "2026-04-25": ["10:00", "12:00", "14:00", "17:00"],
        }
    },
    "Dr. Gupta": {
        "cardiologist": True,
        "slots": {
            "2026-04-23": ["08:30", "11:00", "13:30"],
            "2026-04-24": ["09:30", "12:00", "16:00"],
            "2026-04-25": ["08:00", "10:00", "13:00", "15:30"],
        }
    },
    "Dr. Rajesh": {
        "dermatologist": True,
        "slots": {
            "2026-04-23": ["09:00", "11:30", "14:30"],
            "2026-04-24": ["10:00", "12:30", "15:00"],
            "2026-04-25": ["09:00", "11:00", "14:00"],
        }
    },
    "Dr. Mehra": {
        "orthopedic": True,
        "slots": {
            "2026-04-23": ["10:00", "12:00", "15:00"],
            "2026-04-24": ["09:00", "11:30", "14:00", "16:30"],
            "2026-04-25": ["09:30", "13:00", "15:00"],
        }
    },
}

_SPECIALTY_TO_DOCTORS: Dict[str, List[str]] = {
    "cardiologist": ["Dr. Sharma", "Dr. Gupta"],
    "dermatologist": ["Dr. Rajesh"],
    "orthopedic": ["Dr. Mehra"],
    "general": list(_doctor_schedule.keys()),
}


class AppointmentEngine:
    """
    Pure scheduling logic. No agent/LLM code here.
    Validates, books, cancels, and reschedules appointments.
    """

    # --- Availability ---

    def get_available_slots(self, doctor_name: str, date: str) -> List[str]:
        """Return available (unbooked) slots for a doctor on a date."""
        doc = _doctor_schedule.get(doctor_name)
        if not doc:
            return []

        all_slots = doc["slots"].get(date, [])
        booked = self._get_booked_slots(doctor_name, date)
        available = [s for s in all_slots if s not in booked]
        return available

    def find_doctors_by_specialty(self, specialty: str) -> List[str]:
        specialty_lower = specialty.lower().rstrip("s")  # 'cardiologists' -> 'cardiologist'
        for key, docs in _SPECIALTY_TO_DOCTORS.items():
            if key.startswith(specialty_lower) or specialty_lower.startswith(key):
                return docs
        return list(_doctor_schedule.keys())  # fallback: all doctors

    def _get_booked_slots(self, doctor_name: str, date: str) -> List[str]:
        booked = []
        for appt in _appointments.values():
            if (appt["doctor"] == doctor_name
                    and appt["date"] == date
                    and appt["status"] in ("confirmed", "rescheduled")):
                booked.append(appt["time"])
        return booked

    # --- Booking ---

    def book_appointment(
        self,
        patient_id: str,
        doctor_name: str,
        date: str,
        time_slot: str,
        specialty: str = ""
    ) -> Dict[str, Any]:
        """
        Book a new appointment.
        Returns result dict with success flag and appointment data or error.
        """
        # Validate doctor exists
        if doctor_name not in _doctor_schedule:
            return {"success": False, "error": "Doctor not found", "code": "INVALID_DOCTOR"}

        # Validate time not in past
        try:
            appt_dt = datetime.strptime(f"{date} {time_slot}", "%Y-%m-%d %H:%M")
            if appt_dt < datetime.now():
                return {"success": False, "error": "Cannot book in the past", "code": "PAST_TIME"}
        except ValueError:
            return {"success": False, "error": "Invalid date/time format", "code": "INVALID_DATETIME"}

        # Check slot availability
        available = self.get_available_slots(doctor_name, date)
        if time_slot not in available:
            alternatives = available[:3] if available else []
            return {
                "success": False,
                "error": "Slot not available",
                "code": "SLOT_TAKEN",
                "alternatives": alternatives
            }

        appointment_id = str(uuid.uuid4())[:8].upper()
        appointment = {
            "id": appointment_id,
            "patient_id": patient_id,
            "doctor": doctor_name,
            "specialty": specialty,
            "date": date,
            "time": time_slot,
            "status": "confirmed",
            "created_at": time.time()
        }
        _appointments[appointment_id] = appointment

        logger.info(f"Appointment booked: {appointment_id} | {patient_id} -> {doctor_name} @ {date} {time_slot}")
        return {"success": True, "appointment": appointment}

    # --- Cancellation ---

    def cancel_appointment(self, appointment_id: str, patient_id: str) -> Dict[str, Any]:
        appt = _appointments.get(appointment_id)
        if not appt:
            return {"success": False, "error": "Appointment not found", "code": "NOT_FOUND"}
        if appt["patient_id"] != patient_id:
            return {"success": False, "error": "Not authorized", "code": "UNAUTHORIZED"}
        if appt["status"] == "cancelled":
            return {"success": False, "error": "Already cancelled", "code": "ALREADY_CANCELLED"}

        appt["status"] = "cancelled"
        appt["cancelled_at"] = time.time()
        logger.info(f"Appointment cancelled: {appointment_id}")
        return {"success": True, "appointment": appt}

    # --- Rescheduling ---

    def reschedule_appointment(
        self,
        appointment_id: str,
        patient_id: str,
        new_date: str,
        new_time: str
    ) -> Dict[str, Any]:
        appt = _appointments.get(appointment_id)
        if not appt:
            return {"success": False, "error": "Appointment not found", "code": "NOT_FOUND"}
        if appt["patient_id"] != patient_id:
            return {"success": False, "error": "Not authorized", "code": "UNAUTHORIZED"}
        if appt["status"] == "cancelled":
            return {"success": False, "error": "Cannot reschedule a cancelled appointment", "code": "CANCELLED"}

        # Validate new slot
        try:
            new_dt = datetime.strptime(f"{new_date} {new_time}", "%Y-%m-%d %H:%M")
            if new_dt < datetime.now():
                return {"success": False, "error": "Cannot reschedule to the past", "code": "PAST_TIME"}
        except ValueError:
            return {"success": False, "error": "Invalid date/time format", "code": "INVALID_DATETIME"}

        available = self.get_available_slots(appt["doctor"], new_date)
        if new_time not in available:
            alternatives = available[:3] if available else []
            return {
                "success": False,
                "error": "New slot not available",
                "code": "SLOT_TAKEN",
                "alternatives": alternatives
            }

        old_date, old_time = appt["date"], appt["time"]
        appt["date"] = new_date
        appt["time"] = new_time
        appt["status"] = "rescheduled"
        appt["rescheduled_at"] = time.time()

        logger.info(f"Appointment rescheduled: {appointment_id} from {old_date} {old_time} -> {new_date} {new_time}")
        return {"success": True, "appointment": appt}

    # --- Lookup ---

    def get_patient_appointments(self, patient_id: str) -> List[Dict]:
        return [
            a for a in _appointments.values()
            if a["patient_id"] == patient_id and a["status"] != "cancelled"
        ]

    def get_appointment(self, appointment_id: str) -> Optional[Dict]:
        return _appointments.get(appointment_id)
