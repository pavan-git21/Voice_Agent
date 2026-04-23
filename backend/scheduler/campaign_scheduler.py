"""
Outbound Campaign Mode
Proactively initiates calls for reminders and follow-ups.
In production this would integrate with Twilio or similar.
"""
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from scheduler.appointment_engine.engine import AppointmentEngine, _appointments

logger = logging.getLogger(__name__)


@dataclass
class Campaign:
    campaign_id: str
    campaign_type: str          # reminder | followup | vaccination
    patient_id: str
    appointment_id: Optional[str]
    scheduled_at: float
    language: str = "en"
    status: str = "pending"     # pending | sent | failed
    message_template: str = ""


_campaigns: Dict[str, Campaign] = {}
_engine = AppointmentEngine()


TEMPLATES = {
    "reminder": {
        "en": "Hello {name}, this is a reminder about your appointment with {doctor} tomorrow at {time}. Would you like to confirm or reschedule?",
        "hi": "नमस्ते {name}, यह आपके कल {time} बजे {doctor} के साथ अपॉइंटमेंट की याद दिलाने के लिए है। क्या आप पुष्टि करना या पुनर्निर्धारित करना चाहते हैं?",
        "ta": "வணக்கம் {name}, நாளை {time} மணிக்கு {doctor} உடன் உங்கள் சந்திப்பை நினைவூட்டுகிறோம். உறுதிப்படுத்த அல்லது மாற்ற விரும்புகிறீர்களா?"
    },
    "followup": {
        "en": "Hello {name}, this is a follow-up call after your recent visit with {doctor}. How are you feeling? Do you need to book a follow-up appointment?",
        "hi": "नमस्ते {name}, {doctor} के साथ आपकी हाल की यात्रा के बाद यह फॉलो-अप कॉल है। आप कैसा महसूस कर रहे हैं?",
        "ta": "வணக்கம் {name}, {doctor} உடனான உங்கள் சமீபத்திய வருகைக்கு பிறகு இது ஒரு பின்தொடர் அழைப்பு."
    },
    "vaccination": {
        "en": "Hello {name}, you are due for your vaccination. Would you like to book an appointment?",
        "hi": "नमस्ते {name}, आपका टीकाकरण का समय आ गया है। क्या आप अपॉइंटमेंट बुक करना चाहेंगे?",
        "ta": "வணக்கம் {name}, உங்கள் தடுப்பூசி நேரம் வந்துவிட்டது. சந்திப்பை பதிவு செய்ய விரும்புகிறீர்களா?"
    }
}


class CampaignScheduler:

    def schedule_reminder(
        self,
        patient_id: str,
        appointment_id: str,
        language: str = "en",
        hours_before: int = 24
    ) -> Campaign:
        """Schedule a reminder call X hours before appointment."""
        appt = _appointments.get(appointment_id)
        if not appt:
            raise ValueError(f"Appointment {appointment_id} not found")

        appt_dt = datetime.strptime(f"{appt['date']} {appt['time']}", "%Y-%m-%d %H:%M")
        call_at = appt_dt - timedelta(hours=hours_before)

        import uuid
        campaign = Campaign(
            campaign_id=str(uuid.uuid4())[:8],
            campaign_type="reminder",
            patient_id=patient_id,
            appointment_id=appointment_id,
            scheduled_at=call_at.timestamp(),
            language=language,
            message_template=TEMPLATES["reminder"].get(language, TEMPLATES["reminder"]["en"])
        )
        _campaigns[campaign.campaign_id] = campaign
        logger.info(f"Reminder scheduled: {campaign.campaign_id} for patient {patient_id} at {call_at}")
        return campaign

    def schedule_followup(
        self,
        patient_id: str,
        appointment_id: str,
        language: str = "en",
        days_after: int = 3
    ) -> Campaign:
        """Schedule a follow-up call after appointment."""
        appt = _appointments.get(appointment_id)
        if not appt:
            raise ValueError(f"Appointment {appointment_id} not found")

        appt_dt = datetime.strptime(f"{appt['date']} {appt['time']}", "%Y-%m-%d %H:%M")
        call_at = appt_dt + timedelta(days=days_after)

        import uuid
        campaign = Campaign(
            campaign_id=str(uuid.uuid4())[:8],
            campaign_type="followup",
            patient_id=patient_id,
            appointment_id=appointment_id,
            scheduled_at=call_at.timestamp(),
            language=language,
            message_template=TEMPLATES["followup"].get(language, TEMPLATES["followup"]["en"])
        )
        _campaigns[campaign.campaign_id] = campaign
        logger.info(f"Follow-up scheduled: {campaign.campaign_id} for patient {patient_id}")
        return campaign

    def get_due_campaigns(self) -> List[Campaign]:
        """Return campaigns that are due to be executed now."""
        now = time.time()
        return [
            c for c in _campaigns.values()
            if c.status == "pending" and c.scheduled_at <= now
        ]

    def mark_sent(self, campaign_id: str):
        if campaign_id in _campaigns:
            _campaigns[campaign_id].status = "sent"

    def get_opening_message(self, campaign: Campaign, patient_name: str, doctor_name: str, appt_time: str) -> str:
        template = campaign.message_template
        return template.format(name=patient_name, doctor=doctor_name, time=appt_time)
