"""Minimal tracing: Tracer protocol and no-op/console implementation; correlation ID support."""

from typing import Any, Protocol, runtime_checkable

from app.observability.logging import get_logger

logger = get_logger(__name__)


@runtime_checkable
class Tracer(Protocol):
    """Protocol for request/agent tracing; supports correlation ID propagation."""

    def start_span(self, name: str, correlation_id: str | None = None, **attrs: Any) -> "Span":
        """Start a span. correlation_id is taken from request when present."""
        ...

    def set_correlation_id(self, correlation_id: str) -> None:
        """Set correlation ID for the current trace context."""
        ...


class Span(Protocol):
    """Minimal span interface."""

    def set_attribute(self, key: str, value: Any) -> None:
        ...

    def end(self) -> None:
        ...


class NoOpSpan:
    """No-op span for when tracing is disabled."""

    def set_attribute(self, key: str, value: Any) -> None:
        pass

    def end(self) -> None:
        pass


class NoOpTracer:
    """No-op tracer: spans do nothing."""

    def __init__(self) -> None:
        self._correlation_id: str | None = None

    def start_span(self, name: str, correlation_id: str | None = None, **attrs: Any) -> Span:
        if correlation_id is not None:
            self._correlation_id = correlation_id
        return NoOpSpan()

    def set_correlation_id(self, correlation_id: str) -> None:
        self._correlation_id = correlation_id

    @property
    def correlation_id(self) -> str | None:
        return self._correlation_id


class ConsoleTracer:
    """Minimal console tracer: logs span start/end and correlation ID."""

    def __init__(self) -> None:
        self._correlation_id: str | None = None

    def start_span(self, name: str, correlation_id: str | None = None, **attrs: Any) -> Span:
        if correlation_id is not None:
            self._correlation_id = correlation_id
        logger.info("span_start", span=name, correlation_id=self._correlation_id, **attrs)
        return _ConsoleSpan(name, self._correlation_id)

    def set_correlation_id(self, correlation_id: str) -> None:
        self._correlation_id = correlation_id

    @property
    def correlation_id(self) -> str | None:
        return self._correlation_id


class _ConsoleSpan:
    def __init__(self, name: str, correlation_id: str | None) -> None:
        self._name = name
        self._correlation_id = correlation_id
        self._attrs: dict[str, Any] = {}

    def set_attribute(self, key: str, value: Any) -> None:
        self._attrs[key] = value

    def end(self) -> None:
        logger.info(
            "span_end",
            span=self._name,
            correlation_id=self._correlation_id,
            **self._attrs,
        )
