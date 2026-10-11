from __future__ import annotations

import time
from math import ceil

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.types import ASGIApp

from app.core.config import get_settings


MAX_TRACKED_CLIENTS = 10_000


class InMemoryRateLimiter:
    def __init__(self, max_clients: int = MAX_TRACKED_CLIENTS) -> None:
        self._buckets: dict[str, tuple[float, int]] = {}
        self._max_clients = max_clients

    def check(self, key: str, *, limit: int, window_seconds: int, now: float | None = None) -> tuple[bool, int]:
        current = now if now is not None else time.monotonic()
        window = max(window_seconds, 1)
        allowed_limit = max(limit, 1)
        if key not in self._buckets and len(self._buckets) >= self._max_clients:
            self._evict(current)
        reset_at, count = self._buckets.get(key, (current + window, 0))
        if current >= reset_at:
            reset_at = current + window
            count = 0
        if count >= allowed_limit:
            retry_after = max(1, ceil(reset_at - current))
            self._buckets[key] = (reset_at, count)
            return False, retry_after
        self._buckets[key] = (reset_at, count + 1)
        return True, max(1, ceil(reset_at - current))

    def _evict(self, current: float) -> None:
        """Drop expired windows; if still full, drop the windows closest to expiry."""

        self._buckets = {key: value for key, value in self._buckets.items() if value[0] > current}
        overflow = len(self._buckets) - self._max_clients + 1
        if overflow > 0:
            for key in sorted(self._buckets, key=lambda item: self._buckets[item][0])[:overflow]:
                del self._buckets[key]

    def clear(self) -> None:
        self._buckets.clear()


rate_limiter = InMemoryRateLimiter()


def clear_rate_limit_state() -> None:
    rate_limiter.clear()


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        settings = get_settings()
        # CORS preflight carries no credentials or payload and is not counted.
        if not settings.rate_limit_enabled or request.method == "OPTIONS":
            return await call_next(request)

        key = _client_key(request, settings.rate_limit_trusted_proxy_count)
        allowed, retry_after = rate_limiter.check(
            key,
            limit=settings.rate_limit_requests,
            window_seconds=settings.rate_limit_window_seconds,
        )
        headers = {
            "X-RateLimit-Limit": str(settings.rate_limit_requests),
            "X-RateLimit-Window": str(settings.rate_limit_window_seconds),
        }
        if not allowed:
            if request.url.path.startswith(settings.assessment_api_prefix):
                from app.assessment_v2.errors import assessment_error_response

                response = assessment_error_response(
                    request,
                    "rate_limit_exceeded",
                    429,
                    "Too many requests.",
                )
                response.headers.update({**headers, "Retry-After": str(retry_after)})
                return response
            return JSONResponse(
                {"detail": "Too many requests."},
                status_code=429,
                headers={**headers, "Retry-After": str(retry_after)},
            )

        response = await call_next(request)
        response.headers.setdefault("X-RateLimit-Limit", str(settings.rate_limit_requests))
        response.headers.setdefault("X-RateLimit-Window", str(settings.rate_limit_window_seconds))
        return response


def _client_key(request: Request, trusted_proxy_count: int = 0) -> str:
    """Identify the caller without trusting client-supplied forwarding headers.

    ``X-Forwarded-For`` is only read when the deployment declares how many
    proxies sit in front of the API; the entry appended by the outermost
    trusted proxy is the client address. Anything further left is caller input.
    """

    if trusted_proxy_count > 0:
        hops = [hop.strip() for hop in request.headers.get("x-forwarded-for", "").split(",") if hop.strip()]
        if len(hops) >= trusted_proxy_count:
            return hops[-trusted_proxy_count]
    if request.client is not None:
        return request.client.host
    return "unknown"
