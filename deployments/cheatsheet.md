# Cheatsheet — M.U.M.N.K8s

Comandos rápidos para la calificación y recuperación del sistema.

---

## IPs y referencias críticas

| Recurso | IP | Puerto |
|---|---|---|
| Gateway API (entrada externa) | `34.102.175.55` | 80 |
| Valkey VM | `10.64.129.9` | 6379 |
| Grafana VM | `10.64.130.14` | 3000 |
| Zot registry | `34.68.174.65` | 5000 |
| Ruta pública | `/grpc-201905884` | — |

---

## Verificación rápida del sistema (para calificación)

```bash
# 1. Todos los pods Running
kubectl get pods -A | grep -v Running | grep -v Completed

# 2. VMs KubeVirt activas
kubectl get vmi -n messaging

# 3. IP del Gateway
kubectl get gateway rust-api-gateway -n military-pipeline

# 4. HPA estado
kubectl get hpa -n military-pipeline

# 5. Pipeline E2E — debe responder "Report forwarded successfully"
curl -X POST http://34.102.175.55/grpc-201905884 \
  -H "Content-Type: application/json" \
  -d '{"country":"CHN","warplanes_in_air":42,"warships_in_water":14,"timestamp":"2026-04-29T02:00:00Z"}'

# 6. Keys en Valkey (deben aparecer ~14 keys)
kubectl run redis-check --image=redis:alpine --rm -it --restart=Never -- redis-cli -h 10.64.129.9 KEYS "*"

# 7. Verificar imágenes en Zot
curl http://34.68.174.65:5000/v2/_catalog
```

---

## Acceder a Grafana

```bash
kubectl port-forward -n messaging service/grafana-service 3000:3000
# Abrir: http://localhost:3000
# Usuario: admin / Contraseña: (la que configuraste)
```

---

## Recuperar Grafana si se cae

### 1. Entrar a la VM
```bash
virtctl console grafana-vm -n messaging
# Login: ubuntu / ubuntu
```

### 2. Aplicar bind mounts y arrancar
```bash
sudo mkdir -p /opt/grafana-share /opt/grafana-lib /opt/grafana-log
sudo mkdir -p /usr/share/grafana /var/lib/grafana /var/log/grafana
sudo mount --bind /opt/grafana-share /usr/share/grafana
sudo mount --bind /opt/grafana-lib /var/lib/grafana
sudo mount --bind /opt/grafana-log /var/log/grafana
sudo systemctl start grafana-server
sudo systemctl is-active grafana-server
```

### 3. Si /opt/grafana-share está vacío — reinstalar Grafana
```bash
wget -q -O - https://apt.grafana.com/gpg.key | sudo gpg --dearmor | sudo tee /etc/apt/keyrings/grafana.gpg > /dev/null
echo "deb [signed-by=/etc/apt/keyrings/grafana.gpg] https://apt.grafana.com stable main" | sudo tee /etc/apt/sources.list.d/grafana.list
sudo apt-get update
sudo apt-get -o dir::cache=/opt/apt-cache install -y grafana
sudo grafana-cli --homepath /usr/share/grafana plugins install redis-datasource
sudo systemctl daemon-reload
sudo systemctl enable grafana-server
sudo systemctl start grafana-server
```

---

## Limpiar Valkey y repoblar

```bash
# Limpiar todo
kubectl run redis-flush --image=redis:alpine --rm -it --restart=Never -- redis-cli -h 10.64.129.9 FLUSHALL

# Fix si Valkey bloquea escrituras por RDB error
kubectl run redis-fix --image=redis:alpine --rm -it --restart=Never -- redis-cli -h 10.64.129.9 CONFIG SET stop-writes-on-bgsave-error no

# Luego arrancar Locust para repoblar
cd /home/julian/Documents/201905884_LAB_SO1_1S2026_PT3/locust
locust -f locustfile.py --host http://34.102.175.55
# UI: http://localhost:8089 — 100 usuarios, spawn rate 10
```

---

## Arrancar Locust

```bash
cd /home/julian/Documents/201905884_LAB_SO1_1S2026_PT3/locust

# Con interfaz web
locust -f locustfile.py --host http://34.102.175.55

# Headless (sin UI)
locust -f locustfile.py --host http://34.102.175.55 --headless -u 100 -r 10
```

---

## Inspeccionar datos en Valkey

```bash
# Ver todas las keys
kubectl run redis-check --image=redis:alpine --rm -it --restart=Never -- redis-cli -h 10.64.129.9 KEYS "*"

# Ver ranking de aviones
kubectl run redis-check --image=redis:alpine --rm -it --restart=Never -- redis-cli -h 10.64.129.9 ZREVRANGE rss_rank 0 4 WITHSCORES

# Ver ranking de barcos
kubectl run redis-check --image=redis:alpine --rm -it --restart=Never -- redis-cli -h 10.64.129.9 ZREVRANGE cpu_rank 0 4 WITHSCORES

# Ver moda de aviones (valor ganador)
kubectl run redis-check --image=redis:alpine --rm -it --restart=Never -- redis-cli -h 10.64.129.9 GET warplanes_in_air_moda_winner

# Ver max/min
kubectl run redis-check --image=redis:alpine --rm -it --restart=Never -- redis-cli -h 10.64.129.9 GET max_warplanes_in_air
kubectl run redis-check --image=redis:alpine --rm -it --restart=Never -- redis-cli -h 10.64.129.9 GET min_warplanes_in_air

# Ver total CHN
kubectl run redis-check --image=redis:alpine --rm -it --restart=Never -- redis-cli -h 10.64.129.9 GET total_chn

# Ver últimos 5 reportes CHN
kubectl run redis-check --image=redis:alpine --rm -it --restart=Never -- redis-cli -h 10.64.129.9 LRANGE meminfo 0 4
```

---

## Rebuild y redespliegue de servicios

```bash
cd /home/julian/Documents/201905884_LAB_SO1_1S2026_PT3

# Go Consumer
docker buildx build --platform linux/amd64 -f Dockerfile.go-consumer -t 34.68.174.65:5000/go-consumer:latest --push .
kubectl rollout restart deployment/go-consumer -n messaging
kubectl rollout status deployment/go-consumer -n messaging

# Go Client
docker buildx build --platform linux/amd64 -f Dockerfile.go-client -t 34.68.174.65:5000/go-client:latest --push .
kubectl rollout restart deployment/go-client -n military-pipeline

# Go Server
docker buildx build --platform linux/amd64 -f Dockerfile.go-server -t 34.68.174.65:5000/go-server:latest --push .
kubectl rollout restart deployment/go-server -n military-pipeline

# Rust API
docker buildx build --platform linux/amd64 -f rust-api/Dockerfile -t 34.68.174.65:5000/rust-api:latest --push rust-api/
kubectl rollout restart deployment/rust-api -n military-pipeline
```

---

## Fix nodos GKE — ImagePullBackOff desde Zot

Si un pod no puede hacer pull desde Zot (error: `http: server gave HTTP response to HTTPS client`):

```bash
# Identificar nodo del pod fallido
kubectl describe pod <nombre-pod> -n <namespace> | grep "Node:"

# SSH al nodo
gcloud compute ssh <nombre-nodo> --zone us-east1-b --project mumk8s

# Dentro del nodo — limpiar mirrors y agregar config_path
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

grep "config_path" /etc/containerd/config.toml || sudo tee -a /etc/containerd/config.toml << 'EOF'

[plugins."io.containerd.grpc.v1.cri".registry]
  config_path = "/etc/containerd/certs.d"
EOF

sudo mkdir -p /etc/containerd/certs.d/34.68.174.65:5000
sudo tee /etc/containerd/certs.d/34.68.174.65:5000/hosts.toml << 'EOF'
server = "http://34.68.174.65:5000"

[host."http://34.68.174.65:5000"]
  capabilities = ["pull", "resolve"]
  skip_verify = true
EOF

sudo systemctl restart containerd && sudo systemctl is-active containerd
exit
```

---

## Paneles Grafana — configuración exacta

| # | Panel | Viz | Type | Command | Key |
|---|---|---|---|---|---|
| 1 | Max Warplanes | Stat | Redis Core | GET | `max_warplanes_in_air` |
| 2 | Min Warplanes | Stat | Redis Core | GET | `min_warplanes_in_air` |
| 3 | Max Warships | Stat | Redis Core | GET | `max_warships_in_water` |
| 4 | Min Warships | Stat | Redis Core | GET | `min_warships_in_water` |
| 5 | Top Countries Warplanes | Bar chart | Redis Core | ZRANGE | `rss_rank` (Index 0 a -1) |
| 6 | Top Countries Warships | Bar chart | Redis Core | ZRANGE | `cpu_rank` (Index 0 a -1) |
| 7 | Mode Warplanes | Stat | Redis Core | GET | `warplanes_in_air_moda_winner` |
| 8 | Mode Warships | Stat | Redis Core | GET | `warships_in_water_moda_winner` |
| 9 | País Asignado | Text | — | — | Texto fijo: `CHN` |
| 10 | Total Reports CHN | Stat | Redis Core | GET | `total_chn` |
| 11 | Time Series CHN | Time series | CLI | LRANGE meminfo 0 99 | + Transform: Extract fields JSON + Convert timestamp a Time |

---

## Logs de servicios

```bash
# Consumer
kubectl logs -l app=go-consumer -n messaging -f

# Go Server
kubectl logs -l app=go-server -n military-pipeline -f

# Rust API
kubectl logs -l app=rust-api -n military-pipeline -f

# Go Client
kubectl logs -l app=go-client -n military-pipeline -f

# RabbitMQ
kubectl logs -l app=rabbitmq -n messaging -f
```
