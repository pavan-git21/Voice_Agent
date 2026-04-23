"""
Tool definitions that the LLM agent can invoke.
Each tool wraps the appointment engine — the agent never calls the engine directly.
"""
import logging
from typing import Dict, Any, List

from scheduler.appointment_engine.engine import AppointmentEngine

logger = logging.getLogger(__name__)

_engine = AppointmentEngine()


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def check_availability(doctor_name: str, date: str) -> Dict[str, Any]:
    """
    Check available time slots for a specific doctor on a date.
    """
    slots = _engine.get_available_slots(doctor_name, date)
    if not slots:
        return {
            "available": False,
            "doctor": doctor_name,
            "date": date,
            "slots": []
        }
    return {
        "available": True,
        "doctor": doctor_name,
        "date": date,
        "slots": slots
    }


def find_doctors(specialty: str) -> Dict[str, Any]:
    """
    Find doctors by specialty (e.g., cardiologist, dermatologist).
    """
    doctors = _engine.find_doctors_by_specialty(specialty)
    return {
        "specialty": specialty,
        "doctors": doctors,
        "count": len(doctors)
    }


def book_appointment(
    patient_id: str,
    doctor_name: str,
    date: str,
    time_slot: str,
    specialty: str = ""
) -> Dict[str, Any]:
    """
    Book an appointment for a patient.
    """
    result = _engine.book_appointment(
        patient_id=patient_id,
        doctor_name=doctor_name,
        date=date,
        time_slot=time_slot,
        specialty=specialty
    )
    return result


def cancel_appointment(appointment_id: str, patient_id: str) -> Dict[str, Any]:
    """
    Cancel an existing appointment.
    """
    return _engine.cancel_appointment(appointment_id=appointment_id, patient_id=patient_id)


def reschedule_appointment(
    appointment_id: str,
    patient_id: str,
    new_date: str,
    new_time: str
) -> Dict[str, Any]:
    """
    Reschedule an existing appointment to a new date/time.
    """
    return _engine.reschedule_appointment(
        appointment_id=appointment_id,
        patient_id=patient_id,
        new_date=new_date,
        new_time=new_time
    )


def get_patient_appointments(patient_id: str) -> Dict[str, Any]:
    """
    Get all active appointments for a patient.
    """
    appointments = _engine.get_patient_appointments(patient_id)
    return {
        "patient_id": patient_id,
        "appointments": appointments,
        "count": len(appointments)
    }


# ---------------------------------------------------------------------------
# Tool registry for the LLM
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "check_availability",
            "description": "Check available appointment slots for a specific doctor on a given date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "doctor_name": {"type": "string", "description": "Full name of the doctor, e.g. 'Dr. Sharma'"},
                    "date": {"type": "string", "description": "Date in YYYY-MM-DD format"}
                },
                "required": ["doctor_name", "date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_doctors",
            "description": "Find available doctors by medical specialty (e.g. cardiologist, dermatologist).",
            "parameters": {
                "type": "object",
                "properties": {
                    "specialty": {"type": "string", "description": "Medical specialty requested by patient"}
                },
                "required": ["specialty"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "book_appointment",
            "description": "Book a clinical appointment for a patient.",
            "parameters": {
                "type": "object",
                "properties": {
                    "patient_id": {"type": "string"},
                    "doctor_name": {"type": "string"},
                    "date": {"type": "string", "description": "YYYY-MM-DD"},
                    "time_slot": {"type": "string", "description": "HH:MM, 24-hour format"},
                    "specialty": {"type": "string"}
                },
                "required": ["patient_id", "doctor_name", "date", "time_slot"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_appointment",
            "description": "Cancel an existing appointment by ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "appointment_id": {"type": "string"},
                    "patient_id": {"type": "string"}
                },
                "required": ["appointment_id", "patient_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "reschedule_appointment",
            "description": "Move an existing appointment to a new date and time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "appointment_id": {"type": "string"},
                    "patient_id": {"type": "string"},
                    "new_date": {"type": "string", "description": "YYYY-MM-DD"},
                    "new_time": {"type": "string", "description": "HH:MM"}
                },
                "required": ["appointment_id", "patient_id", "new_date", "new_time"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_patient_appointments",
            "description": "Retrieve all active appointments for a patient.",
            "parameters": {
                "type": "object",
                "properties": {
                    "patient_id": {"type": "string"}
                },
                "required": ["patient_id"]
            }
        }
    }
]

TOOL_REGISTRY = {
    "check_availability": check_availability,
    "find_doctors": find_doctors,
    "book_appointment": book_appointment,
    "cancel_appointment": cancel_appointment,
    "reschedule_appointment": reschedule_appointment,
    "get_patient_appointments": get_patient_appointments,
}
