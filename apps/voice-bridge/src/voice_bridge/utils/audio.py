import audioop
import numpy as np
import soxr


# ── Inbound: Twilio μ-law/8k → PCM/16k for ADK ───────────────────────────────
def twilio_ulaw8k_to_adk_pcm16k(mulaw_bytes: bytes) -> bytes:
    pcm8 = audioop.ulaw2lin(mulaw_bytes, 2)                      # → 16-bit PCM @ 8k
    # resample: int16 ↔ float32 for soxr
    x = np.frombuffer(pcm8, dtype=np.int16).astype(np.float32) / 32768.0
    y = soxr.resample(x, 8000, 16000)                     # 8k → 16k
    pcm16 = (np.clip(y, -1, 1) * 32767).astype(np.int16).tobytes()
    return pcm16  # send via ADK: Blob(data=pcm16, mime_type="audio/pcm;rate=16000")

# ── Outbound: ADK PCM/24k → μ-law/8k for Twilio ─────────────────────────────
def adk_pcm24k_to_twilio_ulaw8k(pcm24: bytes) -> bytes:
    x = np.frombuffer(pcm24, dtype=np.int16).astype(np.float32) / 32768.0
    y = soxr.resample(x, 24000, 8000)                     # 24k → 8k
    pcm8 = (np.clip(y, -1, 1) * 32767).astype(np.int16).tobytes()
    ulaw = audioop.lin2ulaw(pcm8, 2)                      # PCM → μ-law
    return ulaw


# import numpy as np
# import soxr
# import audioop


# def mulaw_to_pcm(mulaw_bytes: bytes) -> np.ndarray:
#     """
#     Convert μ-law encoded audio to PCM format.
#     This function converts μ-law encoded audio data to PCM format and resamples it from 8kHz to 24kHz.
#     The input audio data is expected to be in μ-law format, and the output will be a NumPy array of
#     int16 PCM samples.
#     Args:
#         mulaw_bytes (bytes): The μ-law encoded audio data.
#     Returns:
#         np.ndarray: The PCM audio data resampled to 24kHz.
#     """
#     pcm = audioop.ulaw2lin(mulaw_bytes, 2)
#     audio_np = np.frombuffer(pcm, dtype=np.int16)

#     # Resample from 8kHz to 24kHz, maintaining int16 format
#     audio_24k = soxr.resample(audio_np, 8000, 24000)

#     # Return as int16 instead of converting to float32
#     return audio_24k.astype(np.int16)


# def pcm_to_mulaw(audio_data: np.ndarray) -> bytes:
#     """
#     Convert PCM audio to Twilio μ-law format.
#     This function converts PCM audio data to μ-law format and resamples it from 24kHz to 8kHz.
#     The input audio data is expected to be in PCM format, and the output will be μ-law encoded bytes.
#     Args:
#         audio_data (np.ndarray): The PCM audio data.
#     Returns:
#         bytes: The μ-law encoded audio data.
#     """
#     # Normalize dtype
#     if audio_data.dtype == np.int16:
#         audio_data = audio_data.astype(np.float32) / 32768.0
#     elif audio_data.dtype != np.float32:
#         raise ValueError(f"Unsupported dtype: {audio_data.dtype}")

#     # Resample from 24kHz → 8kHz
#     resampled = soxr.resample(audio_data, 24000, 8000)

#     # Convert to int16
#     resampled_int16 = np.clip(resampled * 32768.0, -32768, 32767).astype(np.int16)

#     # μ-law encode
#     return audioop.lin2ulaw(resampled_int16.tobytes(), 2)
