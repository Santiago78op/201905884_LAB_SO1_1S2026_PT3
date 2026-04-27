# Configuración GCP / GKE — M.U.M.N.K8s

## Cuenta GCP

- Cuenta: `santiagojulian78op@gmail.com`
- Proyecto: `mumk8s`
- Billing: activo ($300 crédito gratuito)
- Zona elegida: `us-central1-a`

---

## Instalación gcloud CLI (en VM Debian)

```bash
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg

echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee /etc/apt/sources.list.d/google-cloud-sdk.list

sudo apt-get update && sudo apt-get install -y google-cloud-cli google-cloud-cli-gke-gcloud-auth-plugin kubectl
```

**Autenticación y proyecto:**
```bash
gcloud init
# Seleccionar cuenta y proyecto mumk8s
```

---

## APIs habilitadas

```bash
gcloud services enable container.googleapis.com compute.googleapis.com --project mumk8s
```

> **Nota:** `kubevirt.io` NO es una API de GCP. KubeVirt se instala con `kubectl` después de crear el clúster.

---

## Crear clúster GKE

```bash
gcloud container clusters create mumk8s-cluster --zone us-central1-a --num-nodes 3 --machine-type n1-standard-2 --enable-autoscaling --min-nodes 1 --max-nodes 5 --project mumk8s
```

> Tarda 5–10 minutos.

**Conectar kubectl al clúster:**
```bash
gcloud container clusters get-credentials mumk8s-cluster --zone us-central1-a --project mumk8s
```

**Verificar conexión:**
```bash
kubectl get nodes
```

---

## Instalar KubeVirt en el clúster

> Ejecutar DESPUÉS de que kubectl esté conectado al clúster.

```bash
kubectl apply -f https://github.com/kubevirt/kubevirt/releases/download/v1.3.0/kubevirt-operator.yaml
kubectl apply -f https://github.com/kubevirt/kubevirt/releases/download/v1.3.0/kubevirt-cr.yaml
```

**Verificar que KubeVirt esté listo:**
```bash
kubectl get kubevirt -n kubevirt
kubectl wait --for=condition=Available kubevirt/kubevirt -n kubevirt --timeout=300s
```

---

## Crear VM GCP para Zot (fuera del clúster)

```bash
gcloud compute instances create zot-registry \
  --zone us-central1-a \
  --machine-type e2-medium \
  --image-family debian-12 \
  --image-project debian-cloud \
  --project mumk8s
```

**Instalar Docker y Zot en la VM:**
```bash
# SSH a la VM
gcloud compute ssh zot-registry --zone us-central1-a --project mumk8s

# Dentro de la VM:
sudo apt-get update && sudo apt-get install -y docker.io
sudo docker run -d -p 5000:5000 --name zot ghcr.io/project-zot/zot-linux-amd64:latest
```

**Obtener IP externa de Zot:**
```bash
gcloud compute instances describe zot-registry --zone us-central1-a --project mumk8s --format='get(networkInterfaces[0].accessConfigs[0].natIP)'
```

---

## Build y Push de imágenes a Zot

> Reemplazar `<ZOT_IP>` con la IP externa de la VM de Zot.

```bash
# Desde la raíz del repo
docker build -f Dockerfile.go-client   -t <ZOT_IP>:5000/go-client:latest .
docker build -f Dockerfile.go-server   -t <ZOT_IP>:5000/go-server:latest .
docker build -f Dockerfile.go-consumer -t <ZOT_IP>:5000/go-consumer:latest .
docker build -f rust-api/Dockerfile    -t <ZOT_IP>:5000/rust-api:latest rust-api/

docker push <ZOT_IP>:5000/go-client:latest
docker push <ZOT_IP>:5000/go-server:latest
docker push <ZOT_IP>:5000/go-consumer:latest
docker push <ZOT_IP>:5000/rust-api:latest
```

> También actualizar los YAMLs en `deployments/` para usar `<ZOT_IP>:5000/` en lugar de `zot-registry:5000/`.

---

## Aplicar manifiestos K8s

```bash
kubectl apply -f deployments/namespaces.yaml
kubectl apply -f deployments/rabbitmq.yaml
kubectl apply -f deployments/go-services.yaml
kubectl apply -f deployments/rust-api.yaml
kubectl apply -f deployments/gateway.yaml
kubectl apply -f deployments/kubevirt.yaml
```

---

## Verificación del sistema

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

## Estado del clúster (2026-04-27)

| Componente | Estado |
|---|---|
| Proyecto GCP | `mumk8s` |
| Clúster GKE | `mumk8s-cluster` — RUNNING |
| Zona clúster | `us-east1-b` |
| Master IP | `34.26.140.144` |
| Nodos activos | 2 × `n2-standard-4` (pd-standard, 50GB, UBUNTU_CONTAINERD) |
| Virtualización anidada | habilitada |
| KubeVirt | **Deployed** v1.3.0 |
| kubectl | Configurado |
| VM Zot | `zot-registry` — `us-central1-a` — IP: `34.68.174.65` |
| Zot puerto | 5000 (firewall `allow-zot` abierto) |
| Imágenes en Zot | go-client, go-server, go-consumer, rust-api ✅ |
| Namespaces K8s | `military-pipeline` + `messaging` ✅ |
| RabbitMQ | Deployment + Service en `messaging` ✅ |
| Go Services | go-client, go-server, go-consumer desplegados ✅ |
| Rust API + HPA | Desplegado en `military-pipeline` ✅ |
| Gateway API | Habilitando (`RECONCILING`)... |
| KubeVirt VMs | Pendiente (después del Gateway) |

---

## Notas de virtctl

`virtctl` es opcional para este proyecto. No se necesita para:
- Aplicar manifiestos de VirtualMachine
- Arrancar VMs con cloud-init

Solo se requeriría para consola interactiva, migración en vivo o upload de discos. Para M.U.M.N.K8s, `kubectl` es suficiente.

---

## Errores conocidos

| Error | Causa | Solución |
|---|---|---|
| `kubevirt.io` no encontrado en `gcloud services enable` | KubeVirt no es API de GCP | Instalar con `kubectl apply` después del clúster |
| `kubectl` conecta a `localhost:8080` | kubectl no configurado | Ejecutar `get-credentials` |
| `--zone` no reconocido | Backslash roto en copy-paste | Usar comando en una sola línea |
| `container.googleapis.com` error 403 | API no habilitada | `gcloud services enable container.googleapis.com` |
| `Quota 'SSD_TOTAL_GB' exceeded` | Cuota SSD agotada en us-central1 | Usar `--disk-type pd-standard --disk-size 50` |
| `GCE_STOCKOUT` en us-central1-a | Sin n2-standard-4 disponibles | Cambiar zona a `us-east1-b` |
| KubeVirt job en `Pending` eternamente | GKE no expone nodos control-plane | Agregar label manualmente: `kubectl label node <nodo> node-role.kubernetes.io/control-plane=""` |
