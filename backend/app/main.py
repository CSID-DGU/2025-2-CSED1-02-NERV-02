from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.api.v1.api import api_router

app = FastAPI(
    title="YouTube Comment Filtering System API",
    description="1차/2차/위험도/정책 모델을 엄격하게 분리하여 단계별 데이터 변화를 명확히 보여주는 API",
    version="1.0.2",
    openapi_version="3.0.2"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "YouTube Comment Filtering System API is running. Visit /docs for API documentation."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    # Swagger UI (Docs): http://localhost:8000/docs