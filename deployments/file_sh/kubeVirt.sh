#!/bin/bash

# Lista de nodos a etiquetar
NODES=(
    "gke-mumk8s-cluster-default-pool-1158e3a4-31wx"
    "gke-mumk8s-cluster-default-pool-1158e3a4-dht6"
    "gke-mumk8s-cluster-default-pool-1158e3a4-j9qp"
)

echo "Iniciando el etiquetado de nodos..."

for NODE in "${NODES[@]}"; do
    echo "Aplicando etiqueta a: $NODE"
    kubectl label node "$NODE" node-role.kubernetes.io/control-plane="" --overwrite
done

echo "Proceso completado."
