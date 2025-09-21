# Kubernetes Config

Follow the instructions here to deploy the project to a GKE AutoPilot Cluster

## Instructions

It's not just as simple as running `kubectl apply`, there's more we have to do first!

### 1. Create a GKE Autopilot cluster

Or you could create it in the console.

```sh
gcloud container clusters create-auto <cluster-name> --project=<project-id> --region=<region>
```

### 2. Reserve Static IP

This is necessary to bind our gateway to a static, unchanging IP address which we can point our domain at.

When this is configured, go to your domain's DNS config and create an `A` record from `*` pointing at this IP address to use all subdomains.


```sh
gcloud compute addresses create heckerlabs-ip --global --project=<project-id>

# in DNS config, create an `A` record from `*` to this IP
```

### 3. CertificateMap for HTTPS

This step is a bit more involved. There are several commands that need to be run to setup SSL/HTTPS.

```sh
# Configurable Variables
PROJECT_ID="heckerlabs"
BASE="heckerlabs.com"
WILDCARD="*.heckerlabs.com"
AUTH="auth-heckerlabs"
CERT="cert-wildcard"
MAP="heckathon-certmap"
ENTRY="wildcard-entry"

gcloud config set project "$PROJECT_ID"

# 1) DNS Authorization (one record proves apex + wildcard)
gcloud certificate-manager dns-authorizations create "$AUTH" \
  --domain="$BASE" --location=global
gcloud certificate-manager dns-authorizations describe "$AUTH" \
  --location=global \
  --format='value(dnsResourceRecord.name,dnsResourceRecord.type,dnsResourceRecord.data)'
# add this record at your DNS provider

# 2) Create Google-managed wildcard certificate
gcloud certificate-manager certificates create "$CERT" \
  --location=global \
  --domains="$WILDCARD" \
  --dns-authorizations="$AUTH"

# 3) Create cert map + entry for the wildcard hostname pattern
gcloud certificate-manager maps create "$MAP" --location=global
gcloud certificate-manager maps entries create "$ENTRY" \
  --location=global --map="$MAP" \
  --hostname="$WILDCARD" \
  --certificates="$CERT"
```

### 4. Provide Secrets

You will need a Google API key, Twilio API keys and auth tokens, and a few more.

- Copy `k8s/.env.example` to `k8s/.env` and fill the values. These will be used to populate kubernetes secrets.

### 5. Build & Push Docker Images

`voice-bridge` and `anthos-mcp` are local images not published to a public registry. First, we need to build them and push them to a private container registry. Please follow the directions in [voice-bridge](../apps/voice-bridge/README.md) and [anthos-mcp](../apps/anthos-mcp/README.md), respectively.

### 5. Apply Kubernetes

This command will apply the config specified in `k8s/kustomization.yaml` and all referenced files.

```sh
kubectl apply -k k8s/
```
### 6. View service state

Make sure all the services are running.

```sh
kubectl get service
```

### 7. View deployments

It may take a while for everything to get up and running, but when it is you should be able to see something at the main subdomains that were configured in [gateway](./gateway.yaml).

- [Bank of Anthos](https://bank.heckerlabs.com)
- [MCP Server](https://mcp.heckerlabs.com/mcp) (gives error in browser)
- [Voice Bridge](https://voice.heckerlabs.com/docs)
