from typing import Sequence
from google.adk import Agent
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.genai.types import (
    ActivityHandling,
    PrebuiltVoiceConfig,
    RealtimeInputConfig,
    SpeechConfig,
    VoiceConfig,
)


def build_agent_from_profile(profile: TenantProfile) -> Agent:
    """
    Return a configured ADK Agent for this tenant.
    """
    # Tools: resolve from your registry by name/config in the profile
    tools: Sequence[object] = resolve_tools_for_profile(profile.tools)

    model_id = profile.model or "gemini-2.5-flash-preview-native-audio-dialog"
    instruction = profile.prompt.instruction

    agent = Agent(
        name=f"{profile.slug}_receptionist",
        model=model_id,
        instruction=instruction,
        tools=tools,
    )
    return agent


def make_run_config_for_profile(profile: TenantProfile) -> RunConfig:
    """
    Live config: AUDIO out, voice, barge-in behavior via realtime_input_config.
    """
    voice_name = profile.voice.prebuilt or "Aoede"
    prebuilt_voice_config = PrebuiltVoiceConfig(voice_name=voice_name)
    voice_config = VoiceConfig(prebuilt_voice_config=prebuilt_voice_config)
    speech_config = SpeechConfig(voice_config=voice_config)

    # VAD + interruption (barge-in) handled by Live/ADK; we opt into interrupting.
    realtime = RealtimeInputConfig(
        activity_handling=ActivityHandling.START_OF_ACTIVITY_INTERRUPTS
    )

    return RunConfig(
        response_modalities=["AUDIO"],  # agent will speak
        speech_config=speech_config,  # choose voice
        realtime_input_config=realtime,  # VAD + interruption
        # (optionally) input/output transcription:
        # output_audio_transcription=genai_types.AudioTranscriptionConfig(),
        # input_audio_transcription=genai_types.AudioTranscriptionConfig(),
        # session_resumption=genai_types.SessionResumptionConfig(mode="TRANSPARENT"),
        max_llm_calls=500,
        streaming_mode=StreamingMode.BIDI,
    )
