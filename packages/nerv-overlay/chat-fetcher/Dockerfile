FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
# CHZZK 채팅은 공식 OpenAPI Sessions API (socket.io) 로 구독.
# python-socketio 클라이언트로 직접 처리 (chzzkpy 의존성 없음).
RUN pip install --no-cache-dir \
    "fastapi>=0.115.0" \
    "uvicorn[standard]>=0.30.0" \
    "pydantic>=2.0.0" \
    "httpx>=0.27.0" \
    "websockets>=12.0" \
    "python-socketio[asyncio_client]>=5.11.0" \
    "google-api-python-client>=2.0.0"

COPY app ./app

EXPOSE 8002

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
