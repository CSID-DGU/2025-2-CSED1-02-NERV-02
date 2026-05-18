FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
# CHZZK 채팅은 chzzkpy 의 user_client gateway 로 구독 (EIO=3 호환).
# OAuth flow 는 우리 raw httpx 로 처리 (chzzkpy 의 OAuth 흐름은 우회).
RUN pip install --no-cache-dir \
    "fastapi>=0.115.0" \
    "uvicorn[standard]>=0.30.0" \
    "pydantic>=2.0.0" \
    "httpx>=0.27.0" \
    "websockets>=12.0" \
    "chzzkpy==2.2.0" \
    "google-api-python-client>=2.0.0"

# chzzkpy 2.2.0 의 ahttp_client 가 pydantic 2.10+ 와 by_alias 호환 이슈가 있어
# install 직후 monkey-patch (sed). 실패 시 빌드 깨지지 않게 || true.
RUN sed -i \
        -e 's/by_alias=by_alias,/by_alias=True,/g' \
        -e 's/by_alias: Optional\[bool\] = False/by_alias: Optional[bool] = True/g' \
        /usr/local/lib/python3.12/site-packages/ahttp_client/extension/pydantic.py 2>/dev/null || true && \
    sed -i 's/open_packet\.model_dump()/open_packet.model_dump(by_alias=True)/g' \
        /usr/local/lib/python3.12/site-packages/chzzkpy/gateway.py 2>/dev/null || true

COPY app ./app

EXPOSE 8002

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
