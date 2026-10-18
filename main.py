from collections import deque
from datetime import datetime, timezone
import json
import os
import time
import uuid

from fastapi import FastAPI, Query, Request
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest

EMAIL = os.getenv("SERVICE_EMAIL", "24f2007778@ds.study.iitm.ac.in")
START_TIME = time.monotonic()

# Prometheus Counter exports as http_requests_total.
HTTP_REQUESTS = Counter(
    "http_requests",
    "Total number of HTTP requests received by this service",
    ["method", "path"],
)

# In-memory ring buffer for the grader's /logs/tail check.
LOG_ENTRIES = deque(maxlen=2000)

app = FastAPI(title="Prometheus Instrumented Work Service")


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@app.middleware("http")
async def instrument_requests(request: Request, call_next):
    path = request.url.path
    method = request.method
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())

    # Increment before routing, so /metrics itself is counted as a request too.
    HTTP_REQUESTS.labels(method=method, path=path).inc()

    entry = {
        "level": "INFO",
        "ts": utc_timestamp(),
        "path": path,
        "request_id": request_id,
        "method": method,
    }
    LOG_ENTRIES.append(entry)
    # Emit one structured JSON record to the platform's runtime logs.
    print(json.dumps(entry, separators=(",", ":"), ensure_ascii=False), flush=True)

    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
    except Exception as exc:
        error_entry = {
            "level": "ERROR",
            "ts": utc_timestamp(),
            "path": path,
            "request_id": request_id,
            "method": method,
            "error": type(exc).__name__,
        }
        LOG_ENTRIES.append(error_entry)
        print(json.dumps(error_entry, separators=(",", ":"), ensure_ascii=False), flush=True)
        raise


@app.get("/")
async def root():
    return {"status": "ok", "service": "prometheus-work-service"}


@app.get("/work")
async def work(n: int = Query(default=1, ge=0, le=1_000_000)):
    # Perform n lightweight deterministic work units.
    accumulator = 0
    for i in range(n):
        accumulator = (accumulator + i) % 1_000_000_007
    # Keep the work result internal; the required response shape is exact.
    _ = accumulator
    return {"email": EMAIL, "done": n}


@app.get("/metrics", include_in_schema=False)
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "uptime_s": float(max(0.0, time.monotonic() - START_TIME))}


@app.get("/logs/tail")
async def logs_tail(limit: int = Query(default=100, ge=1, le=2000)):
    return list(LOG_ENTRIES)[-limit:]
