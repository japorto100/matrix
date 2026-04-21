"""App-Factory fuer Matrix-Projekt (exec-17: OTel Observability).

Erstellt eine FastAPI App mit:
- Request-ID Middleware (X-Request-ID Propagation)
- JSON Request Logging
- OpenTelemetry Traces + Metrics + Logs (opt-in via OTEL_ENABLED=true)
- OpenObserve Basic Auth (via OPENOBSERVE_USER/PASSWORD)

OTel ist zentral hier — jeder Service der create_service_app() nutzt
bekommt Observability automatisch. Kein OTel-Init in Service-Code noetig.
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request

# Load env files — analog zu GO_ENV pattern:
#   1. .env als baseline (leere Defaults / committed-safe values)
#   2. .env.<APP_ENV> override (real keys, gitignored) — gewinnt
# Shell-Env gewinnt über beides (wird nicht überschrieben weil override=True nur file→file wirkt,
# load_dotenv mit override=True ersetzt NUR zuvor aus Datei geladene Werte, nicht os.environ-preset).
_root = Path(__file__).resolve().parents[1]
_env_base = _root / ".env"
if _env_base.exists():
    load_dotenv(dotenv_path=_env_base, override=False)

_app_env = os.getenv("APP_ENV", "development").strip().lower()
_env_specific = _root / f".env.{_app_env}"
if _env_specific.exists():
    load_dotenv(dotenv_path=_env_specific, override=True)

REQUEST_ID_HEADER = "X-Request-ID"


def _init_otel(app: FastAPI, title: str) -> None:
    """Initialize OpenTelemetry Traces + Metrics + Logs for this app.

    Activated via OTEL_ENABLED=true. Sends to OpenObserve gRPC endpoint.
    All imports in try/except — service starts without tracing if packages missing.
    """
    if os.getenv("OTEL_ENABLED", "").strip().lower() != "true":
        return

    try:
        import base64

        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        exporter_kwargs: dict = {}
        oo_user = os.getenv("OPENOBSERVE_USER", "").strip()
        if oo_user:
            oo_pass = os.getenv("OPENOBSERVE_PASSWORD", "")
            token = base64.b64encode(f"{oo_user}:{oo_pass}".encode()).decode()
            oo_org = os.getenv("OPENOBSERVE_ORG", "default")
            exporter_kwargs["headers"] = {
                "authorization": f"Basic {token}",
                "organization": oo_org,
            }

        provider = TracerProvider(resource=Resource.create({"service.name": title}))
        provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(**exporter_kwargs))
        )
        trace.set_tracer_provider(provider)
        FastAPIInstrumentor.instrument_app(app)

        # Traces outbound httpx calls (LLM APIs, Go Gateway, internal services)
        try:
            from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

            HTTPXClientInstrumentor().instrument()
        except ImportError:
            pass

        # — Metrics —
        try:
            from opentelemetry import metrics as otel_metrics
            from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
                OTLPMetricExporter,
            )
            from opentelemetry.sdk.metrics import MeterProvider
            from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

            _mp = MeterProvider(
                resource=Resource.create({"service.name": title}),
                metric_readers=[
                    PeriodicExportingMetricReader(OTLPMetricExporter(**exporter_kwargs))
                ],
            )
            otel_metrics.set_meter_provider(_mp)
        except ImportError:
            pass

        # — Logs bridge (Python logging → OTLP) —
        try:
            import logging as _stdlib_logging

            from opentelemetry._logs import set_logger_provider
            from opentelemetry.exporter.otlp.proto.grpc._log_exporter import (
                OTLPLogExporter,
            )
            from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
            from opentelemetry.sdk._logs.export import BatchLogRecordProcessor

            _lp = LoggerProvider(resource=Resource.create({"service.name": title}))
            _lp.add_log_record_processor(
                BatchLogRecordProcessor(OTLPLogExporter(**exporter_kwargs))
            )
            set_logger_provider(_lp)
            _stdlib_logging.root.addHandler(
                LoggingHandler(logger_provider=_lp, level=_stdlib_logging.INFO)
            )
        except ImportError:
            pass

    except ImportError:
        pass  # OTel packages optional — service starts without tracing


def create_service_app(title: str, version: str = "0.1.0") -> FastAPI:
    """Create FastAPI app with request logging and optional OTel middleware."""
    app = FastAPI(title=title, version=version)

    # OTel init — centralized, opt-in via OTEL_ENABLED=true
    _init_otel(app, title)

    logger = logging.getLogger(f"matrix.{title}")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False

    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):
        request_id = request.headers.get(REQUEST_ID_HEADER, "").strip() or str(
            uuid.uuid4()
        )
        request.state.request_id = request_id
        started = time.perf_counter()

        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id

        logger.info(
            json.dumps(
                {
                    "service": title,
                    "requestId": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                }
            )
        )
        return response

    return app
