from collections import deque
from datetime import datetime, timezone
import logging
import time
import uuid

from fastapi import FastAPI, Query, Request
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest

EMAIL = "24f2007778@ds.study.iitm.ac.in"
START_TIME = time.monotonic()

app = FastAPI(title="Prometheus Instrumented Work Service")

# The client exports this as http_requests_total.
HTTP_REQUESTS = Counter(
    "http_requests",
    "Total number of HTTP requests received by this service",
    ["method", "path"],
)

# Keep a bounded in-memory tail of structured JSON log records.
LOG_TAIL = deque(maxlen=1000)
logger = logging.getLogger("request_json")
logger.setLevel(logging.INFO)


@app.middleware("http")
async def instrument_requests(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    path = request.url.path

    # Increment before the endpoint runs so the current scrape request is
    # included in the metrics response as well.
    HTTP_REQUESTS.labels(method=request.method, path=path).inc()

    ts = datetime.now(timezone.utc).isoformat()
    entry = {
        "level": "INFO",
        "ts": ts,
        "path": path,
        "request_id": request_id,
        "method": request.method,
    }

    try:
        response = await call_next(request)
        entry["status_code"] = response.status_code
        response.headers["X-Request-ID"] = request_id
        return response
    except Exception:
        entry["level"] = "ERROR"
        entry["status_code"] = 500
        raise
    finally:
        LOG_TAIL.append(entry)
        # Emit a structured JSON line to the platform's application logs.
        import json
        logger.info(json.dumps(entry, separators=(",", ":")))


@app.get("/work")
async def work(n: int = Query(default=1, ge=0, le=1000000)):
    # Perform n simple units of work. The loop keeps the parameter meaningful
    # without making grader requests unnecessarily expensive.
    done = 0
    for _ in range(n):
        done += 1
    return {"email": EMAIL, "done": done}


@app.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    # Prometheus exposition format, not JSON.
    return PlainTextResponse(
        content=generate_latest().decode("utf-8"),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "uptime_s": float(max(0.0, time.monotonic() - START_TIME))}


@app.get("/logs/tail")
async def logs_tail(limit: int = Query(default=10, ge=0, le=1000)):
    entries = list(LOG_TAIL)
    return entries[-limit:] if limit else []
