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

## Estado Paneles (sesión 16 — 2026-04-29) — COMPLETO ✅

| # | Panel | Estado | Configuración Grafana |
|---|---|---|---|
| 1 | Max Warplanes | ✅ | Redis Core, GET, `max_warplanes_in_air`, Stat |
| 2 | Min Warplanes | ✅ | Redis Core, GET, `min_warplanes_in_air`, Stat |
| 3 | Max Warships | ✅ | Redis Core, GET, `max_warships_in_water`, Stat |
| 4 | Min Warships | ✅ | Redis Core, GET, `min_warships_in_water`, Stat |
| 5 | Top Warplanes (rss_rank) | ✅ | Redis Core, ZRANGE, `rss_rank`, Index 0 -1, Bar chart |
| 6 | Top Warships (cpu_rank) | ✅ | Redis Core, ZRANGE, `cpu_rank`, Index 0 -1, Bar chart |
| 7 | Moda Warplanes | ✅ | Redis Core, GET, `warplanes_in_air_moda_winner`, Stat |
| 8 | Moda Warships | ✅ | Redis Core, GET, `warships_in_water_moda_winner`, Stat |
| 9 | País Asignado | ✅ | Text panel, texto fijo "CHN" |
| 10 | Total Reports CHN | ✅ | Redis Core, GET, `total_chn`, Stat |
| 11 | Time Series CHN | ✅ | CLI, LRANGE meminfo 0 99 + Extract fields JSON + Convert timestamp Time |

## Decisiones de diseño implementadas

### Moda — dos capas en Valkey
- `warplanes_in_air_moda` → Hash frecuencias (HINCRBY)
- `warplanes_in_air_moda_winner` → valor ganador actual (GET directo desde Grafana)
- `warplanes_in_air_moda_winner_count` → conteo del ganador (comparación interna)
- Razón: lógica en el Consumer, no en Grafana

### Rankings — ZINCRBY acumulativo
- `rss_rank` y `cpu_rank` usan ZINCRBY — acumula totales por país
- Grafana usa Redis Core ZRANGE (no CLI) para obtener columnas estructuradas

### Time Series CHN — meminfo filtrado
- Consumer solo hace LPUSH a `meminfo` cuando `country == CHN`
- Grafana: CLI LRANGE + transformación Extract fields JSON + Convert timestamp

## Estructuras Valkey Reales (verificadas sesión 16 — 2026-04-29)

14 keys activas:

```
ZINCRBY rss_rank <valor> <country>          # ranking acumulado aviones
ZINCRBY cpu_rank <valor> <country>          # ranking acumulado barcos
SET max_warplanes_in_air <valor>            # máximo global aviones
SET min_warplanes_in_air <valor>            # mínimo global aviones
SET max_warships_in_water <valor>           # máximo global barcos
SET min_warships_in_water <valor>           # mínimo global barcos
HINCRBY warplanes_in_air_moda <val> 1       # distribución frecuencias aviones
SET warplanes_in_air_moda_winner <val>      # moda aviones (valor ganador)
SET warplanes_in_air_moda_winner_count <n>  # conteo del ganador
HINCRBY warships_in_water_moda <val> 1      # distribución frecuencias barcos
SET warships_in_water_moda_winner <val>     # moda barcos (valor ganador)
SET warships_in_water_moda_winner_count <n> # conteo del ganador
LPUSH meminfo <json>                        # serie temporal CHN únicamente
INCR total_chn                              # contador reportes CHN
```

## Nota de Penalización

Grafana sin KubeVirt = **-60% de la nota final**. Es el criterio de mayor peso en la rúbrica (25 pts + penalización).

## Conexiones

- [[grafana]]
- [[valkey]]
- [[consumer]]
- [[proyecto-enunciado]]
