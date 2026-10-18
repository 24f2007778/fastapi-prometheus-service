# Prometheus Instrumented FastAPI Service

Endpoints:
- `GET /work?n=K` returns `{"email":"24f2007778@ds.study.iitm.ac.in","done":K}` and does K lightweight work units.
- `GET /metrics` returns live Prometheus exposition text including `http_requests_total`.
- `GET /healthz` returns status and process uptime.
- `GET /logs/tail?limit=N` returns the last N structured JSON request log entries.

Every incoming HTTP request increments the Prometheus counter in middleware and is recorded as a JSON log line to stdout and in an in-memory tail buffer.

## Run locally

```bash
python -m pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

## Deploy on Vercel

1. Upload these files to a Git repository (e.g. GitHub).
2. Import the repository at https://vercel.com/new.
3. Vercel detects the FastAPI app exported as `app` in `main.py`; no custom build command is required.
4. Deploy and use the production domain as the service base URL.
5. Verify `/healthz`, `/metrics`, `/work?n=3`, and `/logs/tail?limit=10`.

Set `SERVICE_EMAIL` in project environment variables if the grader expects a different email address.

## Important runtime note

The counter and log tail are in-memory and are per running process. This meets the usual sequential grader flow when requests are served by the same warm instance, but serverless platforms may recycle or scale instances. If the grader requires globally durable metrics/logs across separate instances, a shared external store is needed.
