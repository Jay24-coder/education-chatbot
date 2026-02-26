"""Database package: connection pool and repositories.

This package centralizes all direct Postgres access:

- `pool` exposes process-wide async engine / pool helpers.
- `repositories` contains thin, testable data access abstractions.
"""

from . import pool  # noqa: F401

__all__ = ["pool"]

