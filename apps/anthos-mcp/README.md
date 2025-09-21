# Anthos MCP

MCP Server for AI Agents to interact with Bank of Anthos services.

## Exposing Internal K8s Services

```sh
kubectl port-forward svc/balancereader 8080:8080
```

```sh
kubectl port-forward svc/userservice 8081:8080
```

## Docker

This application uses Docker to run on Kubernetes, Cloud Run, or any other container runtime.

To build and run an image locally, run the following commands **from the project root directory**.

### Build Docker Image

```sh
PROJECT_ID="heckerlabs"
LOCATION="us-central1"
AR_HOST="${LOCATION}-docker.pkg.dev" # registry hostname
REPOSITORY="heckathon" # Artifact Registry repository name
IMAGE="anthos-mcp" # image name inside the repo (can match repo)
VERSION="$(git rev-parse --short HEAD)" # e.g., ab12cd3
LOCAL_TAG="${IMAGE}:${VERSION}" # e.g., anthos-mcp:ab12cd3

# Build local image
docker build -f "apps/${IMAGE}/Dockerfile" -t $LOCAL_TAG .
# also tag it as latest locally
docker tag $LOCAL_TAG "${IMAGE}:latest"
```

### Run Docker Image locally

```sh
docker run -it -p 8000:8000 --env-file ./.env $LOCAL_TAG
```

### Push Image to GCR

```sh
# Create GCR Repo
gcloud config set project $PROJECT_ID
gcloud artifacts repositories create $REPOSITORY --repository-format=docker --location=$LOCATION || true

# Authenticate Docker to Registry
gcloud auth configure-docker $AR_HOST

# Tag image for Registry
REMOTE_COMMIT="${AR_HOST}/${PROJECT_ID}/${REPOSITORY}/${IMAGE}:${VERSION}"
REMOTE_LATEST="${AR_HOST}/${PROJECT_ID}/${REPOSITORY}/${IMAGE}:latest"
# Provide both commit hash and latest tags
docker tag $LOCAL_TAG $REMOTE_COMMIT
docker tag $LOCAL_TAG $REMOTE_LATEST

# Push to Registry
docker push $REMOTE_COMMIT
docker push $REMOTE_LATEST
```

