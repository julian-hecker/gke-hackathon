"""
Live messaging runtime and bridge for ADK agent.

Usage:
```python
live_events, live_request_queue = await start_agent_session(...)

async def handle_agent_event(event: AgentEvent):
    await websocket.send_json(...)

try:
    async with asyncio.TaskGroup() as tg:
        agent_coroutine = agent_to_client_messaging(handle_agent_event, live_events)
        agent_task = tg.create_task(agent_coroutine)

        websocket_loop_coroutine = ... # sends messages from client to agent
        # should run in parallel with agent_task for live bidirectional audio
        websocket_task = tg.create_task(websocket_loop_coroutine)
except Exception as ex:
    print(f"TaskGroup caught: {ex}")
finally:
    live_request_queue.close()
    websocket.close()
```
"""


from typing import AsyncGenerator, Awaitable, Callable, Literal

from google.adk.agents.run_config import RunConfig  # , StreamingMode
from google.adk.events import Event
from google.adk.runners import InMemoryRunner  # , Runner
from google.adk.agents.live_request_queue import LiveRequestQueue

# from google.adk.sessions import InMemorySessionService
from google.genai import types
from google.genai.types import Part, Blob
from pydantic import BaseModel, Field

from adk_agents.agents.search_agent.agent import root_agent
# from adk_agents.runtime.factory import build_agent_from_profile, make_run_config_for_profile

# AudioOutCallback = Callable[[bytes], None]
# TextOutCallback = Callable[[str, bool], None]

# @dataclass
# class SessionHandle:
#     runner: Runner
#     run_task: asyncio.Task
#     live_request_queue: LiveRequestQueue


# class SessionService:

#     def __init__(self):
#         self._sessions: dict[str, SessionHandle] = {}
#         self._session_service = InMemorySessionService()

#     async def create_or_attach(self, session_id: str, tenant_profile: dict, on_audio: AudioOutCallback):
#         if session_id in self._sessions:
#             return self._sessions[session_id]

#         agent = build_agent_from_profile(tenant_profile)
#         run_config = make_run_config_for_profile(tenant_profile)

#         runner = Runner(app_name=f"{tenant_profile['slug']}_runner", agent=agent, session_service=self._session_service)

#         live_events, live_request_queue = await runner.run_live(run_config=run_config)

#         run_task = asyncio.create_task()
#         self._sessions[session_id] = SessionHandle(runner, run_task, live_request_queue=live_request_queue)


APP_NAME = "THE VOICE AGENT"

LiveEvents = AsyncGenerator[Event, None]


# TODO: Make this *dynamic*
async def start_agent_session(user_id: str, session_id: str) -> tuple[LiveEvents, LiveRequestQueue]:
    """Starts an agent session"""

    # Create a Runner
    runner = InMemoryRunner(
        app_name=APP_NAME,
        agent=root_agent,
    )

    # Create a Session
    session = await runner.session_service.create_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
    )

    run_config = RunConfig(
        response_modalities=["AUDIO"],
        session_resumption=types.SessionResumptionConfig(),
    )

    live_request_queue = LiveRequestQueue()

    live_events = runner.run_live(
        session=session,
        live_request_queue=live_request_queue,
        run_config=run_config,
    )
    return live_events, live_request_queue


class AgentInterruptedEvent(BaseModel):
    type: Literal["interrupted"] = "interrupted"


class AgentTurnCompleteEvent(BaseModel):
    type: Literal["complete"] = "complete"


class AgentDataEvent(BaseModel):
    payload: bytes = Field(description="Output PCM bytes (16-bit, 24kHz)")
    type: Literal["data"] = "data"


AgentEvent = AgentInterruptedEvent | AgentTurnCompleteEvent | AgentDataEvent
OnAgentEvent = Callable[[AgentEvent], Awaitable[None]]


async def agent_to_client_messaging(
    on_agent_event: OnAgentEvent, live_events: LiveEvents
) -> None:
    """
    Agent to client communication.
    Sends events to the client via the on_event callback.
    To be used in an asyncio.TaskGroup in parallel with webhook loop.

    Args:
        on_agent_event: Async callback invoked per AgentEvent.
        live_events: Async generator of ADK Event objects to send to client.
    """
    async for event in live_events:
        message: AgentEvent

        if event.turn_complete:
            message = AgentTurnCompleteEvent()
            await on_agent_event(message)
            continue

        if event.interrupted:
            message = AgentInterruptedEvent()
            await on_agent_event(message)
            continue

        # TODO: Look into parts, there's lots of types of parts
        part: Part = event.content and event.content.parts and event.content.parts[0]  # pyright: ignore[reportAssignmentType]

        if not part:
            print("Agent sent event without part")
            continue

        is_audio = (
            part.inline_data
            and part.inline_data.mime_type
            and part.inline_data.mime_type.startswith("audio/pcm")
        )

        if not is_audio:
            print("Agent sent part without audio")
            continue

        audio_data = part.inline_data and part.inline_data.data
        if audio_data:
            # payload = base64.b64encode(audio_data).decode("ascii")
            message = AgentDataEvent(payload=audio_data)
            await on_agent_event(message)
            continue


def send_pcm_to_agent(pcm_audio: bytes, live_request_queue: LiveRequestQueue):
    """
    Sends audio data to the agent.

    Should be nested inside the websocket loop, which runs alongside agent_to_client_messaging.

    Args:
        pcm_audio: bytes - Input PCM bytes (16-bit, 16kHz)
        live_request_queue: LiveRequestQueue - The live request queue to send audio to
    """
    live_request_queue.send_realtime(Blob(data=pcm_audio, mime_type="audio/pcm"))
