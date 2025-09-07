import os
from fastapi import HTTPException, Request
from twilio.request_validator import RequestValidator


auth_token = os.environ.get("TWILIO_AUTH_TOKEN", "")
is_local = os.environ.get("APP_ENVIRONMENT", "PROD") == "LOCAL"


async def validate_twilio(request: Request):
    if is_local:
        return
    validator = RequestValidator(auth_token)
    signature = request.headers.get("X-Twilio-Signature", "")
    form = await request.form()
    is_valid = validator.validate(str(request.url), dict(form), signature)
    if not is_valid:
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")
