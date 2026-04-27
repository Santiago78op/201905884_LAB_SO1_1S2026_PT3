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

```bash
# Configurar Docker para registry inseguro (solo primera vez)
echo '{"insecure-registries": ["34.68.174.65:5000"]}' | sudo tee /etc/docker/daemon.json
sudo systemctl restart docker

# Crear builder para AMD64 (solo primera vez)
docker buildx create --use --name amd64builder
docker buildx inspect --bootstrap

cd /home/julian/Documents/201905884_LAB_SO1_1S2026_PT3

# Build y push directo a Zot (--push sube automáticamente)
docker buildx build --platform linux/amd64 -f Dockerfile.go-client   -t 34.68.174.65:5000/go-client:latest   --push .
docker buildx build --platform linux/amd64 -f Dockerfile.go-server   -t 34.68.174.65:5000/go-server:latest   --push .
docker buildx build --platform linux/amd64 -f Dockerfile.go-consumer -t 34.68.174.65:5000/go-consumer:latest --push .
docker buildx build --platform linux/amd64 -f rust-api/Dockerfile    -t 34.68.174.65:5000/rust-api:latest    --push rust-api/

# Verificar imágenes en Zot
curl http://34.68.174.65:5000/v2/_catalog
```

---

## Paso 8 — Configurar registry inseguro en nodos GKE

```bash
kubectl apply -f deployments/insecure-registry.yaml
kubectl get pods -n kube-system -l name=configure-insecure-registry
```

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

---

## Paso 10 — Verificar el sistema completo

```bash
# Pods en todos los namespaces
kubectl get pods -A

# HPA
kubectl get hpa -n military-pipeline

# VMs KubeVirt
kubectl get vm -n messaging

# IP pública del Gateway
kubectl get gateway -n military-pipeline

# Logs del consumer
kubectl logs -l app=go-consumer -n messaging -f
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
| `GCE_STOCKOUT` | Sin VMs disponibles en la zona | Cambiar zona |
| KubeVirt job `Pending` | GKE no expone control-plane | `kubectl label node <nodo> node-role.kubernetes.io/control-plane=""` |
| `Gateway API CRDs not found` | Gateway API no habilitado | `gcloud container clusters update ... --gateway-api=standard` |
| Docker pull falla en nodos | Registry inseguro no configurado | Aplicar `insecure-registry.yaml` |
