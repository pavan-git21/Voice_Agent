from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional

from scheduler.appointment_engine.engine import AppointmentEngine

router = APIRouter()
_engine = AppointmentEngine()


# ── Request models ────────────────────────────────────────────────────────────

class BookRequest(BaseModel):
    patient_id: str
    doctor_name: str
    date: str           # YYYY-MM-DD
    time_slot: str      # HH:MM
    specialty: Optional[str] = ""


class RescheduleRequest(BaseModel):
    patient_id: str
    appointment_id: str
    new_date: str
    new_time: str


class CancelRequest(BaseModel):
    patient_id: str
    appointment_id: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/availability")
def check_availability(doctor_name: str, date: str):
    slots = _engine.get_available_slots(doctor_name, date)
    return {"doctor": doctor_name, "date": date, "available_slots": slots}


@router.get("/doctors")
def find_doctors(specialty: str):
    doctors = _engine.find_doctors_by_specialty(specialty)
    return {"specialty": specialty, "doctors": doctors}


@router.post("/book")
def book_appointment(body: BookRequest):
    result = _engine.book_appointment(
        patient_id=body.patient_id,
        doctor_name=body.doctor_name,
        date=body.date,
        time_slot=body.time_slot,
        specialty=body.specialty or ""
    )
    if not result["success"]:
        raise HTTPException(status_code=409, detail=result)
    return result


@router.post("/reschedule")
def reschedule_appointment(body: RescheduleRequest):
    result = _engine.reschedule_appointment(
        appointment_id=body.appointment_id,
        patient_id=body.patient_id,
        new_date=body.new_date,
        new_time=body.new_time
    )
    if not result["success"]:
        raise HTTPException(status_code=409, detail=result)
    return result


@router.post("/cancel")
def cancel_appointment(body: CancelRequest):
    result = _engine.cancel_appointment(
        appointment_id=body.appointment_id,
        patient_id=body.patient_id
    )
    if not result["success"]:
        raise HTTPException(status_code=409, detail=result)
    return result


@router.get("/patient/{patient_id}")
def get_patient_appointments(patient_id: str):
    appointments = _engine.get_patient_appointments(patient_id)
    return {"patient_id": patient_id, "appointments": appointments}
