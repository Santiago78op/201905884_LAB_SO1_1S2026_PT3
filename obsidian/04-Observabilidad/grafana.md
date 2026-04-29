# Grafana

Visualización de métricas. Corre en VM KubeVirt (`grafana-vm`, namespace `messaging`).
Entrada: [[Valkey]]

---

## Acceso

- IP VM: `10.64.130.14`
- Puerto: `3000`
- URL: `http://10.64.130.14:3000`

## Data Source

- Tipo: Redis (plugin `redis-datasource`)
- URL: `10.64.129.9:6379` (VM Valkey)
- Sin autenticación

## Estado de Paneles (sesión 13 — 2026-04-29)

| # | Panel | Key Valkey | Tipo | Estado |
|---|---|---|---|---|
| 1 | Max. Aviones en Aire | `max_warplanes_in_air` | Stat / GET | CREADO |
| 2 | Min. Aviones en Aire | `min_warplanes_in_air` | Stat / GET | CREADO |
| 3 | Max. Barcos en Mar | `max_warships_in_water` | Stat / GET | CREADO |
| 4 | Min. Barcos en Mar | `min_warships_in_water` | Stat / GET | CREADO |
| 5 | Top Países — Aviones | `rss_rank` | — | PENDIENTE |
| 6 | Top Países — Barcos | `cpu_rank` | — | PENDIENTE |
| 7 | Moda Aviones en Aire | `warplanes_in_air_moda` | — | PENDIENTE |
| 8 | Moda Barcos en Mar | `warships_in_water_moda` | — | PENDIENTE |
| 9 | País Asignado | — | — | PENDIENTE |
| 10 | Total Reportes País | `total_chn` | — | PENDIENTE |
| 11 | Serie Temporal País | `meminfo` | — | PENDIENTE |

País asignado: **CHN** (carnet 201905884, último dígito = 4).

## Keys Valkey usadas por Consumer

| Key | Tipo Redis | Contenido |
|---|---|---|
| `rss_rank` | Sorted Set | Ranking por warplanes (ZINCRBY) |
| `cpu_rank` | Sorted Set | Ranking por warships (ZINCRBY) |
| `max_warplanes_in_air` | String | Máximo global de aviones |
| `min_warplanes_in_air` | String | Mínimo global de aviones |
| `max_warships_in_water` | String | Máximo global de barcos |
| `min_warships_in_water` | String | Mínimo global de barcos |
| `warplanes_in_air_moda` | Hash | Frecuencia por valor (HINCRBY) |
| `warships_in_water_moda` | Hash | Frecuencia por valor (HINCRBY) |
| `meminfo` | List | Serie temporal JSON |
| `total_chn` | Counter | Total reportes CHN (INCR) |

## Comandos Valkey útiles para verificar datos

```bash
# Verificar ranking aviones
ZREVRANGE rss_rank 0 4 WITHSCORES

# Verificar ranking barcos
ZREVRANGE cpu_rank 0 4 WITHSCORES

# Verificar serie temporal
LRANGE meminfo 0 -1

# Verificar max/min
GET max_warplanes_in_air
GET min_warplanes_in_air
```

## ALERTA: Bind Mounts No Persisten en Reinicios

Ver [[kubevirt]] — sección "Grafana VM — Problema de Disco y Solución". Si la VM reinicia, ejecutar los bind mounts manualmente antes de usar Grafana.

## Nota de Penalización

Grafana sin KubeVirt = **-60% de la nota final**. Es el criterio de mayor peso en la rúbrica.

## Conexiones

- [[kubevirt]]
- [[dashboards-grafana]]
- [[valkey]]
- [[consumer]]
