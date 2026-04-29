# KubeVirt

Extensión de Kubernetes para correr máquinas virtuales como recursos nativos del clúster.
Corre sobre [[GKE]].

---

## ¿Por qué VMs y no contenedores?

Valkey y Grafana corren en VMs completas (con su propio kernel) en lugar de contenedores. Esto cumple el requisito del proyecto de usar KubeVirt para estas cargas de trabajo.

## Requisitos en los nodos GKE

- Image type: `UBUNTU_CONTAINERD` (COS no soporta nested virtualization de forma confiable)
- Flag: `--enable-nested-virtualization` al crear el clúster

## Instalación (Operator Pattern)

Versión activa: **v1.8.x** (sesión 12 — 2026-04-28). Versiones anteriores usadas: v1.3.0 (descartada).

```bash
# 1. Instalar el operador
kubectl apply -f https://github.com/kubevirt/kubevirt/releases/download/v1.8.0/kubevirt-operator.yaml

# 2. Activar KubeVirt con el Custom Resource
kubectl apply -f https://github.com/kubevirt/kubevirt/releases/download/v1.8.0/kubevirt-cr.yaml

# Verificar
kubectl get kubevirt kubevirt -n kubevirt -o jsonpath='{.status.phase}'
# Debe retornar: Deployed
```

## VMs del proyecto

| VM | Namespace | IP | Servicio | Estado sesión 13 |
|---|---|---|---|---|
| `valkey-vm` | `messaging` | `10.64.129.9:6379` | redis-server (compatible Valkey) | RUNNING — datos verificados |
| `grafana-vm` | `messaging` | `10.64.130.14:3000` | Grafana dashboards | RUNNING — 4/11 paneles |

## Grafana VM — Problema de Disco y Solución (sesión 13 — 2026-04-29)

### Problema

Cloud-init falló durante el provisionamiento de la VM Grafana por falta de espacio en el disco raíz de 2 GB. Grafana no arrancaba.

### Solución: emptyDisk 10Gi + bind mounts manuales

Se agregó un `emptyDisk` de 10 Gi al VirtualMachine y se montó con bind mounts en la VM:

```bash
sudo mkdir -p /opt/grafana-share /opt/grafana-lib /opt/grafana-log
sudo mkdir -p /usr/share/grafana /var/lib/grafana /var/log/grafana
sudo mount --bind /opt/grafana-share /usr/share/grafana
sudo mount --bind /opt/grafana-lib /var/lib/grafana
sudo mount --bind /opt/grafana-log /var/log/grafana
sudo systemctl start grafana-server
```

> **ALERTA: los bind mounts no sobreviven reinicios.** Si la VM reinicia, ejecutar el bloque anterior antes de usar Grafana.

### Plugin Redis instalado

```bash
grafana-cli --homepath /usr/share/grafana plugins install redis-datasource
```

Data source configurado: tipo Redis, URL `10.64.129.9:6379`, sin autenticación.

## virtctl — Problema de Arquitectura (sesión 13)

`virtctl` en ARM64 lanzaba crash silencioso porque el binario descargado era AMD64. Solución: descargar el binario ARM64 explícitamente.

```bash
# Descargar binario correcto para ARM64
curl -L -o virtctl https://github.com/kubevirt/kubevirt/releases/download/v1.8.0/virtctl-v1.8.0-linux-arm64
chmod +x virtctl
sudo mv virtctl /usr/local/bin/
```

## Problema conocido: virt-operator en Pending (nodeAffinity)

KubeVirt v1.8.x tiene un `nodeAffinity` en el virt-operator que exige el label `node-role.kubernetes.io/control-plane=""`. GKE no expone el control-plane como nodo worker, así que ningún nodo tiene ese label por defecto.

Fix obligatorio en los 3 nodos antes de que virt-operator arranque:

```bash
kubectl label node gke-mumk8s-cluster-default-pool-1158e3a4-31wx node-role.kubernetes.io/control-plane=""
kubectl label node gke-mumk8s-cluster-default-pool-1158e3a4-dht6 node-role.kubernetes.io/control-plane=""
kubectl label node gke-mumk8s-cluster-default-pool-1158e3a4-j9qp node-role.kubernetes.io/control-plane=""
```

Estado sesión 12: todos los pods KubeVirt 1/1 Running tras aplicar el fix.

## Ver también

- [[gke]] — configuración del clúster con nested virtualization
- [[deployments/setup-guide.md]] — Paso 4 con comandos completos
