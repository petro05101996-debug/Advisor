FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8110 \
    MAX_POST_BYTES=2097152

WORKDIR /app
COPY . /app

EXPOSE 8110
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python - <<'PY'
import os, urllib.request
port=os.environ.get('PORT','8110')
urllib.request.urlopen(f'http://127.0.0.1:{port}/', timeout=3).read(200)
PY

CMD ["python", "integration_architect_pro.py"]
