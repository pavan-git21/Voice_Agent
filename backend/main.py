import os
import time
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from api.routes.appointment_routes import router as appointment_router
from api.routes.websocket_routes import router as ws_router
from memory.session_memory.session_store import SessionStore
from memory.persistent_memory.patient_store import PatientStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Voice AI Agent backend...")
    app.state.session_store = SessionStore()
    app.state.patient_store = PatientStore()
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="2Care.ai Voice AI Agent",
    description="Real-Time Multilingual Voice AI Agent for clinical appointment booking",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(appointment_router, prefix="/api/appointments", tags=["appointments"])
app.include_router(ws_router, prefix="/ws", tags=["websocket"])


@app.get("/")
def health_check():
    return {
        "status": "running",
        "service": "2Care.ai Voice AI Agent",
        "version": "1.0.0"
    }


@app.get("/health")
def detailed_health():
    return {
        "status": "ok",
        "timestamp": time.time(),
        "components": {
            "backend": "up",
            "session_memory": "up",
            "patient_store": "up"
        }
    }
