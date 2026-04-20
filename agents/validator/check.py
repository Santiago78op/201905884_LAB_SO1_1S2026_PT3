#!/usr/bin/env python3
"""
M.U.M.N.K8s — Validador Local (sin API, sin dependencias externas)
Analiza el código fuente del proyecto y reporta el estado de implementación.

Uso:
    python3 check.py
    python3 check.py --area code
    python3 check.py --area infra
    python3 check.py --area messaging
    python3 check.py --area docs
"""

import re
import sys
import argparse
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent

# ─── Colores ANSI ────────────────────────────────────────────────────────────
G  = "\033[92m"   # verde
Y  = "\033[93m"   # amarillo
R  = "\033[91m"   # rojo
B  = "\033[94m"   # azul
W  = "\033[1m"    # bold
RS = "\033[0m"    # reset

def ok(msg):  print(f"  {G}✓{RS} {msg}")
def warn(msg): print(f"  {Y}⚠{RS} {msg}")
def err(msg):  print(f"  {R}✗{RS} {msg}")
def info(msg): print(f"  {B}→{RS} {msg}")
def header(msg): print(f"\n{W}{msg}{RS}")
def sep(): print("─" * 60)

# ─── Utilidades ──────────────────────────────────────────────────────────────
def read(path: Path) -> str:
    try:
        return path.read_text(errors="replace")
    except Exception:
        return ""

def glob_first(pattern: str) -> Path | None:
    results = list(ROOT.glob(pattern))
    return results[0] if results else None

def glob_all(pattern: str) -> list[Path]:
    return list(ROOT.glob(pattern))

def contains(text: str, *patterns: str) -> bool:
    return all(p in text for p in patterns)

def contains_re(text: str, pattern: str) -> bool:
    return bool(re.search(pattern, text))

# ─── ÁREA 1: Servicios de Código ─────────────────────────────────────────────
def check_code():
    header("ÁREA 1 — Servicios de Código")
    sep()
    score = 0
    max_score = 30  # rust(5) + go-client(5) + go-server(5) + consumer(5) + proto(5) + robustez(5)

    # ── Proto ────────────────────────────────────────────────────────────────
    print(f"\n{W}[proto/]{RS}")
    proto_file = ROOT / "proto" / "warreport.proto"
    pb_go      = ROOT / "proto" / "warreport.pb.go"
    grpc_go    = ROOT / "proto" / "warreport_grpc.pb.go"

    if proto_file.exists():
        content = read(proto_file)
        checks = [
            ("Countries enum (usa,rus,chn,esp,gtm)", contains(content, "usa = 1", "rus = 2", "chn = 3", "esp = 4", "gtm = 5")),
            ("WarReportRequest con los 4 campos",    contains(content, "warplanes_in_air", "warships_in_water", "timestamp", "country")),
            ("WarReportResponse",                     "WarReportResponse" in content),
            ("rpc SendReport definido",               "SendReport" in content),
        ]
        all_ok = True
        for label, result in checks:
            if result: ok(label)
            else: err(label); all_ok = False
        if pb_go.exists() and grpc_go.exists():
            ok("Código generado (pb.go + grpc.pb.go) presente")
            if all_ok: score += 5
        else:
            warn("Faltan archivos generados — ejecuta: protoc -I=proto --go_out=proto --go-grpc_out=proto warreport.proto")
    else:
        err("proto/warreport.proto no existe")

    # ── Rust API ─────────────────────────────────────────────────────────────
    print(f"\n{W}[rust-api/]{RS}")
    main_rs  = ROOT / "rust-api" / "src" / "main.rs"
    cargo    = ROOT / "rust-api" / "Cargo.toml"

    if not main_rs.exists():
        err("src/main.rs no existe")
    else:
        rs = read(main_rs)
        cargo_content = read(cargo)

        is_stub = rs.strip() in ['fn main() {\n    println!("Hello, world!");\n}',
                                   'fn main() {\r\n    println!("Hello, world!");\r\n}'] \
                  or (len(rs.strip()) < 80 and "println" in rs and "Hello" in rs)

        if is_stub:
            err("STUB — solo Hello World, sin implementación")
        else:
            has_server   = any(x in rs for x in ["HttpServer", "App::new", "Router", "axum", "actix"])
            has_endpoint = any(x in rs for x in ["grpc-", "/grpc", "post(", "route(", ".service("])
            has_grpc_out = any(x in rs for x in ["tonic", "grpc", "Channel", "connect"])

            if has_server:    ok("Servidor HTTP detectado")
            else:             err("Sin servidor HTTP (actix-web o axum)")
            if has_endpoint:  ok("Endpoint HTTP definido")
            else:             warn("No se detecta ruta /grpc-201905884")
            if has_grpc_out:  ok("Cliente gRPC hacia Go detectado")
            else:             warn("No se detecta salida gRPC (tonic/channel)")

            # Cargo.toml deps
            for dep in ["actix-web", "axum", "tonic"]:
                if dep in cargo_content:
                    ok(f"Dependencia '{dep}' en Cargo.toml")

            if has_server and has_endpoint:
                score += 4
            elif has_server:
                score += 2

    # ── Go gRPC Client (Deployment 1) ────────────────────────────────────────
    print(f"\n{W}[go-api-grpc-client/]{RS}")
    go_files = glob_all("go-api-grpc-client/**/*.go")

    if not go_files:
        err("No se encontraron archivos .go")
    else:
        all_content = "\n".join(read(f) for f in go_files)

        checks = [
            ("Servidor HTTP (net/http o framework)",  any(x in all_content for x in ["http.ListenAndServe", "http.NewServeMux", "gin.", "chi."])),
            ("Ruta /grpc-201905884",                  "grpc-201905884" in all_content),
            ("Parseo del JSON del payload",           any(x in all_content for x in ["json.Unmarshal", "json.NewDecoder", "json.Decode"])),
            ("Mapeo country string → proto enum",     any(x in all_content for x in ["proto.Countries", "wartweets.Countries", "switch", "country"])),
            ("Llamada gRPC SendReport",               "SendReport" in all_content),
            ("Manejo de errores",                     all_content.count("err != nil") >= 2),
        ]
        passed = 0
        for label, result in checks:
            if result: ok(label); passed += 1
            else: warn(label)

        if passed >= 5: score += 5
        elif passed >= 3: score += 3
        else: score += 1

        # Buscar hostnames hardcodeados
        if contains_re(all_content, r'"localhost:\d+"|"127\.0\.0\.1'):
            warn("Hostname hardcodeado detectado — usar os.Getenv() con fallback")
        else:
            ok("Sin hostnames hardcodeados (o usa env vars)")

    # ── Go gRPC Server + RabbitMQ Writer (Deployments 2/3) ───────────────────
    print(f"\n{W}[go-grpc-server-writer/]{RS}")
    srv_files = glob_all("go-grpc-server-writer/**/*.go")

    if not srv_files:
        err("No se encontraron archivos .go")
    else:
        all_content = "\n".join(read(f) for f in srv_files)

        checks = [
            ("Implementa WarReportServiceServer",      any(x in all_content for x in ["WarReportServiceServer", "RegisterWarReportServiceServer"])),
            ("Escucha en puerto gRPC",                 any(x in all_content for x in ["net.Listen", "grpc.NewServer", "Serve("])),
            ("Conecta a RabbitMQ (amqp.Dial)",        "amqp.Dial" in all_content),
            ("Exchange: warreport_exchange",           "warreport_exchange" in all_content),
            ("Queue: warreport_queue",                 "warreport_queue" in all_content),
            ("Routing key: warreport.process",        "warreport.process" in all_content),
            ("Publica mensaje (ch.Publish)",          any(x in all_content for x in ["ch.Publish", "channel.Publish", ".Publish("])),
        ]
        passed = 0
        for label, result in checks:
            if result: ok(label); passed += 1
            else: err(label)

        if passed >= 6: score += 5
        elif passed >= 4: score += 3
        else: score += 1

        # Detectar el typo específico
        if "locatehost" in all_content:
            err("BUG CRÍTICO: typo 'locatehost' en lugar de hostname configurable")
            err("  → Corregir: usar os.Getenv(\"RABBITMQ_HOST\") con fallback \"localhost\"")
        elif contains_re(all_content, r'"localhost:\d+"|"127\.0\.0\.1'):
            warn("Hostname RabbitMQ hardcodeado — usar os.Getenv() con fallback para K8s")
        else:
            ok("Hostname RabbitMQ configurable via env var")

    # ── Go RabbitMQ Consumer ──────────────────────────────────────────────────
    print(f"\n{W}[go-rabbit-consumer/]{RS}")
    con_files = glob_all("go-rabbit-consumer/**/*.go")

    if not con_files:
        err("No se encontraron archivos .go")
    else:
        all_content = "\n".join(read(f) for f in con_files)

        is_stub = (
            all_content.count("\n") < 15
            and any(x in all_content for x in ['Println("go-rabbit', 'Println("Hello'])
            and "amqp" not in all_content
        )

        if is_stub:
            err("STUB — sin lógica de RabbitMQ ni Valkey")
            info("Pendiente: conectar RabbitMQ → consumir warreport_queue → escribir en Valkey")
        else:
            checks = [
                ("Conecta a RabbitMQ",                    "amqp.Dial" in all_content),
                ("Consume de warreport_queue",             "warreport_queue" in all_content),
                ("Parsea el mensaje JSON",                 any(x in all_content for x in ["json.Unmarshal", "json.Decode", "json.NewDecoder"])),
                ("Conecta a Valkey/Redis",                 any(x in all_content for x in ["redis.NewClient", "valkey", "redis.Dial", "go-redis"])),
                ("Escribe en rss_rank (ZADD aviones)",    "rss_rank" in all_content),
                ("Escribe en cpu_rank (ZADD barcos)",     "cpu_rank" in all_content),
                ("Escribe en meminfo (LPUSH serie temp)", "meminfo" in all_content),
            ]
            passed = 0
            for label, result in checks:
                if result: ok(label); passed += 1
                else: warn(label)

            if passed >= 6: score += 5
            elif passed >= 3: score += 3
            else: score += 1

    sep()
    pct = int(score / max_score * 100)
    print(f"\n  Punteo área código: {W}{score}/{max_score} pts ({pct}%){RS}")
    return score, max_score


# ─── ÁREA 2: Infraestructura ─────────────────────────────────────────────────
def check_infra():
    header("ÁREA 2 — Infraestructura (Dockerfiles + YAMLs K8s)")
    sep()
    score = 0
    max_score = 40

    print(f"\n{W}[Dockerfiles]{RS}")
    services = ["rust-api", "go-api-grpc-client", "go-grpc-server-writer", "go-rabbit-consumer"]
    for svc in services:
        df = glob_first(f"{svc}/Dockerfile")
        if df:
            ok(f"Dockerfile presente: {svc}/")
            score += 1
        else:
            warn(f"Sin Dockerfile: {svc}/  (crear cuando el código esté listo)")

    print(f"\n{W}[Kubernetes YAMLs — deployments/]{RS}")
    yaml_files = glob_all("deployments/**/*.yaml") + glob_all("deployments/**/*.yml")

    if not yaml_files:
        warn("No se encontró la carpeta deployments/ con YAMLs")
        info("Pendiente para la fase de infraestructura en GCP")
    else:
        all_yaml = "\n".join(read(f) for f in yaml_files)

        items = [
            ("Gateway API (kind: Gateway)",             "kind: Gateway" in all_yaml),
            ("HTTPRoute /grpc-201905884",               "grpc-201905884" in all_yaml),
            ("HPA para rust-api",                       "HorizontalPodAutoscaler" in all_yaml and "rust" in all_yaml),
            ("HPA para go-api-grpc-client",             "HorizontalPodAutoscaler" in all_yaml and "grpc-client" in all_yaml),
            ("KubeVirt VM Valkey (kind: VirtualMachine)","VirtualMachine" in all_yaml and "valkey" in all_yaml.lower()),
            ("KubeVirt VM Grafana (kind: VirtualMachine)","VirtualMachine" in all_yaml and "grafana" in all_yaml.lower()),
            ("Imágenes referenciando Zot registry",     contains_re(all_yaml, r'image:.*zot|image:.*registry\.')),
            ("Namespaces definidos",                    "kind: Namespace" in all_yaml),
        ]
        for label, result in items:
            if result: ok(label); score += 3
            else: warn(label)

    sep()
    pct = int(score / max_score * 100)
    print(f"\n  Punteo área infra: {W}{score}/{max_score} pts ({pct}%){RS}")
    return score, max_score


# ─── ÁREA 3: Mensajería y Almacenamiento ─────────────────────────────────────
def check_messaging():
    header("ÁREA 3 — Mensajería y Almacenamiento")
    sep()
    score = 0
    max_score = 15

    print(f"\n{W}[RabbitMQ Publisher — go-grpc-server-writer]{RS}")
    srv_content = "\n".join(read(f) for f in glob_all("go-grpc-server-writer/**/*.go"))

    mq_checks = [
        ("Exchange warreport_exchange declarado", "warreport_exchange" in srv_content),
        ("Queue warreport_queue declarada",        "warreport_queue" in srv_content),
        ("Routing key warreport.process",         "warreport.process" in srv_content),
        ("Exchange tipo direct",                  "direct" in srv_content),
        ("Durable: true en exchange y queue",     srv_content.count("true") >= 2),
        ("Publica JSON del mensaje completo",     any(x in srv_content for x in ["json.Marshal", "encoding/json"])),
    ]
    for label, result in mq_checks:
        if result: ok(label); score += 1
        else: err(label)

    print(f"\n{W}[RabbitMQ Consumer + Valkey — go-rabbit-consumer]{RS}")
    con_content = "\n".join(read(f) for f in glob_all("go-rabbit-consumer/**/*.go"))

    valkey_checks = [
        ("Consume de warreport_queue",            "warreport_queue" in con_content),
        ("ZADD a rss_rank (ranking aviones)",     "rss_rank" in con_content),
        ("ZADD a cpu_rank (ranking barcos)",      "cpu_rank" in con_content),
        ("LPUSH a meminfo (serie temporal)",      "meminfo" in con_content),
        ("Conexión a Valkey/Redis",               any(x in con_content for x in ["redis.NewClient", "go-redis", "valkey"])),
        ("Parsea warplanes_in_air y warships",    "warplanes_in_air" in con_content and "warships_in_water" in con_content),
    ]
    for label, result in valkey_checks:
        if result: ok(label); score += 1
        else: warn(label)

    # Hostnames configurables
    print(f"\n{W}[Configuración de Hostnames]{RS}")
    all_go = "\n".join(read(f) for f in glob_all("**/*.go"))
    if "locatehost" in all_go:
        err("Typo 'locatehost' detectado en el código — corregir ahora")
    if contains_re(all_go, r'os\.Getenv\("RABBITMQ'):
        ok("RABBITMQ_HOST leído de variable de entorno")
    elif "localhost" in all_go and "Getenv" not in all_go:
        warn("Hostnames hardcodeados — cambiar a os.Getenv() con fallback para compatibilidad K8s")
    if contains_re(all_go, r'os\.Getenv\("(REDIS|VALKEY)'):
        ok("VALKEY/REDIS host leído de variable de entorno")

    sep()
    pct = int(score / max_score * 100)
    print(f"\n  Punteo área mensajería: {W}{score}/{max_score} pts ({pct}%){RS}")
    return score, max_score


# ─── ÁREA 4: Pruebas y Documentación ─────────────────────────────────────────
def check_docs():
    header("ÁREA 4 — Pruebas y Documentación")
    sep()
    score = 0
    max_score = 12

    # Locust
    print(f"\n{W}[Locust — generación de tráfico]{RS}")
    locust_files = glob_all("locust/**/*.py")
    if not locust_files:
        err("Sin directorio locust/ ni scripts Python")
        err("Penalización: -10% de la nota final si no existe")
        info("Crear: locust/locustfile.py con POST /grpc-201905884 y payload CHN aleatorio")
    else:
        lc = "\n".join(read(f) for f in locust_files)
        items = [
            ("Hereda de HttpUser o FastHttpUser",   any(x in lc for x in ["HttpUser", "FastHttpUser"])),
            ("POST a /grpc-201905884",              "grpc-201905884" in lc),
            ("Campo country en payload",            "country" in lc),
            ("Campo warplanes_in_air",              "warplanes_in_air" in lc),
            ("Campo warships_in_water",             "warships_in_water" in lc),
            ("Valores aleatorios (random)",         "random" in lc),
            ("Rango warplanes 0-50",                "50" in lc),
            ("Rango warships 0-30",                 "30" in lc),
            ("País CHN incluido",                   any(x in lc for x in ["CHN", "chn"])),
        ]
        for label, result in items:
            if result: ok(label); score += 1
            else: warn(label)

    # Manual técnico Markdown
    print(f"\n{W}[Manual Técnico Markdown — REQUISITO MÍNIMO]{RS}")
    EXCLUDE = {"obsidian", "CLAUDE.md", ".venv", ".claude", "agents"}
    md_files = [
        p for p in ROOT.glob("**/*.md")
        if not any(x in str(p) for x in EXCLUDE) and p.stat().st_size > 500
    ]

    if not md_files:
        err("NO SE ENCONTRÓ manual técnico .md en el repositorio")
        err("SIN ESTO LA NOTA FINAL ES 0 — prioridad máxima")
    else:
        for f in md_files:
            info(f"Manual encontrado: {f.relative_to(ROOT)}")
        combined = "\n".join(read(f) for f in md_files)
        secciones = [
            ("Arquitectura general",               any(x in combined.lower() for x in ["arquitectura", "architecture"])),
            ("Flujo completo de datos",            any(x in combined.lower() for x in ["flujo", "pipeline", "flow"])),
            ("Configuración Gateway API",          "gateway" in combined.lower()),
            ("Comunicación REST y gRPC",           "grpc" in combined.lower() and "rest" in combined.lower()),
            ("Uso de RabbitMQ",                    "rabbitmq" in combined.lower()),
            ("Valkey y Grafana sobre KubeVirt",    "kubevirt" in combined.lower()),
            ("Configuración de HPA",               "hpa" in combined.lower()),
            ("Publicación desde Zot",              "zot" in combined.lower()),
            ("Pruebas y conclusiones",             any(x in combined.lower() for x in ["prueba", "conclus", "test"])),
        ]
        for label, result in secciones:
            if result: ok(label); score += 0  # no suma pts aquí, es requisito mínimo
            else: warn(f"Falta sección: {label}")

        score += 2  # si existe el manual, suma los 2 pts

    # OCI Artifact
    print(f"\n{W}[OCI Artifact]{RS}")
    EXCLUDE = {"obsidian", "CLAUDE.md", ".venv", ".claude", "agents"}
    all_content = "\n".join(
        read(f) for f in ROOT.glob("**/*.md")
        if not any(x in str(f) for x in EXCLUDE)
    )
    if "oci" in all_content.lower() or "artifact" in all_content.lower():
        ok("OCI Artifact documentado")
        score += 1
    else:
        warn("OCI Artifact no documentado (debe especificar qué archivo y cómo se usa)")

    sep()
    pct = int(score / max_score * 100)
    print(f"\n  Punteo área docs/pruebas: {W}{score}/{max_score} pts ({pct}%){RS}")
    return score, max_score


# ─── REPORTE FINAL ────────────────────────────────────────────────────────────
def report(results: list[tuple[int, int]]):
    header("RESUMEN EJECUTIVO")
    sep()

    areas = ["Código", "Infraestructura", "Mensajería", "Docs/Pruebas"]
    total_score = 0
    total_max   = 0

    for (s, m), area in zip(results, areas):
        bar_len = 20
        filled  = int(s / m * bar_len) if m > 0 else 0
        bar     = "█" * filled + "░" * (bar_len - filled)
        pct     = int(s / m * 100) if m > 0 else 0
        color   = G if pct >= 70 else (Y if pct >= 40 else R)
        print(f"  {area:<18} [{color}{bar}{RS}] {s:>2}/{m} pts ({pct}%)")
        total_score += s
        total_max   += m

    sep()
    total_pct = int(total_score / total_max * 100)
    color     = G if total_pct >= 70 else (Y if total_pct >= 40 else R)
    print(f"  {'TOTAL':<18} {color}{total_score}/{total_max} pts ({total_pct}%){RS}")

    print(f"\n{W}  Bugs críticos a corregir antes de subir a GCP:{RS}")
    all_go = "\n".join(read(f) for f in ROOT.glob("**/*.go"))
    bugs = []
    if "locatehost" in all_go:
        bugs.append("Typo 'locatehost' en go-grpc-server-writer/cmd/app/main.go")
    if contains_re(all_go, r'"localhost:\d+"') and "Getenv" not in all_go:
        bugs.append("Hostnames hardcodeados — cambiar a os.Getenv() con fallback")
    if not list(ROOT.glob("go-rabbit-consumer/internal/**/*.go")):
        bugs.append("go-rabbit-consumer es un stub — implementar RabbitMQ consumer + Valkey")
    rs_content = read(ROOT / "rust-api" / "src" / "main.rs")
    if "Hello" in rs_content and len(rs_content.strip()) < 100:
        bugs.append("rust-api es un stub — implementar servidor HTTP con Actix-web o Axum")
    if not list(ROOT.glob("locust/**/*.py")):
        bugs.append("Locust ausente — penalización -10% de la nota final")
    manual = [p for p in ROOT.glob("**/*.md") if "obsidian" not in str(p) and "CLAUDE.md" not in str(p) and p.stat().st_size > 500]
    if not manual:
        bugs.append("Manual técnico Markdown AUSENTE — la nota final será 0 sin esto")

    if bugs:
        for b in bugs:
            err(b)
    else:
        ok("Sin bugs críticos detectados")

    print()


# ─── Entry point ──────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Validador local M.U.M.N.K8s")
    parser.add_argument("--area", choices=["code", "infra", "messaging", "docs"],
                        help="Validar solo un área")
    args = parser.parse_args()

    print(f"\n{'═'*60}")
    print(f"  M.U.M.N.K8s — Validador Local")
    print(f"  Carnet: 201905884 | País: CHN | Deadline: 2026-04-30")
    print(f"{'═'*60}")

    area_map = {
        "code":      check_code,
        "infra":     check_infra,
        "messaging": check_messaging,
        "docs":      check_docs,
    }

    if args.area:
        fn = area_map[args.area]
        s, m = fn()
        report([(s, m)])
    else:
        results = [fn() for fn in [check_code, check_infra, check_messaging, check_docs]]
        report(results)


if __name__ == "__main__":
    main()
