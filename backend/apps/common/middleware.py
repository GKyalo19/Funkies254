"""Record method, path pattern, status and duration for API requests (AGENT-8)."""

import re
import time

UUID_RE = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)


class RequestMetricsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        started = time.perf_counter()
        response = self.get_response(request)
        path = request.path or ""
        if path.startswith("/api/"):
            self._record(request, response, started)
        return response

    def _record(self, request, response, started):
        from apps.common.models import RequestMetric

        duration_ms = int((time.perf_counter() - started) * 1000)
        path = UUID_RE.sub(":id", request.path)[:200]
        try:
            RequestMetric.objects.create(
                method=request.method[:8],
                path=path,
                status_code=getattr(response, "status_code", 0) or 0,
                duration_ms=duration_ms,
            )
        except Exception:
            # Metrics must never break a request.
            return
