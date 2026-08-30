# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""OpenTelemetry GenAI Semantic Span Instrumentation and Google Cloud Trace Exporter."""

import contextlib
import logging
import os
import threading
from collections.abc import Generator, Sequence
from typing import Any

import google.auth
from google.adk.cli.api_server import _setup_instrumentation_lib_if_installed
from google.adk.telemetry.google_cloud import get_gcp_exporters, get_gcp_resource
from google.adk.telemetry.setup import maybe_set_otel_providers

try:
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor
    from opentelemetry.trace import Span, Status, StatusCode
except ImportError:
    trace = None  # type: ignore[assignment]
    Resource = None  # type: ignore[assignment, misc]
    TracerProvider = None  # type: ignore[assignment, misc]
    BatchSpanProcessor = None  # type: ignore[assignment, misc]
    SimpleSpanProcessor = None  # type: ignore[assignment, misc]
    Span = Any  # type: ignore[assignment, misc]
    Status = Any  # type: ignore[assignment, misc]
    StatusCode = Any  # type: ignore[assignment, misc]

try:
    from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
except ImportError:
    CloudTraceSpanExporter = None  # type: ignore[assignment, misc]

logger = logging.getLogger(__name__)

_TELEMETRY_LOCK = threading.Lock()
_TELEMETRY_INITIALIZED = False
_TRACER_PROVIDER: Any = None


def is_cloud_trace_enabled() -> bool:
    """Determine if Cloud Trace export is enabled based on environment variables.

    Precedence:
    1. MAYA_DISABLE_CLOUD_TRACE / BLACKWALL_DISABLE_CLOUD_TRACE (if true -> False)
    2. MAYA_EXPORT_CLOUD_TRACE / BLACKWALL_EXPORT_CLOUD_TRACE (if set -> explicit boolean)
    3. INTEGRATION_TEST == 'TRUE' -> False
    4. Default -> True
    """
    disable_flag = os.getenv(
        "MAYA_DISABLE_CLOUD_TRACE",
        os.getenv("BLACKWALL_DISABLE_CLOUD_TRACE", "false")
    ).strip().lower() in ("true", "1", "yes")

    if disable_flag:
        return False

    if os.getenv("INTEGRATION_TEST") == "TRUE":
        return False

    export_flag = os.getenv("MAYA_EXPORT_CLOUD_TRACE", os.getenv("BLACKWALL_EXPORT_CLOUD_TRACE"))
    if export_flag is not None:
        return export_flag.strip().lower() in ("true", "1", "yes")

    return True


def setup_telemetry() -> str | None:
    """Configure GenAI prompt/response logging and OpenTelemetry Cloud Trace exporter.

    Returns:
        Optional GCS bucket name used for prompt/response logging.
    """
    global _TELEMETRY_INITIALIZED, _TRACER_PROVIDER

    if os.getenv("INTEGRATION_TEST") == "TRUE":
        logger.info("Skipping telemetry setup in integration test mode")
        return None

    # Keep full prompts/responses out of trace span attributes (use GenAI logging instead).
    os.environ.setdefault("ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS", "false")

    bucket = os.environ.get("LOGS_BUCKET_NAME")
    capture_content = os.environ.get(
        "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT", "false"
    )
    if bucket and capture_content != "false":
        logger.info(
            "Prompt-response logging enabled - mode: NO_CONTENT (metadata only, no prompts/responses)"
        )
        os.environ["OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"] = "NO_CONTENT"
        os.environ.setdefault("OTEL_INSTRUMENTATION_GENAI_UPLOAD_FORMAT", "jsonl")
        os.environ.setdefault("OTEL_INSTRUMENTATION_GENAI_COMPLETION_HOOK", "upload")
        os.environ.setdefault(
            "OTEL_SEMCONV_STABILITY_OPT_IN", "gen_ai_latest_experimental"
        )
        commit_sha = os.environ.get("COMMIT_SHA", "dev")
        os.environ.setdefault(
            "OTEL_RESOURCE_ATTRIBUTES",
            f"service.namespace=migrate-google-adk-agents,service.version={commit_sha}",
        )
        path = os.environ.get("GENAI_TELEMETRY_PATH", "completions")
        os.environ.setdefault(
            "OTEL_INSTRUMENTATION_GENAI_UPLOAD_BASE_PATH",
            f"gs://{bucket}/{path}",
        )
    else:
        logger.info(
            "Prompt-response logging disabled (set LOGS_BUCKET_NAME=your-bucket and OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=NO_CONTENT to enable)"
        )

    with _TELEMETRY_LOCK:
        export_to_cloud = is_cloud_trace_enabled()

        if trace is not None and TracerProvider is not None:
            try:
                # Initialize TracerProvider if not already set
                current_provider = trace.get_tracer_provider()
                if not isinstance(current_provider, TracerProvider):
                    resource = Resource.create({
                        "service.name": "mayamcp",
                        "service.version": os.environ.get("COMMIT_SHA", "2.0.0"),
                    }) if Resource is not None else None
                    provider = TracerProvider(resource=resource) if resource is not None else TracerProvider()
                    _TRACER_PROVIDER = provider
                    trace.set_tracer_provider(provider)
                else:
                    _TRACER_PROVIDER = current_provider
            except Exception as prov_err:
                logger.warning(f"Failed to initialize OpenTelemetry TracerProvider ({prov_err})")

        # Set up OpenTelemetry exporters for Cloud Trace and Cloud Logging
        if export_to_cloud:
            try:
                credentials, project_id = google.auth.default()
                project = (
                    project_id
                    or os.getenv("GCP_PROJECT")
                    or os.getenv("GOOGLE_CLOUD_PROJECT")
                )

                # Configure ADK telemetry hooks
                otel_hooks = get_gcp_exporters(
                    enable_cloud_tracing=True,
                    enable_cloud_metrics=False,
                    enable_cloud_logging=True,
                    google_auth=(credentials, project),
                )
                otel_resource = get_gcp_resource(project)
                maybe_set_otel_providers(
                    otel_hooks_to_setup=[otel_hooks],
                    otel_resource=otel_resource,
                )

                # Configure direct CloudTraceSpanExporter on TracerProvider if available
                if (
                    CloudTraceSpanExporter is not None
                    and _TRACER_PROVIDER is not None
                    and BatchSpanProcessor is not None
                ):
                    cloud_exporter = CloudTraceSpanExporter(
                        project_id=project,
                        credentials=credentials,
                    )
                    _TRACER_PROVIDER.add_span_processor(BatchSpanProcessor(cloud_exporter))
                    logger.info(f"OpenTelemetry Google Cloud Trace exporter configured for project '{project}'")

                # Set up GenAI SDK instrumentation
                _setup_instrumentation_lib_if_installed()
            except Exception as otel_err:
                logger.warning(
                    f"Skipping OpenTelemetry GCP setup ({otel_err}); "
                    "falling back to non-blocking local logging."
                )
        else:
            logger.info("OpenTelemetry Cloud Trace export disabled or running in local mode.")

        _TELEMETRY_INITIALIZED = True

    return bucket


class _NoOpSpan:
    """Fallback No-Op Span when OpenTelemetry is unavailable or disabled."""

    def set_attribute(self, key: str, value: Any) -> None:
        pass

    def set_attributes(self, attributes: dict[str, Any]) -> None:
        pass

    def record_exception(self, exception: BaseException) -> None:
        pass

    def set_status(self, status: Any, description: str | None = None) -> None:
        pass

    def end(self) -> None:
        pass

    def __enter__(self) -> "_NoOpSpan":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        pass


class _NoOpTracer:
    """Fallback No-Op Tracer when OpenTelemetry is unavailable."""

    @contextlib.contextmanager
    def start_as_current_span(
        self, name: str, *args, **kwargs
    ) -> Generator[_NoOpSpan, None, None]:
        span = _NoOpSpan()
        yield span

    def start_span(self, name: str, *args, **kwargs) -> _NoOpSpan:
        return _NoOpSpan()


def get_tracer(name: str = "mayamcp") -> Any:
    """Get an OpenTelemetry tracer instance or fallback to a NoOpTracer."""
    if trace is None:
        return _NoOpTracer()
    try:
        return trace.get_tracer(name)
    except Exception:
        return _NoOpTracer()


def record_genai_attributes(
    span: Any,
    *,
    system: str = "gemini",
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    finish_reasons: Sequence[str] | None = None,
    session_id: str | None = None,
    phase: str | None = None,
    metric_name: str | None = None,
    metric_score: float | int | None = None,
) -> None:
    """Safely record OpenTelemetry GenAI semantic convention attributes on a span.

    Args:
        span: OpenTelemetry Span (or NoOpSpan)
        system: GenAI system identifier ('gemini' or 'vertex_ai')
        model: Model identifier
        temperature: Generation temperature
        max_tokens: Max output token limit
        input_tokens: Prompt / input token count
        output_tokens: Completion / output token count
        finish_reasons: List of finish reason strings
        session_id: Application session identifier
        phase: Bartender conversational phase
        metric_name: Active evaluation metric name
        metric_score: Active evaluation metric score
    """
    if span is None:
        return

    try:
        if system:
            span.set_attribute("gen_ai.system", str(system))
        if model:
            span.set_attribute("gen_ai.request.model", str(model))
        if temperature is not None:
            span.set_attribute("gen_ai.request.temperature", float(temperature))
        if max_tokens is not None:
            span.set_attribute("gen_ai.request.max_tokens", int(max_tokens))
        if input_tokens is not None:
            span.set_attribute("gen_ai.usage.input_tokens", int(input_tokens))
        if output_tokens is not None:
            span.set_attribute("gen_ai.usage.output_tokens", int(output_tokens))
        if finish_reasons:
            span.set_attribute("gen_ai.response.finish_reasons", [str(r) for r in finish_reasons])
        if session_id:
            span.set_attribute("session.id", str(session_id))
        if phase:
            span.set_attribute("bartender.phase", str(phase))
        if metric_name:
            span.set_attribute("gen_ai.evaluation.metric_name", str(metric_name))
        if metric_score is not None:
            span.set_attribute("gen_ai.evaluation.score", float(metric_score))
    except Exception as attr_err:
        logger.debug(f"Failed to record GenAI span attributes: {attr_err}")


@contextlib.contextmanager
def trace_genai_span(
    name: str,
    tracer_name: str = "mayamcp",
    system: str = "gemini",
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    session_id: str | None = None,
    phase: str | None = None,
) -> Generator[Any, None, None]:
    """Context manager for tracing a GenAI operation with OpenTelemetry semantic conventions.

    Yields:
        The active Span.
    """
    tracer = get_tracer(tracer_name)
    with tracer.start_as_current_span(name) as span:
        record_genai_attributes(
            span,
            system=system,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            session_id=session_id,
            phase=phase,
        )
        try:
            yield span
        except Exception as exc:
            if hasattr(span, "record_exception"):
                span.record_exception(exc)
            if hasattr(span, "set_status") and StatusCode is not None and Status is not None:
                span.set_status(Status(StatusCode.ERROR, str(exc)))
            raise
