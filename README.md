# 2Care.ai — Real-Time Multilingual Voice AI Agent

A voice-powered clinical appointment booking system that communicates with patients in **English, Hindi, and Tamil** and manages appointments automatically through natural conversation.

---

## What It Does

Patients speak (or type) to the agent. The agent understands their intent, checks doctor availability, and books/reschedules/cancels appointments — all in real time, in the patient's language.

```
Patient speaks
    → Speech-to-Text (Whisper)         ~120ms
    → Language Detection               ~5ms
    → AI Agent + Tool Calls (GPT-4o)   ~200ms
    → Text-to-Speech (OpenAI TTS)      ~100ms
    → Audio response back to patient
                               Total:  < 450ms
```

---

## Project Structure

```
voice-ai-agent/
├── backend/
│   ├── main.py                          # FastAPI app entry point
│   ├── config.py                        # All config from env vars (no hardcoded keys)
│   ├── pipeline.py                      # Full voice pipeline with latency tracking
│   ├── latency_tracker.py               # Stage-level latency measurement + logging
│   ├── test_agent.py                    # Text-mode integration tests (no audio needed)
│   │
│   ├── agent/
│   │   ├── prompt/system_prompt.py      # Dynamic system prompt builder
│   │   ├── reasoning/reasoner.py        # LLM reasoning loop with tool orchestration
│   │   └── tools/tool_registry.py       # All tools the agent can call
│   │
│   ├── memory/
│   │   ├── session_memory/              # Redis-backed per-call context
│   │   └── persistent_memory/           # Long-term patient profiles
│   │
│   ├── services/
│   │   ├── speech_to_text/              # OpenAI Whisper
│   │   ├── text_to_speech/              # OpenAI TTS (language-aware voice)
│   │   └── language_detection/          # langdetect + Unicode fallback
│   │
│   ├── scheduler/
│   │   ├── appointment_engine/engine.py # Booking logic (isolated from agent)
│   │   └── campaign_scheduler.py        # Outbound reminders and follow-ups
│   │
│   └── api/
│       └── routes/
│           ├── appointment_routes.py    # REST endpoints
│           └── websocket_routes.py      # Real-time WebSocket for voice
│
├── frontend/
│   └── index.html                       # Browser-based voice/text testing UI
│
└── docker-compose.yml
```

---

## Setup

### 1. Clone and configure

```bash
cd backend
cp .env.example .env
# Add your OPENAI_API_KEY to .env
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run

```bash
uvicorn main:app --reload
```

Backend starts at `http://localhost:8000`.  
Open `frontend/index.html` in a browser to use the UI.

### 4. Docker (optional)

```bash
docker-compose up --build
```

---

## Test Without Audio

Run the text-mode test script to verify the agent works before connecting real audio:

```bash
cd backend
python test_agent.py
```

This runs several scenarios: English booking, Hindi query, conflict detection, rescheduling.

---

## API Reference

### REST

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/appointments/availability?doctor_name=&date=` | Check available slots |
| GET | `/api/appointments/doctors?specialty=` | Find doctors by specialty |
| POST | `/api/appointments/book` | Book an appointment |
| POST | `/api/appointments/reschedule` | Reschedule |
| POST | `/api/appointments/cancel` | Cancel |
| GET | `/api/appointments/patient/{patient_id}` | List patient appointments |

### WebSocket

Connect to: `ws://localhost:8000/ws/voice/{patient_id}`

**Send (audio):**
```json
{
  "type": "audio",
  "data": "<base64 encoded audio>",
  "format": "webm",
  "session_id": "optional-reuse-session"
}
```

**Send (text, for testing):**
```json
{
  "type": "text",
  "data": "Book a cardiologist appointment tomorrow"
}
```

**Receive:**
```json
{
  "type": "response",
  "text": "I found Dr. Sharma available tomorrow at 10:30 AM...",
  "audio": "<base64 mp3>",
  "language": "en",
  "latency": {
    "stt_ms": 110,
    "agent_ms": 185,
    "tts_ms": 92,
    "total_ms": 398
  },
  "within_budget": true,
  "tool_calls": ["find_doctors", "check_availability", "book_appointment"]
}
```

---

## Latency Targets

| Stage | Target | Notes |
|-------|--------|-------|
| Speech recognition | < 120ms | OpenAI Whisper API |
| Agent reasoning | < 200ms | GPT-4o with tool calls |
| Speech synthesis | < 100ms | OpenAI TTS-1 |
| **Total** | **< 450ms** | Measured and logged per request |

All stage timings are logged on every request. Budget breaches are flagged with warnings.

---

## Supported Languages

| Language | Example |
|----------|---------|
| English | "Book appointment with cardiologist tomorrow" |
| Hindi | "मुझे कल डॉक्टर से मिलना है" |
| Tamil | "நாளை மருத்துவரை பார்க்க வேண்டும்" |

Language is auto-detected from Whisper output and confirmed via langdetect. The agent responds in the same language the patient used.

---

## Agent Tools

The LLM can call these tools during a conversation:

| Tool | What it does |
|------|-------------|
| `find_doctors` | Find doctors by specialty |
| `check_availability` | Check open slots for a doctor/date |
| `book_appointment` | Create a confirmed booking |
| `cancel_appointment` | Cancel by appointment ID |
| `reschedule_appointment` | Move to new date/time |
| `get_patient_appointments` | List all active appointments |

---

## Outbound Campaign Mode

The system can proactively initiate calls for:
- Appointment reminders (24h before)
- Follow-up checkups (3 days after)
- Vaccination reminders

```python
from scheduler.campaign_scheduler import CampaignScheduler

scheduler = CampaignScheduler()
campaign = scheduler.schedule_reminder(
    patient_id="P001",
    appointment_id="ABC123",
    language="hi",
    hours_before=24
)
```

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | Your OpenAI API key | required |
| `LLM_MODEL` | Model for agent reasoning | `gpt-4o` |
| `WHISPER_MODEL` | Whisper model | `whisper-1` |
| `TTS_VOICE` | Default TTS voice | `alloy` |
| `REDIS_HOST` | Redis hostname | `localhost` |
| `REDIS_PORT` | Redis port | `6379` |
| `DATABASE_URL` | PostgreSQL/SQLite URL | SQLite |
