# https://github.com/openai/openai-agents-python/issues/304#issuecomment-2746073108

import audioop
import numpy as np
import soxr


# Inbound: Twilio 8-bit 8kHz μ-law -> 16-bit 16kHz PCM for ADK
def twilio_ulaw8k_to_adk_pcm16k(mulaw_bytes: bytes) -> bytes:
    pcm8 = audioop.ulaw2lin(mulaw_bytes, 2)  # μ-law -> 16-bit PCM @ 8kHz
    # resample: int16 <-> float32 for soxr
    x = np.frombuffer(pcm8, dtype=np.int16).astype(np.float32) / 32768.0
    y = soxr.resample(x, 8000, 16000)  # 8kHz -> 16kHz
    pcm16 = (np.clip(y, -1, 1) * 32767).astype(np.int16).tobytes()
    return pcm16


# Outbound: ADK 16-bit 24kHz PCM -> Twilio 8-bit 8kHz μ-law
def adk_pcm24k_to_twilio_ulaw8k(pcm24: bytes) -> bytes:
    x = np.frombuffer(pcm24, dtype=np.int16).astype(np.float32) / 32768.0
    y = soxr.resample(x, 24000, 8000)  # 24kHz -> 8kHz
    pcm8 = (np.clip(y, -1, 1) * 32767).astype(np.int16).tobytes()
    ulaw = audioop.lin2ulaw(pcm8, 2)  # PCM -> μ-law
    return ulaw
