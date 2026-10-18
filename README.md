# FastAPI Prometheus Work Service

## Run locally
```bash
python -m pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Endpoints
- `GET /work?n=K`
- `GET /metrics` (Prometheus exposition format)
- `GET /healthz`
- `GET /logs/tail?limit=N`

For deployment, use a host that runs a persistent web process. Start command:
`uvicorn main:app --host 0.0.0.0 --port $PORT`

The request counter and log tail are in memory per running process. If the platform runs multiple instances or recycles processes, in-memory values are not shared or durable.
