from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.core import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=20,                           # 기본 커넥션 풀 크기
    max_overflow=10,                        # 추가 확장 가능 커넥션 수
    pool_pre_ping=True,                     # 재사용 전 연결 상태 확인
    pool_recycle=3600,                      # 1시간마다 커넥션 재생성 (초 단위)
    connect_args={"connect_timeout": 10,}   # 연결 타임아웃 10초
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine, 
    expire_on_commit=False
)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session