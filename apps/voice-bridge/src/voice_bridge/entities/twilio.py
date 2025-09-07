from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


class TwilioStreamCallbackPayload(BaseModel):
    """
    Payload from Twilio Stream Status Callback

    [See Twilio Docs](https://www.twilio.com/docs/voice/twiml/stream#statuscallback)
    """

    AccountSid: str = Field(description="Twilio Account SID")
    CallSid: str = Field(description="Twilio Call SID")
    StreamSid: str = Field(description="Twilio Stream SID")
    StreamName: str = Field(description="Twilio Stream Name")
    StreamEvent: Literal["stream-started", "stream-stopped", "stream-error"]
    StreamError: str | None = None
    Timestamp: datetime


class TwilioVoiceWebhookPayload(BaseModel):
    """
    Form-encoded payload sent by Twilio when a call hits your webhook.
    
    [See Twilio Docs](https://www.twilio.com/docs/voice/twiml#request-parameters)
    """

    From: str = Field(description="Caller's phone number")
    To: str = Field(description="Recipient's phone number")
    Direction: Literal["inbound", "outbound-api", "outbound-dial"]
    ApiVersion: str = Field("2010-04-01", description="Twilio API Version")
    AccountSid: str = Field("", description="Twilio Account SID")
    CallSid: str = Field("", description="Twilio Call SID")
