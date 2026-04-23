"""
Integration test for the agent pipeline using text input.
Run this to verify the system works before wiring up real audio.

Usage:
    cd backend
    python test_agent.py
"""
import os
import sys
import json
import time

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

# Minimal env setup for testing without .env file
os.environ.setdefault("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", ""))


def run_test(label: str, session_id: str, patient_id: str, text: str, pipeline):
    print(f"\n{'─'*60}")
    print(f"[{label}]")
    print(f"Patient says: {text}")
    result = pipeline.process_text(
        session_id=session_id,
        patient_id=patient_id,
        user_text=text
    )
    print(f"Agent says:   {result['response_text']}")
    print(f"Language:     {result['language']}")
    print(f"Agent time:   {result['agent_ms']}ms")
    if result["tool_calls"]:
        print(f"Tools called: {', '.join(result['tool_calls'])}")
    return result


def main():
    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: Set OPENAI_API_KEY before running tests.")
        sys.exit(1)

    from memory.session_memory.session_store import SessionStore
    from memory.persistent_memory.patient_store import PatientStore
    from pipeline import VoicePipeline

    session_store = SessionStore()
    patient_store = PatientStore()
    pipeline = VoicePipeline(session_store=session_store, patient_store=patient_store)

    SESSION = "test-session-001"
    PATIENT = "P001"

    print("\n" + "="*60)
    print("2Care.ai Voice Agent — Integration Tests")
    print("="*60)

    # Test 1: Book appointment (English)
    run_test(
        "English: Book appointment",
        SESSION, PATIENT,
        "I want to see a cardiologist tomorrow",
        pipeline
    )

    time.sleep(1)

    # Test 2: Multi-turn — follow up with time
    run_test(
        "English: Multi-turn — pick a slot",
        SESSION, PATIENT,
        "Let's go with Dr. Sharma at 10:30",
        pipeline
    )

    time.sleep(1)

    # Test 3: Hindi query
    run_test(
        "Hindi: Book appointment",
        "test-session-002", "P002",
        "मुझे कल डॉक्टर से मिलना है",
        pipeline
    )

    time.sleep(1)

    # Test 4: Conflict scenario
    run_test(
        "English: Conflict detection",
        "test-session-003", "P003",
        "Book Dr. Sharma on 2026-04-23 at 09:00",
        pipeline
    )

    time.sleep(1)

    # Test 5: Check existing appointments
    run_test(
        "English: View appointments",
        "test-session-004", "P001",
        "What appointments do I have?",
        pipeline
    )

    print("\n" + "="*60)
    print("Tests complete.")
    print("="*60)


if __name__ == "__main__":
    main()
