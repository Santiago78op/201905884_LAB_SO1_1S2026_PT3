# Locust — Generador de Carga

Locust es una herramienta de **load testing** (pruebas de carga). Simula miles de usuarios haciendo peticiones HTTP simultáneamente al sistema.

En términos de Sistemas Operativos: Locust crea múltiples **procesos/hilos concurrentes**, cada uno enviando peticiones HTTP en paralelo. Es equivalente a tener 500 usuarios usando la aplicación al mismo tiempo.

## Ubicación en el pipeline

```
[Locust] ──► [Gateway API] → [Rust API] → [Go Client] → ...
    ↑
 generador de tráfico
```

## ¿Por qué existe en el proyecto?

1. **Generar tráfico real** — sin Locust, el pipeline no recibe datos. No hay nada que procesar ni visualizar en Grafana.

2. **Activar el HPA** — el Horizontal Pod Autoscaler escala la Rust API cuando el CPU supera 30%. Sin carga suficiente, el CPU se queda en 0% y el HPA nunca escala.

```
Sin Locust → CPU 0% → HPA no escala → no se puede demostrar autoscaling
```

## Conceptos clave de Locust

### HttpUser

Clase base que representa un usuario virtual. Cada instancia es un usuario simulado que corre en paralelo.

```python
class MiUsuario(HttpUser):
    wait_time = between(1, 3)   # espera entre 1 y 3 segundos entre tareas
    
    @task
    def enviar_reporte(self):
        self.client.post("/ruta", json={...})
```

### @task

Decorador que marca un método como tarea a ejecutar. Locust llama a estos métodos repetidamente durante la prueba.

```python
@task
def mi_tarea(self):
    # se ejecuta una y otra vez por cada usuario virtual
    pass
```

Se puede indicar peso relativo: `@task(3)` se ejecuta 3 veces más que `@task(1)`.

### wait_time = between(min, max)

Define el **tiempo de espera entre tareas** de cada usuario virtual, en segundos. Simula el "think time" de un usuario real — nadie hace click sin pausa.

```python
wait_time = between(1, 3)   # espera aleatoria entre 1s y 3s
```

Sin `wait_time`, los usuarios bombardean el sistema sin pausa — no es realista y puede saturarlo de forma artificial.

Concepto SO1 relacionado: **think time** en modelos de sistemas interactivos.

### self.client

Cliente HTTP pre-configurado con el `host` del servidor. Se usa para hacer peticiones:

```python
self.client.post("/endpoint", json={"key": "value"})
self.client.get("/endpoint")
```

El `host` se define al lanzar Locust: `--host http://mi-servicio:8080`

## Imports necesarios

```python
from locust import HttpUser, task, between
import random
from datetime import datetime
```

| Import | Para qué |
|---|---|
| `HttpUser` | clase base del usuario virtual |
| `task` | decorador que marca métodos como tareas |
| `between` | define el rango de wait_time |
| `random` | generar país, warplanes y warships aleatorios |
| `datetime` | obtener timestamp actual en formato ISO 8601 |

## Payload del proyecto

```json
{
  "country": "ESP",
  "warplanes_in_air": 42,
  "warships_in_water": 14,
  "timestamp": "2026-03-12T20:15:30Z"
}
```

**Reglas de generación:**

| Campo | Tipo | Rango |
|---|---|---|
| `country` | string | aleatorio entre `["USA", "RUS", "CHN", "ESP", "GTM"]` |
| `warplanes_in_air` | int | 0 – 50 |
| `warships_in_water` | int | 0 – 30 |
| `timestamp` | string ISO 8601 | momento actual |

**Cómo generar el timestamp actual:**
```python
datetime.utcnow().isoformat() + "Z"
# produce: "2026-04-27T15:30:00.000000Z"
```

**Cómo elegir un país aleatorio:**
```python
COUNTRIES = ["USA", "RUS", "CHN", "ESP", "GTM"]
country = random.choice(COUNTRIES)
```

## Cómo ejecutar Locust

```bash
locust -f locustfile.py --host http://<gateway-ip> --users 100 --spawn-rate 10
```

| Flag | Significado |
|---|---|
| `-f locustfile.py` | archivo con la definición de usuarios |
| `--host` | URL base del sistema a probar |
| `--users` | número total de usuarios virtuales |
| `--spawn-rate` | cuántos usuarios se crean por segundo hasta llegar al total |

También tiene una UI web en `http://localhost:8089` si se corre sin `--headless`.

## Conexión con HPA

El HPA de Kubernetes monitorea el CPU de los Pods. Cuando Locust genera suficiente carga:

```
Locust → muchas peticiones → CPU Rust API sube > 30% → HPA crea más réplicas (hasta 3)
```

Cuando Locust se detiene:
```
Sin peticiones → CPU baja → HPA elimina réplicas sobrantes (scale down)
```
