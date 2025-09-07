from fastapi import FastAPI
from .routers import health, twilio


def create_app() -> FastAPI:
    app = FastAPI(title="Voice Bridge")
    app.include_router(health.router)
    app.include_router(twilio.router)

    return app


app = create_app()
