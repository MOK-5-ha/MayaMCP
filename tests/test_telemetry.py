"""Unit tests for src.app_utils.telemetry module."""

import os
from unittest.mock import MagicMock, patch
from urllib.parse import urlparse

import pytest

from src.app_utils.telemetry import (
    _NoOpSpan,
    _NoOpTracer,
    get_tracer,
    is_cloud_trace_enabled,
    record_genai_attributes,
    setup_telemetry,
    trace_genai_span,
)


class TestTelemetryConfig:
    """Test environment variable precedence for Cloud Trace configuration."""

    def test_is_cloud_trace_enabled_default(self, monkeypatch):
        """Test is_cloud_trace_enabled returns True by default."""
        monkeypatch.delenv("MAYA_DISABLE_CLOUD_TRACE", raising=False)
        monkeypatch.delenv("BLACKWALL_DISABLE_CLOUD_TRACE", raising=False)
        monkeypatch.delenv("MAYA_EXPORT_CLOUD_TRACE", raising=False)
        monkeypatch.delenv("BLACKWALL_EXPORT_CLOUD_TRACE", raising=False)
        monkeypatch.delenv("INTEGRATION_TEST", raising=False)
        assert is_cloud_trace_enabled() is True

    def test_is_cloud_trace_disabled_via_maya_env(self, monkeypatch):
        """Test MAYA_DISABLE_CLOUD_TRACE disables telemetry."""
        monkeypatch.setenv("MAYA_DISABLE_CLOUD_TRACE", "true")
        assert is_cloud_trace_enabled() is False

    def test_is_cloud_trace_disabled_via_blackwall_env(self, monkeypatch):
        """Test BLACKWALL_DISABLE_CLOUD_TRACE disables telemetry."""
        monkeypatch.setenv("BLACKWALL_DISABLE_CLOUD_TRACE", "1")
        assert is_cloud_trace_enabled() is False

    def test_is_cloud_trace_disabled_in_integration_test_mode(self, monkeypatch):
        """Test INTEGRATION_TEST mode disables cloud trace export."""
        monkeypatch.setenv("INTEGRATION_TEST", "TRUE")
        assert is_cloud_trace_enabled() is False

    def test_is_cloud_trace_explicit_export_flag(self, monkeypatch):
        """Test MAYA_EXPORT_CLOUD_TRACE flag controls telemetry."""
        monkeypatch.delenv("MAYA_DISABLE_CLOUD_TRACE", raising=False)
        monkeypatch.delenv("BLACKWALL_DISABLE_CLOUD_TRACE", raising=False)
        monkeypatch.delenv("INTEGRATION_TEST", raising=False)

        monkeypatch.setenv("MAYA_EXPORT_CLOUD_TRACE", "false")
        assert is_cloud_trace_enabled() is False

        monkeypatch.setenv("MAYA_EXPORT_CLOUD_TRACE", "true")
        assert is_cloud_trace_enabled() is True


class TestSetupTelemetry:
    """Test setup_telemetry initialization and fallback."""

    def test_setup_telemetry_integration_test_skips(self, monkeypatch):
        """Test setup_telemetry returns None in INTEGRATION_TEST mode."""
        monkeypatch.setenv("INTEGRATION_TEST", "TRUE")
        result = setup_telemetry()
        assert result is None

    def test_setup_telemetry_auth_fallback_graceful(self, monkeypatch):
        """Test setup_telemetry gracefully falls back when google.auth fails."""
        monkeypatch.delenv("INTEGRATION_TEST", raising=False)
        monkeypatch.setenv("MAYA_DISABLE_CLOUD_TRACE", "false")

        with patch("google.auth.default", side_effect=Exception("No ADC available")):
            # Should not raise exception
            result = setup_telemetry()
            assert result is None or isinstance(result, str)

    def test_setup_telemetry_prompt_logging_env_configuration(self, monkeypatch):
        """Test setup_telemetry sets environment variables when LOGS_BUCKET_NAME is present."""
        monkeypatch.delenv("INTEGRATION_TEST", raising=False)
        monkeypatch.setenv("LOGS_BUCKET_NAME", "test-maya-logs-bucket")
        monkeypatch.setenv("OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT", "NO_CONTENT")

        with patch("google.auth.default", return_value=(MagicMock(), "test-gcp-proj")):
            bucket = setup_telemetry()
            assert bucket == "test-maya-logs-bucket"
            assert os.environ.get("OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT") == "NO_CONTENT"

    def test_setup_telemetry_attaches_cloud_trace_otlp_exporter(self, monkeypatch):
        """Test setup_telemetry attaches ADK OTLP span processor targeting Cloud Trace endpoint."""
        monkeypatch.delenv("INTEGRATION_TEST", raising=False)
        monkeypatch.setenv("MAYA_DISABLE_CLOUD_TRACE", "false")
        monkeypatch.setenv("MAYA_EXPORT_CLOUD_TRACE", "true")

        import src.app_utils.telemetry as telemetry
        telemetry._TELEMETRY_INITIALIZED = False

        from opentelemetry.sdk.trace import TracerProvider

        mock_provider = MagicMock(spec=TracerProvider)
        mock_provider.add_span_processor = MagicMock()
        mock_creds = MagicMock()

        with patch("opentelemetry.trace.get_tracer_provider", return_value=mock_provider), \
             patch("google.auth.default", return_value=(mock_creds, "test-gcp-proj")):
            telemetry.setup_telemetry()

            added_processors = [
                call[0][0] for call in mock_provider.add_span_processor.call_args_list
            ]
            try:
                assert mock_provider.add_span_processor.called
                assert len(added_processors) >= 1
                for sp in added_processors:
                    assert hasattr(sp, "span_exporter")
                    exporter = sp.span_exporter
                    endpoint = getattr(exporter, "_endpoint", "")
                    assert urlparse(endpoint).hostname == "telemetry.googleapis.com"
            finally:
                for sp in added_processors:
                    sp.shutdown()

    def test_completed_spans_sent_to_active_span_processor(self):
        """Test completed spans are received by the attached span processor with GenAI attributes."""
        from opentelemetry.sdk.trace import TracerProvider

        provider = TracerProvider()
        mock_processor = MagicMock()
        provider.add_span_processor(mock_processor)

        with patch("src.app_utils.telemetry.get_tracer", return_value=provider.get_tracer("test.tracer")):
            with trace_genai_span("test.completed.op", model="gemini-3.5-flash-lite", session_id="sess-xyz") as span:
                assert span is not None

        assert mock_processor.on_end.called
        completed_span = mock_processor.on_end.call_args[0][0]
        assert completed_span.name == "test.completed.op"
        assert completed_span.attributes.get("gen_ai.request.model") == "gemini-3.5-flash-lite"
        assert completed_span.attributes.get("session.id") == "sess-xyz"


class TestGenAISpanInstrumentation:
    """Test GenAI semantic span attribute recording."""

    def test_record_genai_attributes_all_fields(self):
        """Test recording complete set of OpenTelemetry GenAI semantic attributes."""
        mock_span = MagicMock()

        record_genai_attributes(
            mock_span,
            system="gemini",
            model="gemini-3.5-flash-lite",
            temperature=0.7,
            max_tokens=2048,
            input_tokens=150,
            output_tokens=75,
            finish_reasons=["STOP"],
            session_id="test-session-123",
            phase="ordering",
            metric_name="faithfulness",
            metric_score=4.5,
        )

        mock_span.set_attribute.assert_any_call("gen_ai.system", "gemini")
        mock_span.set_attribute.assert_any_call("gen_ai.request.model", "gemini-3.5-flash-lite")
        mock_span.set_attribute.assert_any_call("gen_ai.request.temperature", 0.7)
        mock_span.set_attribute.assert_any_call("gen_ai.request.max_tokens", 2048)
        mock_span.set_attribute.assert_any_call("gen_ai.usage.input_tokens", 150)
        mock_span.set_attribute.assert_any_call("gen_ai.usage.output_tokens", 75)
        mock_span.set_attribute.assert_any_call("gen_ai.response.finish_reasons", ["STOP"])
        mock_span.set_attribute.assert_any_call("session.id", "test-session-123")
        mock_span.set_attribute.assert_any_call("bartender.phase", "ordering")
        mock_span.set_attribute.assert_any_call("gen_ai.evaluation.metric_name", "faithfulness")
        mock_span.set_attribute.assert_any_call("gen_ai.evaluation.score", 4.5)

    def test_record_genai_attributes_none_span_safe(self):
        """Test record_genai_attributes does not fail on None span."""
        record_genai_attributes(None, model="gemini-3.5-flash-lite")

    def test_record_genai_attributes_exception_safe(self):
        """Test record_genai_attributes catches and suppresses span set_attribute errors."""
        mock_span = MagicMock()
        mock_span.set_attribute.side_effect = Exception("Span closed")
        record_genai_attributes(mock_span, model="gemini-3.5-flash-lite")

    def test_trace_genai_span_context_manager(self):
        """Test trace_genai_span records attributes and handles exceptions."""
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span

        with patch("src.app_utils.telemetry.get_tracer", return_value=mock_tracer):
            with trace_genai_span(
                "test.op",
                model="gemini-3.7-flash",
                temperature=1.0,
                session_id="session-xyz",
            ) as span:
                assert span is mock_span

            mock_span.set_attribute.assert_any_call("gen_ai.request.model", "gemini-3.7-flash")
            mock_span.set_attribute.assert_any_call("gen_ai.request.temperature", 1.0)
            mock_span.set_attribute.assert_any_call("session.id", "session-xyz")

    def test_trace_genai_span_exception_recording(self):
        """Test trace_genai_span records exception and sets error status on failure."""
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span

        with patch("src.app_utils.telemetry.get_tracer", return_value=mock_tracer):
            with pytest.raises(ValueError, match="Simulated error"):
                with trace_genai_span("test.op"):
                    raise ValueError("Simulated error")

            mock_span.record_exception.assert_called_once()
            mock_span.set_status.assert_called_once()


class TestNoOpFallbacks:
    """Test No-Op Tracer and Span behavior when OpenTelemetry is unavailable."""

    def test_noop_span_methods_do_not_raise(self):
        """Test all _NoOpSpan methods execute cleanly."""
        span = _NoOpSpan()
        span.set_attribute("key", "val")
        span.set_attributes({"key": "val"})
        span.record_exception(Exception("test"))
        span.set_status("ERROR", "desc")
        span.end()
        with span as s:
            assert s is span

    def test_noop_tracer_methods(self):
        """Test _NoOpTracer context manager and start_span."""
        tracer = _NoOpTracer()
        span = tracer.start_span("test")
        assert isinstance(span, _NoOpSpan)

        with tracer.start_as_current_span("test") as s:
            assert isinstance(s, _NoOpSpan)

    def test_get_tracer_returns_valid_instance(self):
        """Test get_tracer returns a usable tracer."""
        tracer = get_tracer("test")
        assert tracer is not None
        with tracer.start_as_current_span("span.name") as span:
            assert span is not None
