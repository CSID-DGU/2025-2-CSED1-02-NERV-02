"""
시스템 사전(SystemDictionary) 초기 데이터 삽입 스크립트
사용법: python -m scripts.seed_system_dict
"""
import csv
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select, text
from app.db import AsyncSessionLocal
from app.db.models import SystemDictionary


DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "slang.csv"


def load_words_from_csv(path: Path) -> list[str]:
    seen = set()
    words = []
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        next(reader, None)  # 헤더 스킵
        for row in reader:
            if row and row[0].strip():
                word = row[0].strip()
                if word not in seen:
                    seen.add(word)
                    words.append(word)
    return words


async def seed():
    words = load_words_from_csv(DATA_PATH)
    print(f"CSV에서 {len(words)}개 단어 로드 완료")

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(SystemDictionary.word))
        existing = set(result.scalars().all())
        print(f"기존 시스템 사전: {len(existing)}개")

        new_words = [w for w in words if w not in existing]
        if not new_words:
            print("추가할 새 단어가 없습니다.")
            return

        # INSERT IGNORE로 collation 중복 무시
        added = 0
        for w in new_words:
            await session.execute(
                text("INSERT IGNORE INTO system_dictionaries (word, category) VALUES (:word, :category)"),
                {"word": w, "category": "SYSTEM_KEYWORD"}
            )
            added += 1

        await session.commit()

        result2 = await session.execute(select(SystemDictionary.word))
        final_count = len(result2.scalars().all())
        print(f"INSERT 시도: {added}개, 최종 시스템 사전: {final_count}개")


if __name__ == "__main__":
    asyncio.run(seed())
