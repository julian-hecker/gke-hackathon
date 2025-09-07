import asyncio
import base64
from typing import Annotated
from fastapi import APIRouter, Form, Request, Response, WebSocket
from fastapi.params import Depends
from fastapi.responses import HTMLResponse
from twilio.twiml.voice_response import Connect, Stream, VoiceResponse

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
async def twilio_ws(ws: WebSocket):
    """Handle Twilio Media Stream WebSocket connection"""

    async def on_agent_audio_24k(pcm24: bytes):
        payload = None # todo: convert to 8k mulaw
        await ws.send_json(
            {
                "event": "media",
                "streamSid": streamSid,
                "media": {"payload": payload},
            }
        )

    try:
        await ws.accept()
        await ws.receive_json()  # throw away `connected` event

        start_event = await ws.receive_json()
        assert start_event["event"] == "start"

        accountSid = start_event["start"]["accountSid"]
        callSid = start_event["start"]["callSid"]
        encoding = start_event["start"]["mediaFormat"]["encoding"]
        sampleRate = start_event["start"]["mediaFormat"]["sampleRate"]
        channels = start_event["start"]["mediaFormat"]["channels"]
        from_phone = start_event["start"]["customParameters"]["from_phone"]
        to_phone = start_event["start"]["customParameters"]["to_phone"]
        streamSid = start_event["streamSid"]

        logger.info(
            f"accountSid: {accountSid}, callSid: {callSid}, encoding: {encoding}, sampleRate: {sampleRate}, channels: {channels}, from_phone: {from_phone}, to_phone: {to_phone}, streamSid: {streamSid}"
        )

        while True:
            event = await ws.receive_json()

            event_type = event["event"]

            if event_type == "media":
                payload = event["media"]["payload"]
                mulaw_bytes = base64.b64decode(payload)
                pcm_bytes = twilio_ulaw8k_to_adk_pcm16k(mulaw_bytes)

                # await agent live session here

            elif event_type == "dtmf":
                digit = event["dtmf"]["digit"]
                logger.info(digit)

            elif event_type == "stop":
                logger.info("Twilio Media Stream Stopped")
                break

    except asyncio.exceptions.CancelledError:
        raise
    except Exception as ex:
        logger.error(f"Unexpected Error: {ex}")
    finally:
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
