import asyncio
import base64
from typing import Annotated

from fastapi import APIRouter, Form, Request, Response, WebSocket
from fastapi.params import Depends
from fastapi.responses import HTMLResponse
from twilio.twiml.voice_response import Connect, Stream, VoiceResponse

from adk_agents.runtime.live_messaging import (
    AgentEvent,
    agent_to_client_messaging,
    send_pcm_to_agent,
    start_agent_session,
)

from voice_bridge.entities.twilio import (
    TwilioStreamCallbackPayload,
    TwilioVoiceWebhookPayload,
)
from voice_bridge.utils.audio import (
    adk_pcm24k_to_twilio_ulaw8k,
    twilio_ulaw8k_to_adk_pcm16k,
)
from voice_bridge.utils.security import validate_twilio
from voice_bridge.utils.logging import logger


twilio_path = "/twilio"
callback_path = "/callback"
stream_path = "/stream"
router = APIRouter(prefix=twilio_path, tags=["Twilio Webhooks"])


@router.post("/connect", dependencies=[Depends(validate_twilio)])
def create_call(req: Request, payload: Annotated[TwilioVoiceWebhookPayload, Form()]):
    """Generate TwiML to connect a call to a Twilio Media Stream"""

    host = req.url.hostname
    ws_protocol = "wss" if req.url.is_secure else "ws"
    http_protocol = "https" if req.url.is_secure else "http"
    ws_url = f"{ws_protocol}://{host}{twilio_path}{stream_path}"
    callback_url = f"{http_protocol}://{host}{twilio_path}{callback_path}"

    stream = Stream(url=ws_url, statusCallback=callback_url)
    stream.parameter(name="from_phone", value=payload.From)
    stream.parameter(name="to_phone", value=payload.To)
    connect = Connect()
    connect.append(stream)
    response = VoiceResponse()
    response.append(connect)

    logger.info(response)

    return HTMLResponse(content=str(response), media_type="application/xml")


@router.post(callback_path, status_code=204, dependencies=[Depends(validate_twilio)])
def twilio_callback(payload: Annotated[TwilioStreamCallbackPayload, Form()]):
    """Handle Twilio status callbacks"""

    logger.info(payload)

    return Response(status_code=204)


# TODO: Figure out how to validate Twilio signature in a WebSocket
# https://www.twilio.com/docs/usage/webhooks/webhooks-security
# Headers({'host': 'amazing-sincere-grouse.ngrok-free.app', 'user-agent': 'Twilio.TmeWs/1.0', 'connection': 'Upgrade', 'sec-websocket-key': '', 'sec-websocket-version': '13', 'upgrade': 'websocket', 'x-forwarded-for': '98.84.178.199', 'x-forwarded-host': 'amazing-sincere-grouse.ngrok-free.app', 'x-forwarded-proto': 'https', 'x-twilio-signature': '', 'accept-encoding': 'gzip'})


@router.websocket(stream_path)
async def twilio_websocket(ws: WebSocket):
    """Handle Twilio Media Stream WebSocket connection"""

    await ws.accept()
    await ws.receive_json()  # throw away `connected` event

    start_event = await ws.receive_json()
    assert start_event["event"] == "start"

    # account_sid = start_event["start"]["accountSid"]
    call_sid = start_event["start"]["callSid"]
    # encoding = start_event["start"]["mediaFormat"]["encoding"]
    # sample_rate = start_event["start"]["mediaFormat"]["sampleRate"]
    # channels = start_event["start"]["mediaFormat"]["channels"]
    from_phone = start_event["start"]["customParameters"]["from_phone"]
    # to_phone = start_event["start"]["customParameters"]["to_phone"]
    stream_sid = start_event["streamSid"]

    live_events, live_request_queue = await start_agent_session(from_phone, call_sid)

    async def handle_agent_event(event: AgentEvent):
        """Handle outgoing AgentEvent to Twilio WebSocket"""
        logger.debug(event)
        if event.type == "complete":
            # mark twilio buffer
            # https://www.twilio.com/docs/voice/media-streams/websocket-messages#mark-message
            return
        if event.type == "interrupted":
            # https://www.twilio.com/docs/voice/media-streams/websocket-messages#send-a-clear-message
            return await ws.send_json({"event": "clear", "streamSid": stream_sid})

        payload = adk_pcm24k_to_twilio_ulaw8k(event.payload)

        await ws.send_json(
            {
                "event": "media",
                "streamSid": stream_sid,
                "media": {"payload": payload},
            }
        )

    async def websocket_loop():
        """
        Handle incoming WebSocket messages to Agent.
        """
        while True:
            event = await ws.receive_json()
            event_type = event["event"]

            if event_type == "stop":
                logger.debug(f"Call ended by Twilio. Stream SID: {stream_sid}")
                break

            if event_type == "start" or event_type == "connected":
                logger.warning(f"Unexpected Twilio Initialization event: {event}")
                continue

            elif event_type == "dtmf":
                digit = event["dtmf"]["digit"]
                logger.info(f"DTMF: {digit}")
                continue

            elif event_type == "mark":
                logger.info(f"Twilio sent a Mark Event: {event}")
                continue

            elif event_type == "media":
                payload = event["media"]["payload"]
                mulaw_bytes = base64.b64decode(payload)
                pcm_bytes = twilio_ulaw8k_to_adk_pcm16k(mulaw_bytes)
                send_pcm_to_agent(pcm_bytes, live_request_queue)

    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(websocket_loop())
            tg.create_task(agent_to_client_messaging(handle_agent_event, live_events))
    except Exception as ex:
        logger.error(f"Unexpected Error: {ex}")
    finally:
        live_request_queue.close()
        await ws.close()

    # https://www.twilio.com/docs/voice/media-streams/websocket-messages
    # {'event': 'connected', 'protocol': 'Call', 'version': '1.0.0'}
    # {'event': 'start', 'sequenceNumber': '1', 'start': {'accountSid': '', 'streamSid': '', 'callSid': '', 'tracks': ['inbound'], 'mediaFormat': {'encoding': 'audio/x-mulaw', 'sampleRate': 8000, 'channels': 1}, 'customParameters': {'caller': ''}}, 'streamSid': ''}
    # {'event': 'media', 'sequenceNumber': '2', 'media': {'track': 'inbound', 'chunk': '1', 'timestamp': '57', 'payload': '+33+/3t7/f3/fvv7fX3+/f5+/vv2fnv8ePt9ff59fn97/nr//3v9fH14+Hj+fv3++3x+/3j+fn35/f58fX3/e/15ff7+ff78+318/X99/P39/nx9f319+v3+fvp9///9/f5+/Pz/fX76//z+/Xx9+//9fv97fn79ev7//Xh9/3v+fP59/f///P7/+3p6/Hj7/Xz/eP59/X79f/7+/n77/g=='}, 'streamSid': ''}
    # {'event': 'stop', 'sequenceNumber': '50', 'streamSid': '', 'stop': {'accountSid': '', 'callSid': ''}}

    # audio_frames = []

    # try:
    #     while True:
    #         data = await websocket.receive_json()

    #         if data["event"] == "media":
    #             ulaw_bytes = base64.b64decode(data["media"]["payload"])
    #             pcm16 = mulaw_to_pcm(ulaw_bytes)
    #             # audio_frames.append(pcm16)
    #             # audio_frames.append(ulaw_bytes)
    #             back_to_ulaw = pcm_to_mulaw(pcm16)
    #             audio_frames.append(back_to_ulaw)
    #             await websocket.send_json(data)

    #     if audio_frames:
    #         os.makedirs("recordings", exist_ok=True)
    #         timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    #         output_filepath = os.path.join("recordings", f"{timestamp}.wav")

    #         wave_write = pywav.WavWrite(output_filepath, 1,8000,8,7)  # 1 stands for mono channel, 8000 sample rate, 8 bit, 7 stands for MULAW encoding
    #         # wave_write = pywav.WavWrite(output_filepath, 1,24000,16,1)
    #         wave_write.write(b"".join(audio_frames))

    #         # with wave.open(output_filepath, 'wb') as wf:
    #         #     wf.setnchannels(1)
    #         #     wf.setsampwidth(2)
    #         #     wf.setframerate(24000)
    #         #     wf.writeframes(b"".join(audio_frames))
    #         # print(f"Audio saved to {output_filepath}")
    #     await websocket.close()
