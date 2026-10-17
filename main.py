
import logging
import json
import time
import uuid
from collections import deque
from datetime import datetime, timezone
from threading import Lock

from fastapi import FastAPI, Request, Query
from fastapi.responses import Response

app = FastAPI()

# Replace this with the email assigned to you by your course.
ASSIGNED_EMAIL = "24F3004430@ds.study.iitm.ac.in"

# Record the time when this Python process starts.
START_TIME = time.monotonic()

# A live counter shared by requests handled by this process.
request_count = 0
counter_lock = Lock()

# Keep the most recent 1000 structured log entries.
recent_logs = deque(maxlen=1000)
logs_lock = Lock()


class JSONFormatter(logging.Formatter):
    """Format ordinary Python log records as JSON."""

    def format(self, record):
        entry = getattr(record, "structured_entry", {})
        return json.dumps(entry)


logger = logging.getLogger("observability")
logger.setLevel(logging.INFO)
logger.handlers.clear()

handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger.addHandler(handler)
logger.propagate = False


@app.middleware("http")
async def observe_every_request(request: Request, call_next):
    global request_count

    request_id = str(uuid.uuid4())
    start = time.monotonic()

    with counter_lock:
        request_count += 1

    # Store the ID so the endpoint can use it if needed.
    request.state.request_id = request_id

    status_code = 500

    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        entry = {
            "level": "INFO",
            "ts": datetime.now(timezone.utc).isoformat(),
            "path": request.url.path,
            "request_id": request_id,
            "method": request.method,
            "status_code": status_code,
            "duration_ms": round(
                (time.monotonic() - start) * 1000, 3
            ),
        }

        with logs_lock:
            recent_logs.append(entry)

        log_record = logging.LogRecord(
            name="observability",
            level=logging.INFO,
            pathname=__file__,
            lineno=0,
            msg="HTTP request",
            args=(),
            exc_info=None,
        )
        log_record.structured_entry = entry
        logger.handle(log_record)


@app.get("/work")
def work(n: int = Query(default=1, ge=0)):
    # Do K units of actual work.
    done = 0
    for _ in range(n):
        done += 1

    return {
        "email": ASSIGNED_EMAIL,
        "done": done,
    }


@app.get("/metrics")
def metrics():
    global request_count

    prometheus_text = (
        "# HELP http_requests_total Total HTTP requests received.\n"
        "# TYPE http_requests_total counter\n"
        f"http_requests_total {request_count}\n"
    )

    return Response(
        content=prometheus_text,
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )

@app.get("/healthz")
def healthz():
    uptime = max(0.0, time.monotonic() - START_TIME)

    return {
        "status": "ok",
        "uptime_s": float(uptime),
    }


@app.get("/logs/tail")
def logs_tail(limit: int = Query(default=10, ge=1, le=1000)):
    with logs_lock:
        entries = list(recent_logs)

    return entries[-limit:]
