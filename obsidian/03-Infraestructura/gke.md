# GKE

Orquestación principal del sistema.
Contiene [[Gateway API]], [[Rust API]], [[Go gRPC Server]], [[RabbitMQ]], [[Valkey]] y [[Grafana]].

---

## Estado del clúster (sesión 13 — 2026-04-29)

**Estado al cierre de sesión 13:**

| Componente | Estado |
|---|---|
| Clúster GKE n2-standard-4 | RUNNING |
| KubeVirt 1.8.x | RUNNING |
| RabbitMQ | RUNNING |
| VM Valkey (10.64.129.9) | RUNNING |
| VM Grafana (10.64.130.14) | RUNNING |
| Namespaces military-pipeline / messaging | APLICADOS |
| Todos los pods del pipeline | Running (ImagePullBackOff resuelto) |
| Gateway API | RUNNING — IP `34.102.175.55` |
| Pipeline E2E | VERIFICADO — curl devuelve "Report forwarded successfully" |
| Datos en Valkey | VERIFICADOS — `rss_rank` contiene `esp` score `42` |
| Grafana + Redis plugin | INSTALADO en VM, data source conectado |
| Paneles Grafana | 4/11 creados (max/min warplanes, max/min warships) |

**Pendiente sesión 14 (DEADLINE 30/04/2026):** 7 paneles Grafana restantes, Locust carga, evidencia final UEDI.

---

## Configuración del clúster (sesión 12 — 2026-04-28)

**Estado histórico sesión 12:**

| Componente | Estado |
|---|---|
| Clúster GKE n2-standard-4 | RUNNING |
| KubeVirt 1.8.x | RUNNING |
| RabbitMQ | RUNNING |
| VM Valkey (10.64.129.9) | RUNNING |
| VM Grafana (10.64.128.15) | RUNNING |
| Namespaces military-pipeline / messaging | APLICADOS |
| Pods Go services y rust-api | ImagePullBackOff — fix containerd pendiente |

---

| Parámetro | Valor | Razón |
|---|---|---|
| Nombre | `mumk8s-cluster` | |
| Zona | `us-east1-b` | Disponibilidad n2-standard-4 |
| Machine type | `n2-standard-4` | x86/AMD64, nested virtualization soportada |
| Nodos | 3 fijos | Sin autoscaling |
| Node autoscaling | Desactivado | HPA maneja escala de pods |
| Image type | `UBUNTU_CONTAINERD` | Requerida para nested virtualization |
| SO | Ubuntu 24.04 LTS | |
| containerd | 2.1.5 | |
| Nested virtualization | Habilitada | Requerida por KubeVirt (/dev/kvm) |
| Disco | pd-standard, 50GB | Evita errores de cuota SSD |

## Nodos activos (sesión 12)

| Nodo | IP interna |
|---|---|
| gke-mumk8s-cluster-default-pool-1158e3a4-31wx | 10.142.0.12 |
| gke-mumk8s-cluster-default-pool-1158e3a4-dht6 | 10.142.0.10 |
| gke-mumk8s-cluster-default-pool-1158e3a4-j9qp | 10.142.0.11 |

## Decisión: N4A ARM64 descartado

N4A (ARM64/Ampere Altra) fue evaluado y descartado porque **GCP no expone FEAT_NV en instancias ARM64**, lo que impide nested virtualization. KubeVirt requiere `/dev/kvm` que solo existe cuando nested virtualization está habilitada. Se migró a `n2-standard-4` (x86/AMD64) que sí soporta nested virtualization en GCP.

## Comando de creación (sesión 12)

```bash
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

## containerd 2.1.5 — fix certs.d para registry HTTP (sesión 12, 2026-04-28)

### Problema

El enfoque `registry.mirrors` en `config.toml` **no funciona** para registros HTTP puros en containerd 2.1.5. Los pods quedan en `ImagePullBackOff` con:

```
http: server gave HTTP response to HTTPS client
```

Adicionalmente, containerd 2.x lanza error fatal si `mirrors` y `config_path` coexisten:

```
`mirrors` cannot be set when `config_path` is provided
```

### Fix correcto: enfoque certs.d (ejecutar en cada nodo)

**Paso 1 — Limpiar mirrors/configs del config.toml:**

```bash
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
PYEOF
```

**Paso 2 — Crear hosts.toml para Zot (HTTP inseguro):**

```bash
sudo mkdir -p /etc/containerd/certs.d/34.68.174.65:5000
sudo tee /etc/containerd/certs.d/34.68.174.65:5000/hosts.toml << 'EOF'
server = "http://34.68.174.65:5000"
[host."http://34.68.174.65:5000"]
  capabilities = ["pull", "resolve"]
  skip_verify = true
EOF
```

**Paso 3 — Preservar mirror GKE para docker.io y agregar config_path:**

```bash
sudo mkdir -p /etc/containerd/certs.d/docker.io
sudo tee /etc/containerd/certs.d/docker.io/hosts.toml << 'EOF'
server = "https://registry-1.docker.io"
[host."https://mirror.gcr.io"]
  capabilities = ["pull", "resolve"]
[host."https://registry-1.docker.io"]
  capabilities = ["pull", "resolve"]
EOF

# Agregar config_path solo si no existe
grep "config_path" /etc/containerd/config.toml || sudo tee -a /etc/containerd/config.toml << 'CONFIG'
[plugins."io.containerd.grpc.v1.cri".registry]
  config_path = "/etc/containerd/certs.d"
CONFIG

sudo systemctl restart containerd
```

> **Nota:** La IP `34.68.174.65` es la IP externa del nodo donde corre Zot. Si el clúster se recrea, esta IP cambia y hay que actualizar los `hosts.toml` en los 3 nodos.

## ~~Configuración anterior: N4A ARM64 (sesión 11 — descartada)~~

~~Machine type `n4a-standard-4`, ARM64. Descartado por falta de soporte FEAT_NV en GCP.~~

## Gateway API (sesión 13 — 2026-04-29)

**Estado:** RUNNING. IP externa: `34.102.175.55`. Ruta `/grpc-201905884` → `rust-api:8080`.

Pipeline E2E verificado:
```bash
curl http://34.102.175.55/grpc-201905884
# Respuesta: "Report forwarded successfully"
```

### Instalación completa

```bash
# 1. Instalar CRDs
kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.2.0/standard-install.yaml

# 2. Habilitar feature en GKE (obligatorio — sin esto el controlador queda en "Waiting for controller")
gcloud container clusters update mumk8s-cluster \
  --gateway-api=standard \
  --zone us-east1-b \
  --project mumk8s
```

> **Problema conocido:** Si el Gateway queda en estado `Waiting for controller`, la causa es que el feature no fue habilitado en GKE. El `kubectl apply` de los CRDs solos no es suficiente — siempre se necesita el comando `gcloud container clusters update`.

## Namespaces

| Namespace | Contenido |
|---|---|
| `military-pipeline` | Rust API, Go Client, Go Server, HPA, Gateway |
| `messaging` | RabbitMQ, Go Consumer, KubeVirt VMs (Valkey, Grafana) |
| `kubevirt` | Operador KubeVirt |

## Ver también

- [[deployments/setup-guide.md]] — guía canónica de reinstalación paso a paso
- [[kubevirt]] — VMs Valkey y Grafana
- [[zot]] — registry de imágenes ARM64
