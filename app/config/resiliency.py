"""Resiliency configuration: timeouts, retries, circuit breakers."""

from pydantic import BaseModel


class TimeoutConfig(BaseModel):
    """Timeout configuration for outbound calls."""

    # LLM provider timeouts
    llm_request_timeout: float = 30.0  # seconds
    llm_stream_timeout: float = 60.0

    # Database timeouts
    db_query_timeout: float = 5.0
    db_connection_timeout: float = 10.0

    # Vector store timeouts
    vector_query_timeout: float = 10.0

    # General HTTP timeouts
    http_timeout: float = 10.0


class RetryConfig(BaseModel):
    """Retry configuration with exponential backoff."""

    max_retries: int = 3
    initial_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    exponential_base: float = 2.0
    jitter: bool = True


class CircuitBreakerConfig(BaseModel):
    """Circuit breaker configuration."""

    failure_threshold: int = 5  # failures before opening
    success_threshold: int = 2  # successes before half-open
    timeout: float = 60.0  # seconds before attempting recovery


class ResiliencyConfig(BaseModel):
    """Global resiliency configuration."""

    timeouts: TimeoutConfig = TimeoutConfig()
    retries: RetryConfig = RetryConfig()
    circuit_breaker: CircuitBreakerConfig = CircuitBreakerConfig()


# Global resiliency configuration
resiliency_config = ResiliencyConfig()
