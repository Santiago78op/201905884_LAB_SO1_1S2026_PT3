# Guía de Reinstalación desde Cero — M.U.M.N.K8s

Cuenta: `santiagojulian78op@gmail.com` | Proyecto GCP: `mumk8s`

---

## Variables de referencia

```
ZOT_IP=34.68.174.65
ZOT_ZONE=us-central1-a
CLUSTER_ZONE=us-east1-b
PROJECT=mumk8s
CLUSTER=mumk8s-cluster
```

---

## Paso 1 — Autenticar gcloud

```bash
gcloud init
# Seleccionar cuenta santiagojulian78op@gmail.com y proyecto mumk8s
```

---

## Paso 2 — Crear clúster GKE

```bash
gcloud services enable container.googleapis.com compute.googleapis.com --project mumk8s

gcloud container clusters create mumk8s-cluster --zone us-east1-b --num-nodes 3 --machine-type n2-standard-4 --disk-type pd-standard --disk-size 50 --image-type UBUNTU_CONTAINERD --enable-nested-virtualization --enable-autoscaling --min-nodes 1 --max-nodes 5 --project mumk8s
```

> Si hay stockout en us-east1-b, probar us-east1-c o us-east4-b.

---

## Paso 3 — Conectar kubectl

```bash
gcloud container clusters get-credentials mumk8s-cluster --zone us-east1-b --project mumk8s
kubectl get nodes
```

---

## Paso 4 — Instalar KubeVirt

```bash
kubectl apply -f https://github.com/kubevirt/kubevirt/releases/download/v1.3.0/kubevirt-operator.yaml
kubectl apply -f https://github.com/kubevirt/kubevirt/releases/download/v1.3.0/kubevirt-cr.yaml
```

Esperar ~2 minutos. Si el job queda en `Pending`:

```bash
# Agregar label de control-plane a un nodo worker
kubectl label node <nombre-nodo> node-role.kubernetes.io/control-plane=""

# Verificar que KubeVirt está Deployed
kubectl get kubevirt kubevirt -n kubevirt -o jsonpath='{.status.phase}'
```

---

## Paso 5 — Habilitar Gateway API en GKE

```bash
gcloud container clusters update mumk8s-cluster --gateway-api=standard --zone us-east1-b --project mumk8s
```

Esperar hasta que el clúster vuelva a `RUNNING`:

```bash
gcloud container clusters describe mumk8s-cluster --zone us-east1-b --project mumk8s --format='get(status)'
```

---

## Paso 6 — Verificar VM Zot (ya existe)

```bash
# Verificar que Zot responde
curl http://34.68.174.65:5000/v2/_catalog
# Debe mostrar: {"repositories":["go-client","go-consumer","go-server","rust-api"]}
```

Si la VM fue eliminada, recrearla:

```bash
gcloud compute instances create zot-registry --zone us-central1-a --machine-type n1-standard-1 --image-family debian-12 --image-project debian-cloud --project mumk8s

gcloud compute firewall-rules create allow-zot --allow tcp:5000 --source-ranges 0.0.0.0/0 --project mumk8s

gcloud compute ssh zot-registry --zone us-central1-a --project mumk8s
# Dentro de la VM:
sudo apt-get update && sudo apt-get install -y docker.io
sudo systemctl start docker && sudo systemctl enable docker
sudo docker run -d -p 5000:5000 --name zot --restart always ghcr.io/project-zot/zot-linux-amd64:latest
exit
```

---

## Paso 7 — Rebuild imágenes para linux/amd64 y push a Zot

> **IMPORTANTE:** La VM Debian es ARM64 pero los nodos GKE son AMD64.
> Siempre usar `docker buildx` con `--platform linux/amd64`.

### Prerequisitos (solo primera vez tras reinstalar el OS)

```bash
# 1. Instalar QEMU para emulación AMD64
sudo apt-get install -y qemu-user-static binfmt-support

# 2. Verificar que qemu-x86_64 está registrado
ls /proc/sys/fs/binfmt_misc/ | grep qemu-x86_64

# 3. Configurar Docker para registry inseguro
echo '{"insecure-registries": ["34.68.174.65:5000"]}' | sudo tee /etc/docker/daemon.json
sudo systemctl restart docker

# 4. Crear builder con soporte AMD64 y registry insecure
mkdir -p ~/.docker/buildx
cat > ~/.docker/buildx/buildkitd.toml << 'EOF'
[registry."34.68.174.65:5000"]
  http = true
  insecure = true
EOF
docker buildx rm amd64builder 2>/dev/null || true
docker buildx create --use --name amd64builder --config ~/.docker/buildx/buildkitd.toml
docker buildx inspect --bootstrap
# Verificar que "linux/amd64" aparece en Platforms
```

### Build y push

```bash
cd /home/julian/Documents/201905884_LAB_SO1_1S2026_PT3

# Go services — usan QEMU (CGO_ENABLED=0 ya está en los Dockerfiles)
docker buildx build --platform linux/amd64 -f Dockerfile.go-client   -t 34.68.174.65:5000/go-client:latest   --push .
docker buildx build --platform linux/amd64 -f Dockerfile.go-server   -t 34.68.174.65:5000/go-server:latest   --push .
docker buildx build --platform linux/amd64 -f Dockerfile.go-consumer -t 34.68.174.65:5000/go-consumer:latest --push .

# Rust API — usa cross-compilación nativa (QEMU crashea con rustc)
# rust-api/Dockerfile ya tiene --platform=$BUILDPLATFORM + target x86_64-unknown-linux-gnu
docker buildx build --platform linux/amd64 -f rust-api/Dockerfile    -t 34.68.174.65:5000/rust-api:latest    --push rust-api/

# Verificar imágenes en Zot
curl http://34.68.174.65:5000/v2/_catalog
# Debe mostrar: {"repositories":["go-client","go-consumer","go-server","rust-api"]}
```

---

## Paso 8 — Configurar registry inseguro en nodos GKE

> **IMPORTANTE:** El DaemonSet `insecure-registry.yaml` NO funciona correctamente en GKE.
> GKE usa `mirrors` en containerd y el enfoque `config_path` es incompatible.
> Configurar manualmente vía SSH en cada nodo.

```bash
# Obtener nombre del nodo
kubectl get nodes

# SSH al nodo (reemplazar <NOMBRE_NODO> con el nombre real)
gcloud compute ssh <NOMBRE_NODO> --zone us-east1-b --project mumk8s
```

Dentro del nodo, ejecutar:

```bash
# Agregar mirror para Zot (HTTP inseguro)
sudo sed -i '/endpoint = \["https:\/\/mirror\.gcr\.io","https:\/\/registry-1\.docker\.io"\]/a\\n[plugins."io.containerd.grpc.v1.cri".registry.mirrors."34.68.174.65:5000"]\n  endpoint = ["http://34.68.174.65:5000"]\n\n[plugins."io.containerd.grpc.v1.cri".registry.configs."34.68.174.65:5000".tls]\n  insecure_skip_verify = true' /etc/containerd/config.toml

# Verificar que quedó
grep -A 3 "34.68.174.65" /etc/containerd/config.toml

# Reiniciar containerd
sudo systemctl restart containerd
sudo systemctl is-active containerd

# Salir del nodo
exit
```

> **CRÍTICO:** NO usar `config_path` en `config.toml` — conflicta con `mirrors` de GKE y crashea containerd.

---

## Paso 9 — Aplicar manifiestos K8s

```bash
kubectl apply -f deployments/namespaces.yaml
kubectl apply -f deployments/rabbitmq.yaml
kubectl apply -f deployments/go-services.yaml
kubectl apply -f deployments/rust-api.yaml
kubectl apply -f deployments/gateway.yaml
kubectl apply -f deployments/kubevirt.yaml
```

> Después de aplicar kubevirt.yaml, esperar 4-5 minutos para que las VMs terminen cloud-init (instalación de redis-server y grafana).

---

## Paso 10 — Verificar el sistema completo

```bash
# Pods en todos los namespaces
kubectl get pods -A

# VMs KubeVirt (esperar Running True en ambas)
kubectl get vm -n messaging
kubectl get vmi -n messaging

# HPA
kubectl get hpa -n military-pipeline

# IP pública del Gateway (esperar PROGRAMMED=True)
kubectl get gateway -n military-pipeline

# Forzar restart de deployments para limpiar estados viejos
kubectl rollout restart deployment/go-client deployment/go-server deployment/rust-api -n military-pipeline
kubectl rollout restart deployment/go-consumer -n messaging
```

---

## Paso 11 — Probar el pipeline completo

```bash
# Reemplazar <GATEWAY_IP> con la IP del kubectl get gateway
curl -X POST http://<GATEWAY_IP>/grpc-201905884 \
  -H "Content-Type: application/json" \
  -d '{"country":"CHN","warplanes_in_air":42,"warships_in_water":14,"timestamp":"2026-04-28T02:00:00Z"}'
# Debe responder: Report forwarded successfully

# Verificar datos en Valkey
kubectl port-forward svc/valkey-service 6379:6379 -n messaging &
redis-cli -h 127.0.0.1 -p 6379 keys '*'
# Debe mostrar las 10 keys: meminfo, rss_rank, cpu_rank, max/min warplanes/warships, modas, total_chn
kill %1  # Matar el port-forward
```

---

## Apagar el clúster (ahorrar crédito)

```bash
gcloud container clusters delete mumk8s-cluster --zone us-east1-b --project mumk8s --quiet
```

> La VM de Zot sigue corriendo y conserva las imágenes. Solo el clúster GKE se elimina.
> Para detener también la VM de Zot:
> ```bash
> gcloud compute instances stop zot-registry --zone us-central1-a --project mumk8s
> ```

---

## Errores conocidos

| Error | Causa | Solución |
|---|---|---|
| `Quota SSD_TOTAL_GB exceeded` | Cuota SSD agotada | `--disk-type pd-standard --disk-size 50` |
| `Quota CPUS_ALL_REGIONS exceeded` | Zot VM usa 1 CPU, máximo 2 nodos n2-standard-4 | Usar `--num-nodes 2 --max-nodes 3` |
| `GCE_STOCKOUT` | Sin VMs disponibles en la zona | Cambiar zona |
| KubeVirt job `Pending` | GKE no expone control-plane | `kubectl label node <nodo> node-role.kubernetes.io/control-plane=""` |
| `Gateway API CRDs not found` | Gateway API no habilitado | `gcloud container clusters update ... --gateway-api=standard` |
| `exec ./go-client: no such file or directory` | CGO habilitado, binario linkado a glibc, Alpine usa musl | `CGO_ENABLED=0` ya en Dockerfiles |
| `http: server gave HTTP response to HTTPS client` (buildx push) | BuildKit no tiene config de registry insecure | Crear `~/.docker/buildx/buildkitd.toml` y recrear builder |
| `config_path cannot be set when mirrors is provided` | Conflicto en containerd config | Usar `mirrors` vía SSH, nunca `config_path` |
| `no healthy upstream` en Gateway | GKE health check falla (no hay GET /) | rust-api ya tiene `GET /` que retorna 200 |
| Valkey VM en `Pending` eternamente | Estado inconsistente | `kubectl delete vm valkey-vm -n messaging && kubectl apply -f deployments/kubevirt.yaml` |
| go-consumer `CrashLoopBackOff: connection refused` | Valkey VM aún en cloud-init | Esperar 4-5 min y hacer `kubectl rollout restart deployment/go-consumer -n messaging` |
| Go services sin logs | Normal — el código no tiene log.Printf | Verificar datos con `redis-cli keys '*'` vía port-forward |
