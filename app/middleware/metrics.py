import time
import requests
from starlette.middleware.base import BaseHTTPMiddleware

TELEGRAF_URL = "http://telegraf:8186/telegraf"


def _send(metric: str):
    try:
        requests.post(TELEGRAF_URL, data=metric, timeout=1)
    except Exception:
        pass


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.time()
        response = await call_next(request)
        duration_ms = (time.time() - start) * 1000

        endpoint = request.url.path.replace("/", "_").strip("_") or "root"
        status = response.status_code
        error = 1 if status >= 400 else 0

        _send(
            f"http_requests,"
            f"endpoint={endpoint},method={request.method},status={status} "
            f"duration_ms={duration_ms:.2f},error={error}i"
        )

        return response
