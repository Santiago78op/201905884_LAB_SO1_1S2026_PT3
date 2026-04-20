#!/usr/bin/env python3
"""
M.U.M.N.K8s — Agente Maestro de Validación
Orquesta 4 sub-agentes especializados y produce reporte final con punteo.

Uso:
    python3 main.py
    python3 main.py --json        # output raw JSON
    python3 main.py --area code   # solo un área (code|infra|messaging|docs)

Requiere: ANTHROPIC_API_KEY en el entorno.
"""

import json
import os
import sys
import argparse
from typing import Any
import anthropic

from validators import (
    validate_code,
    validate_infrastructure,
    validate_messaging,
    validate_docs_and_testing,
    SHARED_CONTEXT,
)

# ─────────────────────────────────────────────────────────────────────────────
# Definición de herramientas del agente maestro
# ─────────────────────────────────────────────────────────────────────────────
MASTER_TOOLS = [
    {
        "name": "validate_code_services",
        "description": (
            "Ejecuta el sub-agente de validación de código fuente. "
            "Evalúa: Rust API, go-api-grpc-client, go-grpc-server-writer, "
            "go-rabbit-consumer y el contrato proto. "
            "Detecta stubs vs implementaciones reales y bugs críticos."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "validate_infrastructure",
        "description": (
            "Ejecuta el sub-agente de validación de infraestructura Kubernetes. "
            "Evalúa: Gateway API, HPA, Deployments, Dockerfiles, KubeVirt VMs "
            "(Valkey y Grafana), namespaces y registro Zot."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "validate_messaging_storage",
        "description": (
            "Ejecuta el sub-agente de validación de mensajería y almacenamiento. "
            "Evalúa: topología RabbitMQ (exchange/queue/routing key), "
            "lógica del consumer, integración con Valkey y correctitud de conexiones."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "validate_docs_testing",
        "description": (
            "Ejecuta el sub-agente de validación de pruebas y documentación. "
            "Evalúa: script Locust con payload correcto, manual técnico en Markdown "
            "(REQUISITO MÍNIMO para nota ≠ 0), OCI Artifact y dashboards de Grafana."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
]

MASTER_SYSTEM = SHARED_CONTEXT + """
Eres el Agente Maestro de validación del proyecto M.U.M.N.K8s (SO1, FIUSAC).
Tu trabajo es orquestar 4 sub-agentes para evaluar el proyecto completo contra los requisitos
del Proyecto #3 y producir un reporte final con punteo estimado y prioridades de trabajo.

REQUISITOS COMPLETOS DEL PROYECTO (alcance obligatorio):

● Locust: Generación de tráfico con la estructura JSON especificada hacia el endpoint público
  expuesto mediante Kubernetes Gateway API. Datos aleatorios dentro de rangos definidos.

● Gateway API: Exposición del sistema usando Kubernetes Gateway API (NO Ingress Controller).
  Rutas: /grpc-#carnet y opcionalmente /dapr-#carnet.

● Deployments de Rust: API REST que recibe de Locust, envía a Go, escala con HPA
  (1-3 réplicas, CPU > 30%).

● Deployments de Go:
  - Deployment 1 (API REST + gRPC Client): Recibe de Rust, actúa como cliente gRPC.
  - Deployments 2 y 3 (gRPC Server + Writer RabbitMQ): Recibe gRPC, publica en RabbitMQ.
    Pruebas con 1 y 2 réplicas.

● RabbitMQ: Broker principal. Exchange: warreport_exchange, Queue: warreport_queue,
  Routing key: warreport.process.

● RabbitMQ Consumer (Deployment): Consume mensajes, procesa y almacena en Valkey.

● Valkey en KubeVirt: VM independiente dentro del clúster GKE, administrada por KubeVirt.
  Persistencia y conectividad garantizada.

● Grafana en KubeVirt: VM independiente dentro del clúster, conectada a Valkey como fuente.
  11 paneles requeridos: max/min aviones, max/min barcos, moda aviones, moda barcos,
  top 5 países aviones, top 5 países barcos, serie temporal del país asignado
  (aviones+barcos), nombre del país asignado, total reportes del país asignado.

● Zot: Container Registry en VM GCP fuera del clúster. TODAS las imágenes se publican y
  descargan desde Zot.

● OCI Artifact: Descarga de archivo de entrada desde el registry como OCI Artifact.
  Debe documentarse qué archivo y cómo se usa.

● Infraestructura en GCP: Todo en GCP con instancias N1, clúster GKE.

● Documentación (Manual Técnico en Markdown — OBLIGATORIO para nota ≠ 0):
  arquitectura general, flujo de datos, Gateway API config, REST y gRPC,
  RabbitMQ, Valkey+Grafana en KubeVirt, HPA, Zot, pruebas y conclusiones.

RÚBRICA DE PUNTEO (100 pts total):
- 1.1 Arquitectura General + Gateway API (Ingress en K8s): 5 pts
- 1.2 API REST en Rust: 5 pts
- 1.3 Servicios Go (gRPC Client + Server-Writers): 10 pts
- 1.4 Arquitectura General Despliegue en Zot: 10 pts
- 1.5 Message Broker + Consumer RabbitMQ: 15 pts
- 1.6 Almacenamiento Valkey (KubeVirt): 20 pts
- 1.7 Grafana (KubeVirt): 25 pts
- 2.1 Pruebas de Carga HPA + Análisis de Réplicas: 5 pts
- 2.2 Manual Técnico: 2 pts
- 2.3 Respuestas a Preguntas: 3 pts (no evaluable automáticamente)

PENALIZACIONES:
- No usar GKE: -80% de la nota final
- No usar Grafana con KubeVirt: -60% de la nota final
- No usar RabbitMQ: -30% de la nota final
- No usar Valkey con KubeVirt: -15% de la nota final
- No usar Locust: -10% de la nota final
- No usar Zot: -5% de la nota final

REQUISITOS QUE DAN NOTA 0 (independientemente del resto):
1. No entregar en UEDI
2. No entregar manual técnico en Markdown en el repositorio GitHub

INSTRUCCIONES:
1. Llama a los 4 sub-agentes en orden usando las herramientas disponibles.
2. Recopila todos los resultados.
3. Calcula el punteo estimado total.
4. Aplica penalizaciones si corresponde.
5. Genera el reporte final en Markdown con: resumen ejecutivo, tabla de punteo por área,
   bugs críticos a corregir HOY, y lista priorizada de tareas pendientes.

El carnet del estudiante es 201905884 (último dígito: 4 → país asignado: CHN según tabla 4,5=CHN).
La fecha actual es 2026-04-19. La fecha de entrega es 2026-04-30. Quedan 11 días."""


# ─────────────────────────────────────────────────────────────────────────────
# Ejecución del agente maestro (agentic loop)
# ─────────────────────────────────────────────────────────────────────────────
def run_master_agent(
    client: anthropic.Anthropic,
    only_area: str | None = None,
) -> tuple[str, dict[str, Any]]:
    """
    Ejecuta el agente maestro con loop de tool_use.
    Retorna (reporte_markdown, datos_crudos).
    """
    tool_results: dict[str, Any] = {}
    messages = [
        {
            "role": "user",
            "content": (
                "Ejecuta la validación completa del proyecto M.U.M.N.K8s. "
                "Llama a los 4 sub-agentes de validación en orden y luego "
                "genera el reporte final con punteo estimado y prioridades."
                if only_area is None
                else f"Ejecuta SOLO la validación del área: {only_area}. "
                     "Llama únicamente la herramienta correspondiente y genera el reporte."
            ),
        }
    ]

    print("  Iniciando agente maestro...", flush=True)

    while True:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=[{"type": "text", "text": MASTER_SYSTEM, "cache_control": {"type": "ephemeral"}}],
            tools=MASTER_TOOLS,
            messages=messages,
        )

        # Agregar respuesta del asistente al historial
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            # Extraer texto final
            final_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    final_text += block.text
            return final_text, tool_results

        if response.stop_reason != "tool_use":
            break

        # Procesar tool calls
        tool_results_batch = []
        for block in response.content:
            if block.type != "tool_use":
                continue

            tool_name = block.name
            print(f"  → Ejecutando sub-agente: {tool_name}...", flush=True)

            try:
                if tool_name == "validate_code_services":
                    result = validate_code(client)
                elif tool_name == "validate_infrastructure":
                    result = validate_infrastructure(client)
                elif tool_name == "validate_messaging_storage":
                    result = validate_messaging(client)
                elif tool_name == "validate_docs_testing":
                    result = validate_docs_and_testing(client)
                else:
                    result = {"error": f"Herramienta desconocida: {tool_name}"}

                tool_results[tool_name] = result
                tool_results_batch.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result, ensure_ascii=False),
                    }
                )
                print(f"     ✓ Completado: {tool_name}", flush=True)

            except Exception as exc:
                error_result = {"error": str(exc), "agente": tool_name}
                tool_results[tool_name] = error_result
                tool_results_batch.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(error_result),
                        "is_error": True,
                    }
                )
                print(f"     ✗ Error en {tool_name}: {exc}", flush=True)

        messages.append({"role": "user", "content": tool_results_batch})

    return "Error: el agente terminó inesperadamente.", tool_results


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="Validador M.U.M.N.K8s")
    parser.add_argument("--json", action="store_true", help="Imprimir JSON crudo de sub-agentes")
    parser.add_argument(
        "--area",
        choices=["code", "infra", "messaging", "docs"],
        help="Validar solo un área específica",
    )
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: Falta la variable de entorno ANTHROPIC_API_KEY")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    print("\n" + "═" * 60)
    print("  M.U.M.N.K8s — Sistema de Validación Multi-Agente")
    print("  Carnet: 201905884 | País: CHN | Deadline: 2026-04-30")
    print("═" * 60 + "\n")

    area_map = {
        "code": "validate_code_services",
        "infra": "validate_infrastructure",
        "messaging": "validate_messaging_storage",
        "docs": "validate_docs_testing",
    }
    only_area = area_map.get(args.area) if args.area else None

    report, raw_data = run_master_agent(client, only_area=only_area)

    print("\n" + "═" * 60)
    print("  REPORTE FINAL")
    print("═" * 60 + "\n")
    print(report)

    if args.json:
        print("\n" + "═" * 60)
        print("  DATOS CRUDOS (JSON)")
        print("═" * 60 + "\n")
        print(json.dumps(raw_data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
