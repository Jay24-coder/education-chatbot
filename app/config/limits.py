"""Rate limit configuration."""

from pydantic import BaseModel


class RateLimitConfig(BaseModel):
    """Rate limit configuration for API endpoints."""

    # Per-user rate limits
    requests_per_minute: int = 60
    requests_per_hour: int = 1000

    # Per-tenant rate limits (for multi-tenancy)
    tenant_requests_per_minute: int = 1000
    tenant_requests_per_hour: int = 10000

    # Burst allowance
    burst_size: int = 10


# Global rate limit configuration
rate_limit_config = RateLimitConfig()
