# nerv-filter Examples

설치 후 실행할 수 있는 사용 예제 모음.

## 사전 준비

```bash
pip install nerv-filter[cli]
```

## 예제 목록

| 파일 | 설명 | 추가 의존성 |
|---|---|---|
| [01_basic_usage.py](01_basic_usage.py) | 1줄 호출, 인스턴스 재사용, 보안 수준별 비교 | 없음 |
| [02_batch_processing.py](02_batch_processing.py) | 배치 처리 + 처리 속도 비교 | 없음 |
| [03_dynamic_dictionary.py](03_dynamic_dictionary.py) | 화이트/블랙리스트 동적 갱신 | 없음 |
| [04_fastapi_integration.py](04_fastapi_integration.py) | FastAPI 백엔드 통합 (lifespan, async) | `fastapi`, `uvicorn` |
| [05_custom_dictionary.py](05_custom_dictionary.py) | 사용자 정의 사전 사용 | 없음 |

## 실행

```bash
# 단일 예제
python 01_basic_usage.py

# FastAPI 예제
pip install fastapi uvicorn
uvicorn 04_fastapi_integration:app --reload
```

## 핵심 패턴

```python
# 가장 일반적인 사용
from nerv_filter import NervFilter

flt = NervFilter()                       # 한 번만 생성
result = flt.analyze("텍스트")            # 반복 호출
print(result.action, result.masked_text)
```

## 주의사항

- **인스턴스 재사용 권장** — `NervFilter()` 생성마다 Kiwi 로딩(~3초) 발생
- **싱글톤 패턴** — 웹 서버에서는 lifespan 으로 1개 인스턴스 공유
- **Cold start** — 첫 호출 시 모델 로딩으로 ~3초 지연 가능
