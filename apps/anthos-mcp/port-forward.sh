kubectl port-forward svc/balancereader 8080:8080 & \
kubectl port-forward svc/userservice 8081:8080 & \
wait
