"""
M.U.M.N.K8s — Sub-agentes de validación (4 agentes especializados)
Cada agente lee archivos del proyecto y evalúa un área específica.
"""

import json
from pathlib import Path
from typing import Any
import anthropic

PROJECT_ROOT = Path(__file__).parent.parent.parent
MODEL = "claude-sonnet-4-6"

# ─────────────────────────────────────────────────────────────────────────────
# CONTEXTO COMPARTIDO — inyectado en todos los agentes
# ─────────────────────────────────────────────────────────────────────────────
SHARED_CONTEXT = """
════════════════════════════════════════════════════════════
CONTEXTO COMPLETO DEL PROYECTO M.U.M.N.K8s
════════════════════════════════════════════════════════════

PIPELINE COMPLETO:
  Locust → /grpc-201905884
         → [Gateway API]
         → [Rust REST API]  HPA 1-3 réplicas, CPU > 30%
         → [Go Dep 1: gRPC Client]  HPA 1-3 réplicas
         → [Go Dep 2/3: gRPC Server + RabbitMQ Writer]
         → [RabbitMQ]  exchange=warreport_exchange | queue=warreport_queue | rk=warreport.process
         → [Go Consumer]
         → [Valkey — KubeVirt VM1]
         → [Grafana — KubeVirt VM2]
  [Zot Registry] — VM GCP externa, todas las imágenes Docker

CARNET DEL ESTUDIANTE: 201905884
  Último dígito: 4 → País asignado: CHN (tabla: 4,5 = CHN)

────────────────────────────────────────────────────────────
ESTRUCTURA EXACTA DEL MENSAJE JSON (payload HTTP de Locust)
────────────────────────────────────────────────────────────
{
  "country": "ESP",
  "warplanes_in_air": 42,
  "warships_in_water": 14,
  "timestamp": "2026-03-12T20:15:30Z"
}

Reglas de generación:
  - country      : código de país de 3 letras (usa, rus, chn, esp, gtm)
  - warplanes_in_air   : entero aleatorio entre 0 y 50 (inclusive)
  - warships_in_water  : entero aleatorio entre 0 y 30 (inclusive)
  - timestamp    : fecha y hora ISO 8601 del evento

Países válidos (enum proto):
  countries_unknown = 0
  usa = 1
  rus = 2
  chn = 3
  esp = 4
  gtm = 5

Asignación de país por último dígito del carnet:
  0, 1  →  USA
  2, 3  →  RUS
  4, 5  →  CHN  ← (carnet 201905884, dígito 4)
  6, 7  →  ESP
  8, 9  →  GTM

────────────────────────────────────────────────────────────
CONTRATO gRPC (proto/warreport.proto)
────────────────────────────────────────────────────────────
syntax = "proto3";
package wartweets;
option go_package = "./proto";

enum Countries {
  countries_unknown = 0; usa = 1; rus = 2; chn = 3; esp = 4; gtm = 5;
}
message WarReportRequest {
  Countries country        = 1;
  int32 warplanes_in_air   = 2;
  int32 warships_in_water  = 3;
  string timestamp         = 4;
}
message WarReportResponse { string status = 1; }
service WarReportService {
  rpc SendReport (WarReportRequest) returns (WarReportResponse);
}

────────────────────────────────────────────────────────────
TOPOLOGÍA RABBITMQ (obligatoria, exacta)
────────────────────────────────────────────────────────────
  Exchange  : warreport_exchange  (tipo: direct, durable: true)
  Queue     : warreport_queue     (durable: true)
  Routing key: warreport.process
  El mensaje publicado debe ser el JSON completo del WarReportRequest.

────────────────────────────────────────────────────────────
ESTRUCTURA DE DATOS EN VALKEY (para que Grafana pueda leerlos)
────────────────────────────────────────────────────────────
Grafana consulta Valkey con estas keys exactas:
  ZREVRANGE rss_rank   0 4 WITHSCORES   → Top 5 países por aviones en aire
  ZREVRANGE cpu_rank   0 4 WITHSCORES   → Top 5 países por barcos en mar
  LRANGE    meminfo    0 -1             → Datos de serie temporal

El Consumer debe escribir en Valkey:
  - ZADD rss_rank  <score_aviones>  <country>  para cada reporte recibido
  - ZADD cpu_rank  <score_barcos>   <country>  para cada reporte recibido
  - LPUSH meminfo  <json_del_reporte>           para serie temporal
  - Para max/min/moda: puede usar claves auxiliares (ej. SET max_warplanes <valor>)

────────────────────────────────────────────────────────────
ESTRUCTURA DEL DASHBOARD GRAFANA (11 paneles OBLIGATORIOS)
────────────────────────────────────────────────────────────
Panel 1:  Valor máximo general de aviones en aire         (Stat panel)
Panel 2:  Valor mínimo general de aviones en aire         (Stat panel)
Panel 3:  Valor máximo general de barcos en mar           (Stat panel)
Panel 4:  Valor mínimo general de barcos en mar           (Stat panel)
Panel 5:  Moda de aviones en aire                         (Stat panel)
Panel 6:  Moda de barcos en mar                           (Stat panel)
Panel 7:  Top de países con más aviones en aire           (Bar chart — ZREVRANGE rss_rank)
Panel 8:  Top de países con más barcos en mar             (Bar chart — ZREVRANGE cpu_rank)
Panel 9:  Serie temporal del país asignado (CHN):
            - Evolución de aviones en aire
            - Evolución de barcos en mar                   (Time series — LRANGE meminfo)
Panel 10: Nombre del país asignado (CHN)                  (Text/Stat panel)
Panel 11: Cantidad total de reportes del país asignado    (Stat panel)

Ejemplo visual del dashboard (descripción):
  Fila 1: [Max Aviones] [Min Aviones] [Max Barcos] [Min Barcos]
  Fila 2: [Moda Aviones] [Moda Barcos] [Top 5 Aviones] [Top 5 Barcos]
  Fila 3: [País Asignado + Total Reportes] [Serie Temporal CHN: aviones + barcos]
  Footer: [# CARNET]

────────────────────────────────────────────────────────────
RUTA HTTP EXPUESTA (Gateway API)
────────────────────────────────────────────────────────────
  Ruta obligatoria : /grpc-201905884  → Rust REST API
  Ruta opcional    : /dapr-201905884  → flujo Dapr (punteo extra)
  NO usar Ingress Controller — usar Kubernetes Gateway API (gateway.networking.k8s.io)

────────────────────────────────────────────────────────────
PENALIZACIONES (sobre la nota final)
────────────────────────────────────────────────────────────
  No usar GKE             : -80%
  No usar Grafana/KubeVirt: -60%
  No usar RabbitMQ        : -30%
  No usar Valkey/KubeVirt : -15%
  No usar Locust          : -10%
  No usar Zot             : -5%

NOTA = 0 si: (a) no se entrega en UEDI, o (b) no hay manual técnico .md en el repo.

════════════════════════════════════════════════════════════
"""


def _read_files(patterns: list[str]) -> dict[str, str]:
    """Lee archivos del proyecto según patrones glob."""
    files: dict[str, str] = {}
    for pattern in patterns:
        for path in sorted(PROJECT_ROOT.glob(pattern)):
            if path.is_file() and path.stat().st_size < 60_000:
                rel = str(path.relative_to(PROJECT_ROOT))
                try:
                    files[rel] = path.read_text(errors="replace")
                except Exception as e:
                    files[rel] = f"[ERROR READING: {e}]"
    return files


def _call_agent(client: anthropic.Anthropic, system: str, user: str) -> str:
    """Llama a Claude con un prompt de sistema y usuario, retorna el texto."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=[
            {
                "type": "text",
                "text": system,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user}],
    )
    return response.content[0].text


# ─────────────────────────────────────────────────────────────────────────────
# AGENTE 1: Validador de Servicios de Código
# Evalúa: Rust API, Go gRPC Client, Go gRPC Server-Writer, Go Consumer, Proto
# ─────────────────────────────────────────────────────────────────────────────
AGENT1_SYSTEM = SHARED_CONTEXT + """
Eres un validador de código especializado en el proyecto M.U.M.N.K8s.
Tu tarea es revisar el código fuente y determinar si cada servicio está correctamente implementado.

CRITERIOS DE EVALUACIÓN (sé estricto y honesto):

1. rust-api (5 pts): Debe tener servidor HTTP (Actix-web o Axum), endpoint POST /grpc-<carnet>,
   recibir JSON {country, warplanes_in_air, warships_in_water, timestamp} y reenviar a Go via gRPC.
   Un simple "Hello World" o código vacío = STUB = 0 pts.

2. go-api-grpc-client (parte de 10 pts): Debe recibir HTTP de Rust, parsear JSON, mapear country
   al enum proto, y llamar WarReportService.SendReport via gRPC. Debe tener ruta /grpc-<carnet>.

3. go-grpc-server-writer (parte de 10 pts): Debe implementar WarReportServiceServer, recibir
   WarReportRequest, publicar en RabbitMQ exchange=warreport_exchange, queue=warreport_queue,
   routing_key=warreport.process. Detecta errores como typos en hostnames.

4. go-rabbit-consumer (parte de 15 pts): Debe conectarse a RabbitMQ, consumir warreport_queue,
   parsear mensajes y escribir datos procesados en Valkey usando sorted sets y lists.
   Un fmt.Println() = STUB = 0 pts.

5. proto (base): Debe definir Countries enum (usa=1,rus=2,chn=3,esp=4,gtm=5), WarReportRequest,
   WarReportResponse, y el servicio WarReportService con rpc SendReport.

Para cada servicio responde en JSON con este formato exacto:
{
  "servicio": "nombre",
  "estado": "COMPLETO|PARCIAL|STUB|AUSENTE",
  "puntos_estimados": N,
  "puntos_maximos": N,
  "hallazgos": ["hallazgo 1", "hallazgo 2"],
  "bugs_criticos": ["bug 1"]
}
Devuelve un array JSON con un objeto por servicio."""


def validate_code(client: anthropic.Anthropic) -> dict[str, Any]:
    """Agente 1: Valida el código fuente de todos los servicios."""
    files = _read_files([
        "rust-api/src/**/*.rs",
        "rust-api/Cargo.toml",
        "go-api-grpc-client/**/*.go",
        "go-api-grpc-client/go.mod",
        "go-grpc-server-writer/**/*.go",
        "go-grpc-server-writer/go.mod",
        "go-rabbit-consumer/**/*.go",
        "go-rabbit-consumer/go.mod",
        "proto/*.proto",
    ])

    file_dump = "\n\n".join(
        f"### {path}\n```\n{content}\n```" for path, content in files.items()
    )

    result_text = _call_agent(
        client,
        AGENT1_SYSTEM,
        f"Analiza estos archivos del proyecto y devuelve el JSON de validación:\n\n{file_dump}",
    )

    try:
        start = result_text.find("[")
        end = result_text.rfind("]") + 1
        return {"agente": "code_validator", "resultados": json.loads(result_text[start:end])}
    except Exception:
        return {"agente": "code_validator", "resultados": [], "raw": result_text}


# ─────────────────────────────────────────────────────────────────────────────
# AGENTE 2: Validador de Infraestructura Kubernetes
# Evalúa: Gateway API, HPA, Deployments, KubeVirt VMs, Zot, Namespaces
# ─────────────────────────────────────────────────────────────────────────────
AGENT2_SYSTEM = SHARED_CONTEXT + """
Eres un validador de infraestructura Kubernetes para el proyecto M.U.M.N.K8s.
Tu tarea es revisar los manifiestos YAML de Kubernetes y Dockerfiles.

CRITERIOS DE EVALUACIÓN (sé estricto):

1. Gateway API (5 pts): Debe existir un recurso Gateway y HTTPRoute (NO Ingress).
   Rutas requeridas: /grpc-201905884 hacia Rust API. Detecta si se usa Ingress en lugar de Gateway API.

2. Deployments + HPA (parte de 5+10 pts):
   - rust-api Deployment con HPA: minReplicas=1, maxReplicas=3, CPU > 30%
   - go-api-grpc-client Deployment con HPA: minReplicas=1, maxReplicas=3
   - go-grpc-server-writer Deployment (1-2 réplicas para análisis)
   - go-rabbit-consumer Deployment

3. Zot (10 pts): Debe haber configuración o referencia a Zot como container registry.
   Todas las imágenes en los Deployments deben referenciar el registro Zot, no Docker Hub.

4. KubeVirt VMs (parte de 20+25 pts):
   - VirtualMachine para Valkey (VM1)
   - VirtualMachine para Grafana (VM2)
   Ambas deben ser recursos tipo kubevirt.io/v1 VirtualMachine dentro del clúster.

5. Namespaces: Se recomienda military-pipeline, messaging, monitoring.

6. Dockerfiles (parte de todos los servicios): Cada servicio debe tener su propio Dockerfile.

Para cada elemento responde en JSON:
{
  "componente": "nombre",
  "estado": "COMPLETO|PARCIAL|AUSENTE",
  "puntos_estimados": N,
  "puntos_maximos": N,
  "hallazgos": ["..."],
  "archivos_encontrados": ["path/file.yaml"]
}
Devuelve un array JSON."""


def validate_infrastructure(client: anthropic.Anthropic) -> dict[str, Any]:
    """Agente 2: Valida manifiestos K8s, Dockerfiles y configuración de infra."""
    files = _read_files([
        "deployments/**/*.yaml",
        "deployments/**/*.yml",
        "**/Dockerfile",
        "**/Dockerfile.*",
        "**/*.yaml",
        "**/*.yml",
    ])

    if not files:
        return {
            "agente": "infra_validator",
            "resultados": [
                {
                    "componente": "deployments/",
                    "estado": "AUSENTE",
                    "puntos_estimados": 0,
                    "puntos_maximos": 50,
                    "hallazgos": ["No se encontró ningún archivo YAML ni Dockerfile en el proyecto."],
                    "archivos_encontrados": [],
                }
            ],
        }

    file_dump = "\n\n".join(
        f"### {path}\n```yaml\n{content}\n```" for path, content in files.items()
    )

    result_text = _call_agent(
        client,
        AGENT2_SYSTEM,
        f"Analiza estos archivos de infraestructura y devuelve el JSON de validación:\n\n{file_dump}",
    )

    try:
        start = result_text.find("[")
        end = result_text.rfind("]") + 1
        return {"agente": "infra_validator", "resultados": json.loads(result_text[start:end])}
    except Exception:
        return {"agente": "infra_validator", "resultados": [], "raw": result_text}


# ─────────────────────────────────────────────────────────────────────────────
# AGENTE 3: Validador de Mensajería y Almacenamiento
# Evalúa: RabbitMQ topology, Consumer logic, Valkey data structures
# ─────────────────────────────────────────────────────────────────────────────
AGENT3_SYSTEM = SHARED_CONTEXT + """
Eres un validador de mensajería y almacenamiento para el proyecto M.U.M.N.K8s.

CRITERIOS DE EVALUACIÓN:

1. RabbitMQ Publisher (parte de 15 pts): El go-grpc-server-writer debe:
   - Usar exchange: "warreport_exchange" (tipo direct, durable)
   - Queue: "warreport_queue" (durable)
   - Routing key: "warreport.process"
   - Publicar el mensaje JSON completo del reporte militar
   - Penalización: typo en hostname (ej. "locatehost" en vez de hostname configurable)

2. RabbitMQ Consumer (parte de 15 pts): El go-rabbit-consumer debe:
   - Conectarse a RabbitMQ y consumir de "warreport_queue"
   - Parsear el mensaje JSON (country, warplanes_in_air, warships_in_water, timestamp)
   - Un stub sin lógica = 0 pts

3. Valkey/Redis Integration (parte de 20 pts): El consumer debe escribir en Valkey usando:
   - ZADD para sorted sets de ranking por país (warplanes, warships)
   - Estructuras que permitan ZREVRANGE para top países
   - El carnet del estudiante es 201905884 → país asignado: GTM (último dígito 4 → CHN según tabla,
     pero verificar la tabla: 4,5=CHN)
   - Nota: Grafana consulta con ZREVRANGE rss_rank 0 4 y ZREVRANGE cpu_rank 0 4

4. Configuración de conexiones: Los hostnames deben ser configurables via env vars,
   no hardcodeados a "localhost" o strings con typos.

Responde en JSON array con objetos:
{
  "componente": "nombre",
  "estado": "COMPLETO|PARCIAL|STUB|AUSENTE",
  "puntos_estimados": N,
  "puntos_maximos": N,
  "hallazgos": ["..."],
  "bugs_criticos": ["..."]
}"""


def validate_messaging(client: anthropic.Anthropic) -> dict[str, Any]:
    """Agente 3: Valida RabbitMQ topology, consumer y integración con Valkey."""
    files = _read_files([
        "go-grpc-server-writer/**/*.go",
        "go-rabbit-consumer/**/*.go",
        "go-rabbit-consumer/go.mod",
    ])

    file_dump = "\n\n".join(
        f"### {path}\n```go\n{content}\n```" for path, content in files.items()
    )

    result_text = _call_agent(
        client,
        AGENT3_SYSTEM,
        f"Analiza la implementación de mensajería y almacenamiento:\n\n{file_dump}",
    )

    try:
        start = result_text.find("[")
        end = result_text.rfind("]") + 1
        return {"agente": "messaging_validator", "resultados": json.loads(result_text[start:end])}
    except Exception:
        return {"agente": "messaging_validator", "resultados": [], "raw": result_text}


# ─────────────────────────────────────────────────────────────────────────────
# AGENTE 4: Validador de Pruebas y Documentación
# Evalúa: Locust scripts, Manual técnico Markdown, OCI Artifact docs
# ─────────────────────────────────────────────────────────────────────────────
AGENT4_SYSTEM = SHARED_CONTEXT + """
Eres un validador de pruebas y documentación para el proyecto M.U.M.N.K8s.

CRITERIOS DE EVALUACIÓN (muy importantes — algunos son requisito para nota ≠ 0):

1. Locust (5 pts + penalización -10% si ausente): Debe existir un script Python con:
   - Clase que herede de HttpUser o FastHttpUser
   - Task que haga POST a /grpc-201905884
   - Payload JSON: {country: "CHN", warplanes_in_air: aleatorio 0-50,
     warships_in_water: aleatorio 0-30, timestamp: datetime actual}
   - Países válidos: usa, rus, chn, esp, gtm (carnet 201905884 → dígito 4 → CHN)

2. Manual Técnico en Markdown (2 pts + REQUISITO MÍNIMO = nota 0 si ausente):
   Debe estar en el repositorio GitHub (NO en obsidian/). Debe cubrir:
   - arquitectura general
   - flujo completo de datos
   - configuración de Gateway API
   - comunicación REST y gRPC
   - uso de RabbitMQ
   - despliegue de Valkey y Grafana sobre KubeVirt
   - configuración de HPA
   - publicación/consumo de imágenes desde Zot
   - pruebas realizadas y conclusiones
   IMPORTANTE: archivos en obsidian/ NO cuentan como manual técnico del repo.

3. OCI Artifact: Debe haber documentación de qué archivo se sube como OCI Artifact
   a Zot y cómo se usa en el sistema.

4. Dashboard Grafana (parte de 25 pts): Debe documentar los 11 paneles:
   - Max aviones en aire, Min aviones en aire
   - Max barcos en mar, Min barcos en mar
   - Moda aviones, Moda barcos
   - Top 5 países aviones, Top 5 países barcos
   - Serie temporal del país asignado (aviones + barcos)
   - Nombre del país asignado
   - Cantidad total de reportes del país asignado

Responde en JSON array:
{
  "componente": "nombre",
  "estado": "COMPLETO|PARCIAL|AUSENTE",
  "es_requisito_minimo": true/false,
  "puntos_estimados": N,
  "puntos_maximos": N,
  "hallazgos": ["..."],
  "riesgo": "CRITICO|ALTO|MEDIO|BAJO"
}"""


def validate_docs_and_testing(client: anthropic.Anthropic) -> dict[str, Any]:
    """Agente 4: Valida Locust, manual técnico Markdown y documentación."""
    files = _read_files([
        "locust/**/*.py",
        "locust/**/*.md",
        "*.md",
        "docs/**/*.md",
        "proyecto3/**/*.md",
    ])

    # Busca manuals explícitamente (excluye obsidian y CLAUDE.md)
    manual_files = {}
    for pattern in ["**/*.md"]:
        for path in PROJECT_ROOT.glob(pattern):
            rel = str(path.relative_to(PROJECT_ROOT))
            if "obsidian" not in rel and "CLAUDE.md" not in rel and path.stat().st_size < 60_000:
                try:
                    manual_files[rel] = path.read_text(errors="replace")
                except Exception:
                    pass

    files.update(manual_files)

    if not files:
        return {
            "agente": "docs_validator",
            "resultados": [
                {
                    "componente": "Locust",
                    "estado": "AUSENTE",
                    "es_requisito_minimo": True,
                    "puntos_estimados": 0,
                    "puntos_maximos": 5,
                    "hallazgos": ["No se encontró ningún archivo de Locust."],
                    "riesgo": "CRITICO",
                },
                {
                    "componente": "Manual Técnico Markdown",
                    "estado": "AUSENTE",
                    "es_requisito_minimo": True,
                    "puntos_estimados": 0,
                    "puntos_maximos": 2,
                    "hallazgos": [
                        "No se encontró manual técnico .md en el repositorio.",
                        "SIN ESTO LA NOTA ES 0 INDEPENDIENTEMENTE DEL RESTO.",
                    ],
                    "riesgo": "CRITICO",
                },
            ],
        }

    file_dump = "\n\n".join(
        f"### {path}\n```\n{content}\n```" for path, content in files.items()
    )

    result_text = _call_agent(
        client,
        AGENT4_SYSTEM,
        f"Analiza los archivos de pruebas y documentación:\n\n{file_dump}",
    )

    try:
        start = result_text.find("[")
        end = result_text.rfind("]") + 1
        return {"agente": "docs_validator", "resultados": json.loads(result_text[start:end])}
    except Exception:
        return {"agente": "docs_validator", "resultados": [], "raw": result_text}
