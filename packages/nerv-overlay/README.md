# nerv-overlay

치지직 채팅 필터 오버레이 — OBS Browser Source 용 웹 서비스.

> Phase 2-A 진행 중. 현재 골격 단계.

## 아키텍처

```
[Browser / OBS]
       │ HTTP/WebSocket
       ▼
[Spring Boot :8080]   ← UI/인증/DB/WebSocket
       │ HTTP (internal)
       ▼
[FastAPI :8001]       ← nerv-filter SDK 호출
       │
       ▼
[MySQL :3308]         ← 설정 영속화
```

## 기술 스택

| 레이어 | 기술 |
|---|---|
| Frontend | React 18 + Vite + TypeScript (TBD) |
| Backend (메인) | Spring Boot 3.3 + Java 17 + Gradle |
| Backend (필터) | FastAPI + Python 3.10+ + nerv-filter SDK |
| DB | MySQL 8.0 |
| 마이그레이션 | Flyway |
| 통신 | REST + WebSocket |
| 오케스트레이션 | Docker Compose |

## 디렉토리

```
packages/nerv-overlay/
├── docker-compose.yml         # 전체 오케스트레이션
├── filter-service/            # FastAPI + nerv-filter SDK ✅ Day 1
├── spring-app/                # Spring Boot 메인 앱 ✅ Day 2
└── frontend/                  # React (Day 5+)
```

## 빠른 시작 (개발 환경)

### 1. 의존성

| 도구 | 버전 |
|---|---|
| Docker Desktop | 최신 |
| Java | 17 (또는 21) |
| Python | 3.10+ |
| Node.js | 20+ (frontend 작업 시) |
| Gradle (선택) | 8.x — IntelliJ 사용 시 wrapper 자동 |

### 2. 전체 띄우기 (Docker)

```bash
cd packages/nerv-overlay
docker compose up -d
docker compose ps     # 모든 서비스 healthy 확인
```

### 3. 검증

```bash
# 자체 헬스
curl http://localhost:8080/api/hello

# 통합 헬스 (Spring → filter-service)
curl http://localhost:8080/api/health/full

# 필터 위임 테스트
curl -X POST http://localhost:8080/api/filter/test \
    -H "Content-Type: application/json" \
    -d '{"text":"이 시발 진짜","security_level":"MEDIUM"}'
```

## 로컬 개발 (Docker 없이)

각 서비스를 따로 실행:

```bash
# filter-service
cd filter-service
pip install -e .
uvicorn app.main:app --port 8001

# Spring (다른 터미널) — IntelliJ 사용 권장
cd spring-app
# 옵션 A: IntelliJ → Open project → Run OverlayApplication
# 옵션 B: gradle wrapper 가 있으면 ./gradlew bootRun
# 옵션 C: gradle 글로벌 설치 후 gradle bootRun
```

> ⚠️ Spring 만 따로 띄울 때는 MySQL 이 별도로 떠 있어야 함:
> ```bash
> docker compose up -d mysql
> ```

## Spring 첫 실행 — Gradle Wrapper 생성

`gradlew` 가 없을 때 (현재 그렇음):

**방법 A: IntelliJ 활용 (가장 쉬움)**
1. IntelliJ IDEA 열기
2. Open → `packages/nerv-overlay/spring-app` 폴더 선택
3. "Trust Project" → 자동으로 wrapper 생성됨
4. Run 버튼으로 실행

**방법 B: Gradle 직접 설치**
- <https://gradle.org/install/> 참고
- 설치 후 `cd spring-app && gradle wrapper --gradle-version 8.10`

## API (현재)

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/api/hello` | 자체 헬스 |
| GET | `/api/health/full` | filter-service 포함 헬스 |
| POST | `/api/filter/test` | 텍스트 분석 (filter-service 위임) |
| GET | `/actuator/health` | Spring Actuator 헬스 |

## 다음 단계

- [x] Day 3: Spring ↔ filter-service 통합 검증
- [x] Day 4: 설정 CRUD API + Entity/Repository
- [x] Day 5: React 프론트 (설정 페이지)
- [x] Day 6: 오버레이 페이지 + WebSocket + 더미 메시지 + 측정 코드
- [ ] Day 6.5: chat-fetcher 서비스 (chzzkpy + YouTube API)
- [ ] Day 7+: 측정 결과 분석 / UI 다듬기

## 측정 사용법

1. 설정 페이지에서 새 오버레이 생성 → URL 복사
2. 같은 URL 을 다른 브라우저 탭에서 열기 (또는 OBS Browser Source)
3. F12 DevTools 열기 → Console 탭
4. 1~3초 간격으로 더미 메시지가 표시됨
5. 콘솔에 `[Latency]` 로그가 메시지마다 출력:
   - `filter_ms`: filter-service 호출 시간
   - `server_to_client_ms`: Spring → Browser 전송 시간
   - `e2e_render_ms`: 수신 → DOM 렌더 시간
   - `total_ms`: 메시지 생성 → 화면 표시 (전체)
