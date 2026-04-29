#!/bin/bash

# Configuración de variables
PROJECT="mumk8s"
ZONE="us-east1-b"
REGISTRY_IP="34.68.174.65:5000"

# Lista de nodos
NODES=(
  "gke-mumk8s-cluster-default-pool-1158e3a4-dht6"
  "gke-mumk8s-cluster-default-pool-1158e3a4-j9qp"
)

for NODE in "${NODES[@]}"; do
    echo "--------------------------------------------"
    echo "Configurando nodo: $NODE..."
    
    gcloud compute ssh "$NODE" --zone "$ZONE" --project "$PROJECT" --command "
      sudo tee -a /etc/containerd/config.toml << 'EOF'

[plugins.\"io.containerd.grpc.v1.cri\".registry.mirrors.\"$REGISTRY_IP\"]
  endpoint = [\"http://$REGISTRY_IP\"]

[plugins.\"io.containerd.grpc.v1.cri\".registry.configs.\"$REGISTRY_IP\".tls]
  insecure_skip_verify = true
EOF

      echo 'Reiniciando containerd...'
      sudo systemctl restart containerd
      sudo systemctl is-active containerd
    "
done

echo "--------------------------------------------"
echo "Proceso finalizado."
