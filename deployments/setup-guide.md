# Guía de Reinstalación — M.U.M.N.K8s

Cuenta: `santiagojulian78op@gmail.com` | Proyecto GCP: `mumk8s`

---

## Variables de referencia

```
ZOT_IP=34.68.174.65
ZOT_ZONE=us-central1-a
CLUSTER_ZONE=us-east1-b
PROJECT=mumk8s
CLUSTER=mumk8s-cluster
GATEWAY_IP=34.102.175.55
```

> **Arquitectura:** La VM de desarrollo es Debian ARM64 (MacBook M5), pero los nodos GKE son **n2-standard-4 (x86/AMD64)** — requerido por KubeVirt (nested virtualization no disponible en N4A ARM64). Las imágenes deben compilarse para `linux/amd64`.

---

## Teoría del sistema

### ¿Qué es un clúster GKE?

GKE (Google Kubernetes Engine) es un servicio administrado de Kubernetes. Kubernetes es un orquestador de contenedores: decide **dónde** y **cuándo** corre cada contenedor, gestiona fallos, escala réplicas y administra la red entre servicios.

El clúster se compone de:
- **Control Plane** (administrado por GCP): API server, scheduler, etcd.
- **Node Pool**: VMs (nodos) donde corren los pods. Cada pod es uno o más contenedores.

### ¿Por qué n2-standard-4 (x86) y no N4A (ARM64)?

KubeVirt requiere **virtualización anidada** (nested virtualization) para crear VMs dentro del clúster. GCP no expone la instrucción `FEAT_NV` en procesadores ARM64 (N4A/T2A). Solo los nodos x86 (N2, N2D, etc.) soportan `/dev/kvm` necesario para QEMU/KVM. Sin `/dev/kvm`, KubeVirt no puede arrancar VMs.

### ¿Qué es un contenedor y por qué importa la arquitectura?

Un contenedor empaqueta un binario + sus dependencias. Ese binario contiene instrucciones de máquina específicas para una ISA (x86_64 o arm64). Un binario arm64 **no puede ejecutarse** en un nodo x86_64 sin emulación. Por eso los Dockerfiles usan `--platform=linux/amd64` aunque el build se haga desde ARM64 (con QEMU transparente via buildx).

### ¿Qué es KubeVirt?

KubeVirt extiende Kubernetes para correr **máquinas virtuales** como recursos nativos del clúster. Permite que Valkey y Grafana corran en VMs completas (con su propio kernel) en lugar de contenedores. Requiere **virtualización anidada** en los nodos — solo disponible en GKE con nodos x86 y `UBUNTU_CONTAINERD`.

### ¿Qué es Gateway API?

Gateway API es la evolución de Ingress en Kubernetes. Define recursos (`Gateway`, `HTTPRoute`) para exponer servicios al exterior con mayor expresividad. GKE tiene soporte nativo pero requiere dos pasos: instalar los CRDs upstream y habilitar el feature en el clúster con `--gateway-api=standard`.

### ¿Qué es containerd y por qué certs.d?

containerd es el runtime de contenedores en cada nodo GKE. Para hacer pull desde un registry HTTP inseguro (Zot sin TLS), containerd necesita configuración explícita. En containerd 2.x, `registry.mirrors` y `config_path` son **mutuamente excluyentes** — si coexisten en `config.toml`, `mirrors` es ignorado silenciosamente. GKE ya usa `config_path=/etc/containerd/certs.d`, por lo que la única forma correcta es crear archivos `hosts.toml` en ese directorio.

---

## Paso 1 — Autenticar gcloud

**¿Por qué?** `gcloud` es el CLI de GCP. Sin autenticación, ningún comando de infraestructura funciona.

```bash
gcloud init
# Seleccionar cuenta santiagojulian78op@gmail.com y proyecto mumk8s
```

---

## Paso 2 — Crear clúster GKE

**¿Por qué estos parámetros?**
- `n2-standard-4`: 4 vCPUs, 16GB RAM por nodo. **x86/AMD64**. Soporta nested virtualization para KubeVirt.
- `--num-nodes 3`: 3 nodos fijos = 12 vCPUs, 48GB totales. Sin node autoscaling (el HPA escala pods, no nodos).
- `UBUNTU_CONTAINERD`: único image type de GKE que soporta virtualización anidada.
- `--enable-nested-virtualization`: habilita VT-x en los nodos para que KubeVirt pueda crear VMs.
- `--disk-type pd-standard`: evita errores de cuota SSD.

```bash
gcloud services enable container.googleapis.com compute.googleapis.com --project mumk8s

gcloud container clusters create mumk8s-cluster \
  --zone us-east1-b \
  --num-nodes 3 \
  --machine-type n2-standard-4 \
  --disk-type pd-standard \
  --disk-size 50 \
  --image-type UBUNTU_CONTAINERD \
  --enable-nested-virtualization \
  --project mumk8s
```

> Si hay stockout en `us-east1-b`, probar `us-east4-b` o `us-central1-b`.

---

## Paso 3 — Conectar kubectl

**¿Por qué?** `kubectl` necesita credenciales para comunicarse con el API server del clúster. Este comando descarga el kubeconfig.

```bash
gcloud container clusters get-credentials mumk8s-cluster --zone us-east1-b --project mumk8s
kubectl get nodes
# Debe mostrar 3 nodos en estado Ready
```

---

## Paso 4 — Instalar KubeVirt

**¿Por qué dos YAMLs?**
1. `kubevirt-operator.yaml`: instala el **operador** — controlador que entiende los recursos `VirtualMachine`.
2. `kubevirt-cr.yaml`: crea el **Custom Resource** que activa KubeVirt en el clúster.

```bash
export KVVERSION=v1.8.0

kubectl apply -f https://github.com/kubevirt/kubevirt/releases/download/${KVVERSION}/kubevirt-operator.yaml
kubectl apply -f https://github.com/kubevirt/kubevirt/releases/download/${KVVERSION}/kubevirt-cr.yaml
```

Esperar ~3 minutos. Verificar:

```bash
kubectl get kubevirt kubevirt -n kubevirt -o jsonpath='{.status.phase}'
# Debe mostrar: Deployed

kubectl get pods -n kubevirt
# Todos deben estar Running
```

Si los pods quedan en `Pending` por node affinity:

```bash
for NODE in $(kubectl get nodes -o jsonpath='{.items[*].metadata.name}'); do
  kubectl label node $NODE node-role.kubernetes.io/control-plane=""
done
```

---

## Paso 5 — Instalar virtctl (CLI de KubeVirt)

**¿Por qué?** `virtctl` permite interactuar con VMs (console, start, stop). Debe coincidir con la versión del servidor. La máquina de desarrollo es ARM64 — descargar el binario correcto.

```bash
KVVERSION=$(kubectl get kubevirt kubevirt -n kubevirt -o jsonpath='{.status.observedKubeVirtVersion}')

# ARM64 (MacBook M5 / VM Debian ARM64)
curl -L -o virtctl \
  https://github.com/kubevirt/kubevirt/releases/download/${KVVERSION}/virtctl-${KVVERSION}-linux-arm64
chmod +x virtctl
sudo mv virtctl /usr/local/bin/
virtctl version
```

---

## Paso 6 — Habilitar Gateway API en GKE

**¿Por qué dos pasos?** Gateway API en GKE requiere: (1) instalar los CRDs para que Kubernetes reconozca los tipos `Gateway`/`HTTPRoute`, y (2) habilitar el controlador GKE que procesa esos recursos y crea el Load Balancer.

**Paso 6a — Instalar CRDs upstream:**
```bash
kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.2.0/standard-install.yaml
```

**Paso 6b — Habilitar controlador GKE:**
```bash
gcloud container clusters update mumk8s-cluster \
  --gateway-api=standard \
  --zone us-east1-b \
  --project mumk8s
```

Esperar ~2 minutos. Verificar que el clúster vuelve a `RUNNING`:
```bash
gcloud container clusters describe mumk8s-cluster \
  --zone us-east1-b --project mumk8s --format='get(status)'
```

---

## Paso 7 — Verificar VM Zot (ya existe)

**¿Qué es Zot?** Registry OCI privado. Almacena las imágenes AMD64. Corre en una VM GCP separada del clúster (persiste aunque el clúster se elimine).

```bash
curl http://34.68.174.65:5000/v2/_catalog
# Debe mostrar: {"repositories":["go-client","go-consumer","go-server","rust-api"]}
```

Si la VM fue detenida:
```bash
gcloud compute instances start zot-registry --zone us-central1-a --project mumk8s
```

Si la VM fue eliminada, recrearla:
```bash
gcloud compute instances create zot-registry \
  --zone us-central1-a \
  --machine-type n1-standard-1 \
  --image-family debian-12 \
  --image-project debian-cloud \
  --project mumk8s

gcloud compute firewall-rules create allow-zot \
  --allow tcp:5000 \
  --source-ranges 0.0.0.0/0 \
  --project mumk8s

gcloud compute ssh zot-registry --zone us-central1-a --project mumk8s
# Dentro de la VM:
sudo apt-get update && sudo apt-get install -y docker.io
sudo systemctl start docker && sudo systemctl enable docker
sudo docker run -d -p 5000:5000 --name zot --restart always ghcr.io/project-zot/zot-linux-amd64:latest
exit
```

---

## Paso 8 — Build de imágenes AMD64 y push a Zot

**¿Por qué `--platform linux/amd64` desde ARM64?** Los nodos GKE son x86/AMD64. Las imágenes deben ser AMD64. Docker buildx con QEMU permite cross-compilar desde ARM64 → AMD64 de forma transparente.

### Prerequisitos (solo primera vez)

```bash
# Configurar Docker para registry inseguro
echo '{"insecure-registries": ["34.68.174.65:5000"]}' | sudo tee /etc/docker/daemon.json
sudo systemctl restart docker

# Crear builder con soporte para registry insecure y AMD64
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

docker buildx build --platform linux/amd64 -f Dockerfile.go-client   -t 34.68.174.65:5000/go-client:latest   --push .
docker buildx build --platform linux/amd64 -f Dockerfile.go-server   -t 34.68.174.65:5000/go-server:latest   --push .
docker buildx build --platform linux/amd64 -f Dockerfile.go-consumer -t 34.68.174.65:5000/go-consumer:latest --push .
docker buildx build --platform linux/amd64 -f rust-api/Dockerfile    -t 34.68.174.65:5000/rust-api:latest    --push rust-api/

# Verificar
curl http://34.68.174.65:5000/v2/_catalog
```

---

## Paso 9 — Configurar registry inseguro en nodos GKE (certs.d)

**¿Por qué certs.d y no mirrors?** GKE 1.35 usa containerd 2.x con `config_path=/etc/containerd/certs.d`. En containerd 2.x, `registry.mirrors` y `config_path` son mutuamente excluyentes — si coexisten, `mirrors` es silenciosamente ignorado. La única forma correcta es crear `hosts.toml` en el directorio `certs.d`.

Repetir para los 3 nodos:

```bash
# Ver IPs externas de los nodos
kubectl get nodes -o wide

# SSH a cada nodo
gcloud compute ssh <NOMBRE_NODO> --zone us-east1-b --project mumk8s
```

Dentro de cada nodo:

```bash
# Eliminar secciones mirrors/configs si existen
sudo python3 << 'PYEOF'
with open('/etc/containerd/config.toml', 'r') as f:
    lines = f.readlines()
output = []
skip = False
for line in lines:
    if 'registry.mirrors.' in line or 'registry.configs.' in line:
        skip = True
        continue
    elif line.startswith('[') and skip:
        skip = False
    if not skip:
        output.append(line)
with open('/etc/containerd/config.toml', 'w') as f:
    f.writelines(output)
print("Listo")
PYEOF

# Verificar que solo queda config_path (sin mirrors)
grep -n "mirrors\|configs\|config_path" /etc/containerd/config.toml

# Agregar config_path si no existe
grep "config_path" /etc/containerd/config.toml || sudo tee -a /etc/containerd/config.toml << 'EOF'

[plugins."io.containerd.grpc.v1.cri".registry]
  config_path = "/etc/containerd/certs.d"
EOF

# Crear hosts.toml para Zot
sudo mkdir -p /etc/containerd/certs.d/34.68.174.65:5000
sudo tee /etc/containerd/certs.d/34.68.174.65:5000/hosts.toml << 'EOF'
server = "http://34.68.174.65:5000"

[host."http://34.68.174.65:5000"]
  capabilities = ["pull", "resolve"]
  skip_verify = true
EOF

# Preservar mirror de docker.io
sudo mkdir -p /etc/containerd/certs.d/docker.io
sudo tee /etc/containerd/certs.d/docker.io/hosts.toml << 'EOF'
server = "https://registry-1.docker.io"

[host."https://mirror.gcr.io"]
  capabilities = ["pull", "resolve"]

[host."https://registry-1.docker.io"]
  capabilities = ["pull", "resolve"]
EOF

sudo systemctl restart containerd
sudo systemctl is-active containerd
exit
```

---

## Paso 10 — Aplicar manifiestos K8s

**¿Por qué este orden?** Los namespaces deben existir antes que cualquier otro recurso. RabbitMQ debe estar corriendo antes que los servicios Go. Las VMs KubeVirt tardan ~8-10 minutos en completar cloud-init (Grafana es 274MB).

```bash
kubectl apply -f deployments/namespaces.yaml
kubectl apply -f deployments/rabbitmq.yaml
kubectl apply -f deployments/go-services.yaml
kubectl apply -f deployments/rust-api.yaml
kubectl apply -f deployments/gateway.yaml
kubectl apply -f deployments/kubevirt.yaml
```

> Después de aplicar `kubevirt.yaml`, esperar 8-10 minutos para cloud-init de Grafana.

---

## Paso 11 — Fix manual Grafana si cloud-init falla

Si la VM de Grafana arranca pero Grafana no responde, el cloud-init falló (disco raíz 2GB insuficiente para instalar Grafana). El `kubevirt.yaml` ya incluye un `emptyDisk` de 10Gi montado en `/opt`, pero los **bind mounts no persisten entre reinicios de VM**.

Ejecutar dentro de la VM cada vez que reinicie:

```bash
virtctl console grafana-vm -n messaging
# Login: ubuntu / ubuntu
```

Dentro de la VM:

```bash
sudo mkdir -p /opt/grafana-share /opt/grafana-lib /opt/grafana-log
sudo mkdir -p /usr/share/grafana /var/lib/grafana /var/log/grafana
sudo mount --bind /opt/grafana-share /usr/share/grafana
sudo mount --bind /opt/grafana-lib /var/lib/grafana
sudo mount --bind /opt/grafana-log /var/log/grafana

# Si Grafana no está instalado aún:
sudo wget -q -O - https://apt.grafana.com/gpg.key | sudo gpg --dearmor > /tmp/grafana.gpg
sudo mv /tmp/grafana.gpg /etc/apt/keyrings/grafana.gpg
sudo chmod 644 /etc/apt/keyrings/grafana.gpg
echo "deb [signed-by=/etc/apt/keyrings/grafana.gpg] https://apt.grafana.com stable main" | sudo tee /etc/apt/sources.list.d/grafana.list
sudo apt-get update
sudo apt-get -o dir::cache=/opt/apt-cache install -y grafana
sudo grafana-cli --homepath /usr/share/grafana plugins install redis-datasource

sudo systemctl daemon-reload
sudo systemctl enable grafana-server
sudo systemctl start grafana-server
```

---

## Paso 12 — Verificar el sistema completo

```bash
# Todos los pods Running
kubectl get pods -A | grep -v Running | grep -v Completed

# VMs KubeVirt
kubectl get vmi -n messaging

# IP pública del Gateway (esperar PROGRAMMED=True y ADDRESS)
kubectl get gateway rust-api-gateway -n military-pipeline

# Servicios
kubectl get svc -n military-pipeline
kubectl get svc -n messaging
```

---

## Paso 13 — Probar el pipeline completo

```bash
# Enviar reporte de prueba
curl -X POST http://34.102.175.55/grpc-201905884 \
  -H "Content-Type: application/json" \
  -d '{"country":"CHN","warplanes_in_air":42,"warships_in_water":14,"timestamp":"2026-04-29T02:00:00Z"}'
# Debe responder: Report forwarded successfully

# Verificar datos en Valkey
kubectl run redis-check --rm -it --restart=Never \
  --image=redis:7-alpine -n messaging \
  -- redis-cli -h <VALKEY_VM_IP> -p 6379 KEYS "*"
# Debe mostrar ~10 keys: meminfo, rss_rank, cpu_rank, max/min warplanes/warships, modas, total_chn
```

---

## Paso 14 — Acceder a Grafana

```bash
kubectl port-forward -n messaging service/grafana-service 3000:3000
```

Abrir `http://localhost:3000` — usuario: `admin` / contraseña: `admin123`

Data source configurado: Redis → `<VALKEY_VM_IP>:6379` (sin contraseña)

### 11 paneles obligatorios

| # | Panel | Tipo viz | Tipo Redis | Key | Comando |
|---|---|---|---|---|---|
| 1 | Max Warplanes in Air | Stat | String | `max_warplanes_in_air` | GET |
| 2 | Min Warplanes in Air | Stat | String | `min_warplanes_in_air` | GET |
| 3 | Max Warships in Water | Stat | String | `max_warships_in_water` | GET |
| 4 | Min Warships in Water | Stat | String | `min_warships_in_water` | GET |
| 5 | Top Countries Warplanes | Bar/Table | Sorted Set | `rss_rank` | ZREVRANGE 0 4 WITH SCORES |
| 6 | Top Countries Warships | Bar/Table | Sorted Set | `cpu_rank` | ZREVRANGE 0 4 WITH SCORES |
| 7 | Mode Warplanes | Table | Hash | `warplanes_in_air_moda` | HGETALL |
| 8 | Mode Warships | Table | Hash | `warships_in_water_moda` | HGETALL |
| 9 | Info País CHN | Stat | String | `total_chn` | GET |
| 10 | Total Reports CHN | Stat | String | `total_chn` | GET |
| 11 | Time Series CHN | Table/Log | List | `meminfo` | LRANGE 0 -1 |

---

## Apagar el clúster (ahorrar crédito)

```bash
gcloud container clusters delete mumk8s-cluster --zone us-east1-b --project mumk8s --quiet
```

> La VM de Zot sigue corriendo y conserva las imágenes AMD64. Solo el clúster GKE se elimina.
> Para detener también la VM de Zot:
> ```bash
> gcloud compute instances stop zot-registry --zone us-central1-a --project mumk8s
> ```

---

## Errores conocidos

| Error | Causa | Solución |
|---|---|---|
| `Quota SSD_TOTAL_GB exceeded` | Cuota SSD agotada | `--disk-type pd-standard --disk-size 50` |
| `GCE_STOCKOUT` | Sin VMs disponibles en la zona | Cambiar zona (probar `us-east4-b`) |
| KubeVirt pods `Pending` por node affinity | GKE no expone control-plane | `kubectl label node <nodo> node-role.kubernetes.io/control-plane=""` |
| `Gateway API CRDs not found` | CRDs no instalados | Instalar CRDs upstream + `--gateway-api=standard` |
| Gateway `Waiting for controller` | Feature no habilitada en GKE | `gcloud container clusters update ... --gateway-api=standard` |
| `ImagePullBackOff` en pods del pipeline | containerd no confía en Zot HTTP | Aplicar fix certs.d en los 3 nodos (Paso 9) |
| Grafana no responde en puerto 3000 | cloud-init falló por disco lleno | Aplicar fix manual de bind mounts (Paso 11) |
| `E: You don't have enough free space` | Disco raíz VM 2GB insuficiente para Grafana 274MB | Bind mounts a emptyDisk 10Gi + `dir::cache=/opt/apt-cache` |
| `grafana-cli: homepath not found` | Grafana en path no estándar por bind mounts | `grafana-cli --homepath /usr/share/grafana ...` |
| `virtctl: SIGSEGV` | Binario AMD64 en máquina ARM64 | Descargar `virtctl-*-linux-arm64` |
| `CGO_ENABLED` crash en Alpine | Binario linkado a glibc, Alpine usa musl | `CGO_ENABLED=0` ya en Dockerfiles |
| `config_path cannot be set when mirrors is provided` | Conflicto containerd 2.x | Nunca mezclar mirrors y config_path — usar solo certs.d |
| `exec format error` en nodos | Imagen ARM64 en nodo AMD64 | Reconstruir con `--platform linux/amd64` |
| KubeVirt no puede crear VMs / sin `/dev/kvm` | Nodos ARM64 (N4A) no soportan nested virt | Usar nodos x86 (n2-standard-4) |
| go-consumer `CrashLoopBackOff` | Valkey VM aún en cloud-init | Esperar 4-5 min y `kubectl rollout restart deployment/go-consumer -n messaging` |
