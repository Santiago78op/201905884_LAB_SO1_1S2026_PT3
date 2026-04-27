# Apuntes de Despliegue — M.U.M.N.K8s

## Pipeline completo

```
[Locust] → [Gateway API] → [Rust API] → [Go Client] → [Go Server] → [RabbitMQ] → [Consumer] → [Valkey VM] → [Grafana VM]
```

---

## Namespaces

### ¿Qué es un Namespace?

En el kernel Linux, los namespaces aislan recursos del sistema entre procesos (`clone(CLONE_NEWNET)` crea un namespace de red aislado, por ejemplo). Kubernetes usa el mismo concepto a nivel lógico: un **Namespace** es una partición virtual dentro del clúster que agrupa recursos (Pods, Services, Deployments) y les da un scope de red y permisos propio.

### ¿Por qué dos Namespaces?

Separamos por responsabilidad funcional:

| Namespace | Qué vive aquí |
|---|---|
| `military-pipeline` | Rust API, Go gRPC Client, Go gRPC Server |
| `messaging` | RabbitMQ, Go Consumer |

Esto permite aplicar políticas de red, cuotas de recursos y RBAC por separado a cada grupo.

### DNS entre Namespaces

Un Pod en `military-pipeline` **no** puede resolver simplemente `rabbitmq` — necesita el FQDN completo:

```
rabbitmq.messaging.svc.cluster.local
```

El patrón es: `<service>.<namespace>.svc.cluster.local`

### apiVersion de recursos Kubernetes

Los recursos **core** de Kubernetes (`Namespace`, `Pod`, `Service`) usan `apiVersion: v1` porque pertenecen al grupo base de la API — el grupo se omite.

Recursos más nuevos usan el patrón `grupo/versión`:

| Recurso | apiVersion |
|---|---|
| Namespace, Pod, Service | `v1` |
| Deployment, ReplicaSet | `apps/v1` |
| HorizontalPodAutoscaler | `autoscaling/v2` |
| HTTPRoute (Gateway API) | `gateway.networking.k8s.io/v1` |

### YAML — namespaces.yaml

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: military-pipeline

---
apiVersion: v1
kind: Namespace
metadata:
  name: messaging
```

> Dos recursos en un mismo archivo YAML se separan con `---`.

---

## RabbitMQ

### ¿Qué es RabbitMQ en este pipeline?

RabbitMQ es el **broker de mensajería** — implementa el patrón productor/consumidor de SO1. El Go gRPC Server publica mensajes y el Go Consumer los lee de forma asíncrona. Esto desacopla la velocidad de ingesta de la velocidad de procesamiento.

### ¿Por qué vive en el Namespace `messaging`?

Separación de responsabilidades: RabbitMQ es infraestructura de mensajería, no un servicio de procesamiento. Junto al Consumer forman la capa de transporte asíncrono.

### Tipos de Service en Kubernetes

| Tipo | Accesible desde | Uso típico |
|---|---|---|
| `ClusterIP` (default) | Solo dentro del clúster | Comunicación interna entre servicios |
| `NodePort` | Nodo del clúster (IP:puerto) | Acceso externo en desarrollo |
| `LoadBalancer` | Internet (IP pública) | Servicios públicos en nube |

RabbitMQ usa `ClusterIP` porque solo los servicios Go necesitan accederlo — exponerlo externamente sería un riesgo de seguridad.

### Mecanismo selector/matchLabels

El Deployment encuentra sus Pods mediante labels. El campo `selector.matchLabels` del Deployment y el `template.metadata.labels` del Pod **deben coincidir exactamente**. Si no coinciden, el Deployment no puede gestionar sus propios Pods.

El Service también usa `selector` para encontrar los Pods a los que enrutar tráfico — por eso todos apuntan a `app: rabbitmq`.

### YAML — rabbitmq.yaml

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rabbitmq
  namespace: messaging
spec:
  replicas: 1
  selector:
    matchLabels:
      app: rabbitmq
  template:
    metadata:
      labels:
        app: rabbitmq
    spec:
      containers:
        - name: rabbitmq
          image: rabbitmq:3-management
          ports:
            - containerPort: 5672   # AMQP — mensajería
            - containerPort: 15672  # Management UI

---
apiVersion: v1
kind: Service
metadata:
  name: rabbitmq
  namespace: messaging
spec:
  selector:
    app: rabbitmq
  ports:
    - name: amqp
      port: 5672
      targetPort: 5672
    - name: management
      port: 15672
      targetPort: 15672
  # type: ClusterIP  ← valor por defecto, solo accesible dentro del clúster
```

### DNS para otros servicios

El Go Server (en `military-pipeline`) se conecta a RabbitMQ usando:
```
rabbitmq.messaging.svc.cluster.local:5672
```

---

## Go Services

### Namespaces por servicio

| Servicio | Namespace | Razón |
|---|---|---|
| `go-client` | `military-pipeline` | capa HTTP/gRPC |
| `go-server` | `military-pipeline` | procesamiento gRPC |
| `go-consumer` | `messaging` | consume de RabbitMQ |

### Variables de entorno

| Servicio | Variable | Valor | Por qué |
|---|---|---|---|
| `go-client` | `GRPC_SERVER_HOST` | `go-server:50051` | mismo namespace → nombre corto |
| `go-server` | `RABBITMQ_HOST` | `rabbitmq.messaging.svc.cluster.local` | namespace distinto → FQDN |
| `go-consumer` | `RABBITMQ_HOST` | `rabbitmq` | mismo namespace → nombre corto |
| `go-consumer` | `VALKEY_HOST` | `valkey-service` | placeholder KubeVirt |

### ¿Cuándo usar nombre corto vs FQDN?

- **Mismo namespace:** `go-server:50051` (K8s resuelve sin FQDN)
- **Namespace distinto:** `rabbitmq.messaging.svc.cluster.local:5672`

### go-consumer no tiene Service

El `go-consumer` solo inicia conexiones salientes (RabbitMQ, Valkey). Nadie lo llama. Un `Service` expone un Pod para tráfico **entrante** — sin tráfico entrante, no tiene sentido.

### Patrón de configuración con fallback

**Go:**
```go
host := os.Getenv("GRPC_SERVER_HOST")
if host == "" {
    host = "localhost:50051"
}
```

**Rust:**
```rust
let host = env::var("GRPC_CLIENT_HOST").unwrap_or_else(|_| "go-client:8080".into());
```

Permite que el YAML controle producción y el fallback permite desarrollo local sin configuración.

---

## Rust API + HPA

### ¿Qué es el HPA?

`HorizontalPodAutoscaler` escala automáticamente el número de réplicas de un Deployment en función de métricas (CPU, memoria, custom). Implementa el concepto de **elasticidad** en sistemas distribuidos.

### Millicores — unidad de CPU en Kubernetes

`1000m` = 1 core completo. `100m` = 10% de un core.

El HPA calcula: `(uso actual / requests) * 100 = % utilización`

Si el Pod usa `30m` y tiene `requests: 100m` → 30% → se activa el escalado.

### resources en el Deployment

```yaml
resources:
  requests:
    cpu: "100m"   # CPU reservada — base para el cálculo del HPA
  limits:
    cpu: "500m"   # techo máximo que puede consumir el contenedor
```

Sin `requests`, el HPA no puede calcular el porcentaje de uso y no funciona.

### YAML — rust-api.yaml

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rust-api
  namespace: military-pipeline
spec:
  replicas: 1
  selector:
    matchLabels:
      app: rust-api
  template:
    metadata:
      labels:
        app: rust-api
    spec:
      containers:
        - name: rust-api
          image: zot-registry:5000/rust-api:latest
          ports:
            - containerPort: 8080
          env:
            - name: GRPC_CLIENT_HOST
              value: "go-client:8080"
          resources:
            requests:
              cpu: "100m"
            limits:
              cpu: "500m"

---
apiVersion: v1
kind: Service
metadata:
  name: rust-api
  namespace: military-pipeline
spec:
  type: ClusterIP
  selector:
    app: rust-api
  ports:
    - port: 8080
      targetPort: 8080

---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: rust-api-hpa
  namespace: military-pipeline
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: rust-api
  minReplicas: 1
  maxReplicas: 3
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 30
```

---

## Gateway API

### Tres recursos, tres roles

| Recurso | Scope | Rol |
|---|---|---|
| `GatewayClass` | Cluster (sin namespace) | Define el tipo de controlador (GKE L7) |
| `Gateway` | Namespace | Punto de entrada con IP pública, listener en :80 |
| `HTTPRoute` | Namespace | Regla de enrutamiento: path → backend Service |

### parentRefs y namespace

El `HTTPRoute` referencia al `Gateway` con `parentRefs`. Si están en el **mismo** namespace, basta el nombre. Si estuvieran en namespaces distintos, se necesita `namespace:` explícito en el parentRef.

### YAML — gateway.yaml

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: GatewayClass
metadata:
  name: gke-l7-global-external-managed
spec:
  controllerName: networking.gke.io/gateway

---
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: rust-api-gateway
  namespace: military-pipeline
spec:
  gatewayClassName: gke-l7-global-external-managed
  listeners:
    - name: http
      protocol: HTTP
      port: 80
      allowedRoutes:
        namespaces:
          from: All

---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: rust-api-route
  namespace: military-pipeline
spec:
  parentRefs:
    - name: rust-api-gateway
  rules:
    - matches:
        - path:
            type: PathPrefix
            value: /grpc-201905884
      backendRefs:
        - name: rust-api
          port: 8080
```

---

## KubeVirt — Valkey y Grafana

### ¿Qué es KubeVirt?

KubeVirt extiende Kubernetes para correr **máquinas virtuales completas** como recursos del clúster. El recurso es `VirtualMachine` con `apiVersion: kubevirt.io/v1`. Se usa cuando la carga de trabajo necesita un OS completo (no un contenedor).

### Estructura de un VirtualMachine

```
VirtualMachine
└── spec.template
    └── spec
        ├── domain
        │   ├── resources.requests.memory   ← RAM de la VM
        │   └── devices
        │       ├── disks      ← nombres de discos (virtio)
        │       └── interfaces ← red (masquerade = NAT)
        ├── networks           ← tipo de red (pod = red del clúster)
        └── volumes
            ├── containerDisk      ← imagen Docker con el OS base
            └── cloudInitNoCloud   ← script bash de arranque
```

### running: true

Sin `spec.running: true` la VM existe pero está apagada. Debe estar en `true` para que arranque al aplicar el manifiesto.

### Cómo el Service selecciona una VM

KubeVirt inyecta automáticamente el label `kubevirt.io/domain: <nombre-vm>` en el Pod que gestiona cada VM. El Service usa ese label en su `selector` — mismo mecanismo que con Pods normales.

### cloud-init

`cloudInitNoCloud` con `userData` en formato `#cloud-config` ejecuta comandos al primer arranque de la VM. Con `runcmd` se instalan y arrancan los servicios.

### Conexión con el pipeline

`valkey-service` (nombre del Service de Valkey) coincide exactamente con el `VALKEY_HOST` configurado en el Deployment de `go-consumer`. El pipeline está conectado de extremo a extremo.

### YAML — kubevirt.yaml

Ver archivo `deployments/kubevirt.yaml` (Valkey VM + Service + Grafana VM + Service).

Namespaces: ambas VMs en `messaging`.
Puertos: Valkey `:6379`, Grafana `:3000`.