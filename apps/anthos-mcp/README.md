# Anthos MCP

MCP Server for AI Agents to interact with Bank of Anthos services.

## Exposing Internal K8s Services

```sh
kubectl port-forward svc/balancereader 8080:8080
```

```sh
kubectl port-forward svc/userservice 8081:8080
```