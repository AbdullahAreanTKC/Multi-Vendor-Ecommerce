from django.http import JsonResponse
from django.db import connection
import time


def health_check(request):
    """
    Lightweight health endpoint used by load balancers and Docker healthchecks.
    """
    start = time.time()
    db_ok = True
    try:
        connection.ensure_connection()
    except Exception:
        db_ok = False

    return JsonResponse(
        {
            "status": "ok" if db_ok else "degraded",
            "db": db_ok,
            "latency_ms": round((time.time() - start) * 1000, 2),
        }
    )

