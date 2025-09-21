import os
from fastapi import HTTPException, Request
from twilio.request_validator import RequestValidator

from voice_bridge.utils.env import is_local

auth_token = os.environ.get("TWILIO_AUTH_TOKEN", "")


async def validate_twilio(request: Request):
    if is_local:
        return
    validator = RequestValidator(auth_token)
    signature = request.headers.get("X-Twilio-Signature", "")
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    print(proto)
    host = request.headers.get("host", request.url.hostname)
    path = request.url.path or ""
    query = request.url.query
    full_url = f"{proto}://{host}{path}"
    if query:
        full_url += f"?{query}"

    form = await request.form()
    is_valid = validator.validate(full_url, dict(form), signature)
    if not is_valid:
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")
