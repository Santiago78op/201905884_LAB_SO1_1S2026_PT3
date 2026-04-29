---
title: Dashboards Grafana — Requisitos del Proyecto
created: 2026-04-05
updated: 2026-04-29
tags: [grafana, dashboards, observabilidad, valkey]
status: activo
---

# Dashboards Grafana

## Fuente de Datos

- **Valkey** (Redis-compatible) desplegado en KubeVirt VM2
- Grafana se conecta a Valkey como data source tipo Redis

## Visualizaciones Requeridas (obligatorias)

| Panel | Descripción |
|---|---|
| Max. Aviones en Aire | Valor máximo global de `warplanes_in_air` |
| Min. Aviones en Aire | Valor mínimo global de `warplanes_in_air` |
| Max. Barcos en Mar | Valor máximo global de `warships_in_water` |
| Min. Barcos en Mar | Valor mínimo global de `warships_in_water` |
| Top Países — Aviones | Top países con más aviones en aire |
| Top Países — Barcos | Top países con más barcos en mar |
| Moda Aviones en Aire | Moda de `warplanes_in_air` |
| Moda Barcos en Mar | Moda de `warships_in_water` |
| País Asignado | Nombre del país asignado (basado en carnet) |
| Total Reportes País | Cantidad total de reportes del país asignado |
| Serie Temporal País | Evolución temporal de aviones y barcos del país asignado |

## País Asignado (basado en último dígito del carnet)

| Dígito | País |
|--------|------|
| 0, 1   | USA  |
| 2, 3   | RUS  |
| 4, 5   | CHN  |
| 6, 7   | ESP  |
| 8, 9   | GTM  |

## Estructura Sugerida del Dashboard

```
[Max Aviones] [Min Aviones] [Max Barcos] [Min Barcos]
[Moda Aviones]  [Moda Barcos] [Top5 Aviones] [Top5 Barcos]
[País Asignado + Total Reportes] [Serie Temporal País]
[# CARNET]
```

## Estructuras Valkey Reales (verificadas sesión 13 — 2026-04-29)

Keys confirmadas en Valkey:

```
ZINCRBY rss_rank <valor> <country>          # ranking aviones por país
ZINCRBY cpu_rank <valor> <country>          # ranking barcos por país
SET max_warplanes_in_air <valor>            # máximo global aviones
SET min_warplanes_in_air <valor>            # mínimo global aviones
SET max_warships_in_water <valor>           # máximo global barcos
SET min_warships_in_water <valor>           # mínimo global barcos
HINCRBY warplanes_in_air_moda <val> 1       # moda aviones
HINCRBY warships_in_water_moda <val> 1      # moda barcos
LPUSH meminfo <json>                        # serie temporal (toda la pipeline)
INCR total_chn                              # contador reportes CHN
```

Datos verificados: `rss_rank` contiene `esp` con score `42`.

## Nota de Penalización

Grafana sin KubeVirt = **-60% de la nota final**. Es el criterio de mayor peso en la rúbrica (25 pts + penalización).

## Conexiones

- [[grafana]]
- [[valkey]]
- [[consumer]]
- [[proyecto-enunciado]]
