"""
Configura OpenTelemetry com exportacao para Langfuse e auto-instrumentacao Anthropic via openlit.

Ativado automaticamente quando LANGFUSE_PUBLIC_KEY e LANGFUSE_SECRET_KEY estao definidos.
Se as chaves nao estiverem presentes, OTel e desabilitado silenciosamente.

Setup do Langfuse Cloud:
  https://cloud.langfuse.com ? Settings ? API Keys ? copiar pk-lf-... e sk-lf-...
"""
from __future__ import annotations

import base64
import logging
import os

log = logging.getLogger(__name__)

_initialized = False


def init():
    global _initialized
    if _initialized:
        return

    public_key = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
    secret_key = os.environ.get("LANGFUSE_SECRET_KEY", "")

    if public_key and secret_key:
        _setup_langfuse_otlp(public_key, secret_key)

    try:
        import openlit
        openlit.init()
        log.info("OpenLIT inicializado ? Anthropic auto-instrumentado via OTel.")
    except ImportError:
        log.warning("openlit nao instalado ? auto-instrumentacao Anthropic desabilitada.")

    _initialized = True


def _setup_langfuse_otlp(public_key: str, secret_key: str) -> None:
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        auth = base64.b64encode(f"{public_key}:{secret_key}".encode()).decode()
        otlp_endpoint = os.environ.get(
            "LANGFUSE_OTLP_ENDPOINT",
            "https://cloud.langfuse.com/api/public/otel/v1/traces",
        )

        exporter = OTLPSpanExporter(
            endpoint=otlp_endpoint,
            headers={"Authorization": f"Basic {auth}"},
        )
        provider = TracerProvider()
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)

        log.info("Langfuse OTLP exporter configurado: %s", otlp_endpoint)
    except ImportError:
        log.warning(
            "opentelemetry-sdk ou opentelemetry-exporter-otlp-proto-http nao instalados ? "
            "export para Langfuse desabilitado."
        )
