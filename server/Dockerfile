# Build context = repo root (see docker-compose.yml). Runs on the Pi (aarch64).
FROM python:3.13-slim-bookworm

WORKDIR /app

COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# panel-driving code + the spec (panels.local.json is mounted at runtime, not baked)
COPY pi-quickstart/*.py ./pi-quickstart/
COPY docs/idm64-gif-spec.md ./idm64-gif-spec.md
COPY server/app.py .

ENV IDM_PANEL=big
EXPOSE 8080

# one worker (single BLE central) + threads for concurrent health/validate; long timeout for uploads
CMD ["gunicorn", "-w", "1", "--threads", "4", "--timeout", "600", "-b", "0.0.0.0:8080", "app:app"]
