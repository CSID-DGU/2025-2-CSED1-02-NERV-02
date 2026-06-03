FROM python:3.12-slim

# Build context = packages/ (docker-compose 에서 지정).
# 따라서 경로는 packages/ 기준.

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 1) torch CPU 버전 먼저 (기본 인덱스는 CUDA 빌드라 용량 큼 → CPU wheel 명시)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# 2) 로컬 nerv-filter SDK + 2차 의존성([ai]: transformers 등). torch 는 위에서 CPU 설치됨.
COPY nerv-filter/ /tmp/nerv-filter/
RUN pip install --no-cache-dir "/tmp/nerv-filter[ai]"

# 3) FastAPI 등 나머지 의존성
RUN pip install --no-cache-dir \
    "fastapi>=0.115.0" \
    "uvicorn[standard]>=0.30.0" \
    "pydantic>=2.0.0"

# 3) 앱 코드
COPY nerv-overlay/filter-service/app ./app

EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
