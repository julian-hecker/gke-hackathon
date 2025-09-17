# Voice Bridge

This is a FastAPI application that connects Twilio with a Google ADK Agent. This app handles all things twilio and audio encoding.

## Docker

This application uses Docker to run on Kubernetes, Cloud Run, or any other container runtime. 

To build and run an image locally, run the following commands **from the project root directory**.

### Build docker image

```sh
docker build -f apps/voice-bridge/Dockerfile . --tag voice-bridge:tag
```

### Run docker image

```sh
docker run -it -p 8000:8000 --env-file ./.env voice-bridge:tag
```
