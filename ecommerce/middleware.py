import time
from typing import Callable
from django.core.cache import cache
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.conf import settings


class RateLimitMiddleware:
    """
    Lightweight IP-based rate limiting middleware to protect against bursts.
    Uses cache backend (Redis if configured, otherwise local memory).
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response
        self.requests_per_minute = getattr(settings, "RATE_LIMIT_REQUESTS_PER_MINUTE", 200)

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if self.requests_per_minute <= 0:
            return self.get_response(request)

        client_ip = self._get_client_ip(request)
        cache_key = f"ratelimit:{client_ip}"
        current_count = cache.get(cache_key, 0)

        if current_count >= self.requests_per_minute:
            return JsonResponse(
                {"detail": "Rate limit exceeded. Please slow down."},
                status=429,
            )

        # Increment with a 60-second window.
        try:
            cache.incr(cache_key)
        except ValueError:
            cache.set(cache_key, 1, timeout=60)
        else:
            # Ensure expiration is always set even when key already exists.
            cache.touch(cache_key, 60)

        return self.get_response(request)

    @staticmethod
    def _get_client_ip(request: HttpRequest) -> str:
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "unknown")

