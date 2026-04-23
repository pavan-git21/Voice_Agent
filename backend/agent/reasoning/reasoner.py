import json
import time
import logging
from typing import Optional, Dict, Any

from agent.tools.tool_registry import TOOL_DEFINITIONS, TOOL_REGISTRY
from agent.prompt.system_prompt import build_system_prompt
from memory.session_memory.session_store import ConversationState
from memory.persistent_memory.patient_store import PatientProfile

logger = logging.getLogger(__name__)

MAX_TOOL_ITERATIONS = 5  # prevent infinite loops


class AgentReasoner:
    """
    Core reasoning loop.
    Given transcribed text + session state + patient profile,
    calls the LLM, handles tool calls, and returns a final text response.
    """

    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI
            from dotenv import load_dotenv
            import os
            load_dotenv(override=True)
            api_key = os.getenv("OPENAI_API_KEY", "")
            if not api_key:
                raise RuntimeError("OPENAI_API_KEY not set in environment")
            self._client = OpenAI(
                api_key=api_key,
                base_url="https://api.groq.com/openai/v1"
            )
        return self._client

    def reason(
        self,
        user_text: str,
        session: ConversationState,
        patient: PatientProfile
    ) -> Dict[str, Any]:
        """
        Run the agent reasoning loop.

        Returns:
            {
                "response_text": str,
                "duration_ms": float,
                "tool_calls_made": list[str]
            }
        """
        start = time.perf_counter()

        system_prompt = build_system_prompt(
            language=session.language,
            patient_id=patient.patient_id,
            patient_name=patient.name,
            preferred_hospital=patient.preferred_hospital,
            past_doctors=patient.preferred_doctors,
            conversation_history=session.history
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text}
        ]

        tool_calls_made = []
        response_text = ""

        client = self._get_client()

        for iteration in range(MAX_TOOL_ITERATIONS):
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto",
                parallel_tool_calls=False,   # add this line
                temperature=0.3,
                max_tokens=400
            )

            message = response.choices[0].message

            # If no tool calls, we have a final response
            if not message.tool_calls:
                response_text = message.content or ""
                break

            # Handle tool calls
            messages.append(message)

            for tool_call in message.tool_calls:
                fn_name = tool_call.function.name
                fn_args = json.loads(tool_call.function.arguments)

                logger.info(f"Agent calling tool: {fn_name}({fn_args})")
                tool_calls_made.append(fn_name)

                if fn_name not in TOOL_REGISTRY:
                    tool_result = {"error": f"Unknown tool: {fn_name}"}
                else:
                    try:
                        tool_result = TOOL_REGISTRY[fn_name](**fn_args)
                    except Exception as e:
                        logger.error(f"Tool {fn_name} raised: {e}")
                        tool_result = {"error": str(e)}

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(tool_result)
                })
        else:
            logger.warning("Agent hit max tool iterations without final response")
            response_text = self._safe_fallback(session.language)

        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            f"Agent reasoning: {elapsed_ms:.1f}ms | "
            f"tools={tool_calls_made} | "
            f"response_len={len(response_text)}"
        )

        return {
            "response_text": response_text,
            "duration_ms": elapsed_ms,
            "tool_calls_made": tool_calls_made
        }

    def _safe_fallback(self, language: str) -> str:
        fallbacks = {
            "en": "I'm having trouble processing that request. Could you please repeat?",
            "hi": "मुझे आपका अनुरोध समझने में कठिनाई हो रही है। क्या आप दोबारा कह सकते हैं?",
            "ta": "உங்கள் கோரிக்கையை புரிந்துகொள்வதில் சிக்கல் உள்ளது. மீண்டும் சொல்ல முடியுமா?"
        }
        return fallbacks.get(language, fallbacks["en"])