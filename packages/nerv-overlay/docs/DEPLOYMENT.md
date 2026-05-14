# 운영 배포 — Railway (백엔드) + Vercel (프론트엔드)

이 문서는 nerv-overlay 를 Railway + Vercel 조합으로 배포하는 절차입니다.

## 전체 토폴로지

```
사용자 브라우저
  │ HTTPS
  ▼
┌──────────────────────┐         ┌────────────────────────────────────────┐
│ Vercel               │         │ Railway project (private network)      │
│ frontend (정적 SPA)  │ HTTPS   │                                        │
│ *.vercel.app         │ ──────► │  spring-app (public)  ←┐               │
└──────────────────────┘         │     │                  │               │
                                 │     │ internal         │               │
                                 │     ▼                  │               │
                                 │  chat-fetcher (internal)               │
                                 │  filter-service (internal)             │
                                 │  mysql (plugin)                        │
                                 └────────────────────────────────────────┘
```

외부 노출은 **spring-app** 1개만. 다른 서비스는 Railway 의 private DNS (`*.railway.internal`) 로만 통신.

---

## 0. 사전 준비

1. **Railway 계정** — https://railway.app — GitHub 로그인
2. **Vercel 계정** — https://vercel.com — GitHub 로그인
3. **이 레포가 GitHub 에 push 되어 있어야 함** (Railway/Vercel 가 GitHub 연동)
4. **CHZZK 개발자 센터** — https://developers.chzzk.naver.com — 앱 등록 + `CHZZK_CLIENT_ID` / `CHZZK_CLIENT_SECRET` 확보

---

## 1. Railway — 백엔드 4개 서비스 구성

### 1-1. 프로젝트 생성 + MySQL plugin

1. Railway 대시보드 → **New Project** → **Empty Project**
2. 프로젝트 안에서 **+ New** → **Database** → **Add MySQL**
3. MySQL 생성 후 `Variables` 탭에서 다음 값들이 자동 생성된 것 확인:
   - `MYSQL_HOST` `MYSQL_PORT` `MYSQL_DATABASE` `MYSQL_USER` `MYSQL_PASSWORD`
   - `MYSQL_URL` (`mysql://...` 형태)

### 1-2. spring-app 서비스 추가

1. **+ New** → **GitHub Repo** → 이 레포 선택
2. Service 이름: `spring-app`
3. **Settings** → **Source** → **Root Directory** = `packages/nerv-overlay/spring-app`
4. **Settings** → **Networking** → **Generate Domain** (예: `nerv-spring.up.railway.app`)
5. **Variables** 에 다음 입력:

   | Key | Value |
   |---|---|
   | `DB_HOST` | `${{MySQL.MYSQL_HOST}}` |
   | `DB_PORT` | `${{MySQL.MYSQL_PORT}}` |
   | `DB_NAME` | `${{MySQL.MYSQL_DATABASE}}` |
   | `DB_USER` | `${{MySQL.MYSQL_USER}}` |
   | `DB_PASSWORD` | `${{MySQL.MYSQL_PASSWORD}}` |
   | `JWT_SECRET` | (랜덤 32자 이상, 예: `openssl rand -base64 48` 결과) |
   | `PUBLIC_BASE_URL` | `https://nerv-spring.up.railway.app` (자기 도메인) |
   | `FRONTEND_BASE_URL` | `https://nerv-app.vercel.app` (Vercel 도메인 — Step 2 후 입력) |
   | `ALLOWED_ORIGINS` | `https://nerv-app.vercel.app,https://*.vercel.app` |
   | `FILTER_SERVICE_URL` | `http://filter-service.railway.internal:8001` |
   | `CHAT_FETCHER_URL` | `http://chat-fetcher.railway.internal:8002` |
   | `CHAT_FETCHER_WS_URL` | `ws://chat-fetcher.railway.internal:8002` |
   | `PORT` | `8080` |

### 1-3. chat-fetcher 서비스 추가

1. **+ New** → **GitHub Repo** → 같은 레포
2. Service 이름: `chat-fetcher`
3. **Settings** → **Source** → **Root Directory** = `packages/nerv-overlay/chat-fetcher`
4. **Settings** → **Networking** → public domain **생성하지 않음** (private only)
5. **Variables**:

   | Key | Value |
   |---|---|
   | `CHZZK_CLIENT_ID` | CHZZK 개발자 센터 발급값 |
   | `CHZZK_CLIENT_SECRET` | 같은 곳 |
   | `PORT` | `8002` |

### 1-4. filter-service 서비스 추가

filter-service Dockerfile 은 로컬 SDK (`packages/nerv-filter`) 를 build 시 함께 설치하므로 build context 가 `packages/` 전체여야 합니다.

1. **+ New** → **GitHub Repo** → 같은 레포
2. Service 이름: `filter-service`
3. **Settings** → **Source**:
   - **Root Directory** = `packages` ← (다른 서비스와 다르게 한 단계 위)
   - **Dockerfile Path** = `nerv-overlay/filter-service/Dockerfile`
4. public domain 생성 안 함
5. **Variables**: `PORT=8001`

### 1-5. CHZZK redirect_uri 등록

CHZZK 개발자 센터 → 내 앱 → **Redirect URI** 에 추가:
```
https://nerv-spring.up.railway.app/api/oauth/chzzk/callback
```

---

## 2. Vercel — 프론트엔드

1. https://vercel.com → **Add New** → **Project**
2. 같은 GitHub 레포 import
3. **Root Directory** = `packages/nerv-overlay/frontend`
4. **Framework Preset** = Vite (자동 감지됨)
5. **Environment Variables**:

   | Key | Value |
   |---|---|
   | `VITE_BACKEND_BASE_URL` | `https://nerv-spring.up.railway.app` |

6. **Deploy** 클릭. 빌드되면 `https://nerv-app.vercel.app` 같은 URL 발급.
7. Railway 의 spring-app Variables 로 돌아가서 `FRONTEND_BASE_URL` 과 `ALLOWED_ORIGINS` 에 실제 Vercel URL 반영하고 **Redeploy**.

---

## 3. 검증 체크리스트

| 항목 | 확인 방법 |
|---|---|
| Spring 헬스 | `curl https://nerv-spring.up.railway.app/actuator/health` → `{"status":"UP"}` |
| Frontend 로딩 | Vercel URL 브라우저 접속, 로그인/회원가입 UI 표시 |
| 회원가입 | 새 아이디로 가입, JWT 토큰 발급 |
| CHZZK 연동 | 내정보 → "치지직으로 로그인" → 동의 → `/profile?chzzk=connected` 로 복귀 + 카드 녹색 |
| 메인 페이지 | hero "연동 서비스" 가 CHZZK 칩으로 표시 |
| 실 채팅 | 본인 라이브 켜고 채팅창에 메시지 → 메인 페이지에 필터링 결과 표시 |
| OBS | `https://nerv-spring.up.railway.app/overlay/<token>` 를 OBS Browser Source 로 연결 |

---

## 4. 환경변수 요약 (붙여넣기용)

### Railway: spring-app
```env
DB_HOST=${{MySQL.MYSQL_HOST}}
DB_PORT=${{MySQL.MYSQL_PORT}}
DB_NAME=${{MySQL.MYSQL_DATABASE}}
DB_USER=${{MySQL.MYSQL_USER}}
DB_PASSWORD=${{MySQL.MYSQL_PASSWORD}}
JWT_SECRET=<랜덤 32자 이상>
PUBLIC_BASE_URL=https://<spring-domain>.up.railway.app
FRONTEND_BASE_URL=https://<vercel-domain>.vercel.app
ALLOWED_ORIGINS=https://<vercel-domain>.vercel.app,https://*.vercel.app
FILTER_SERVICE_URL=http://filter-service.railway.internal:8001
CHAT_FETCHER_URL=http://chat-fetcher.railway.internal:8002
CHAT_FETCHER_WS_URL=ws://chat-fetcher.railway.internal:8002
PORT=8080
```

### Railway: chat-fetcher
```env
CHZZK_CLIENT_ID=<발급값>
CHZZK_CLIENT_SECRET=<발급값>
PORT=8002
```

### Railway: filter-service
```env
PORT=8001
```

### Vercel: frontend
```env
VITE_BACKEND_BASE_URL=https://<spring-domain>.up.railway.app
```

---

## 5. 흔한 함정

- **CORS 에러**: `ALLOWED_ORIGINS` 에 Vercel preview 도메인까지 포함하려면 패턴 `https://*.vercel.app` 추가. allowedOriginPatterns 모드라 와일드카드 동작.
- **WebSocket 끊김**: 브라우저 콘솔에 `WebSocket connection to 'wss://...' failed` 가 뜨면 `VITE_BACKEND_BASE_URL` 가 https 인지 확인 (ws→wss 자동 변환). spring-app 가 public domain 있는지도 체크.
- **MySQL 마이그레이션 실패**: Flyway 가 V1~V5 순차 실행. 빈 DB 라면 자동 통과. 기존 DB 마이그레이션 충돌 시 `flyway_schema_history` 테이블 직접 점검.
- **filter-service 가 nerv-filter 못 찾음**: filter-service Dockerfile 의 build context 가 `packages/` 가 아닐 경우 발생. Railway 는 root directory 의 Dockerfile 그대로 빌드하므로 [filter-service/Dockerfile](../filter-service/Dockerfile) 의 `COPY` 경로 확인 필요.
- **JSONDecodeError (chat-fetcher)**: CHZZK socket.io 의 EIO=3 vs 우리 클라이언트 EIO=4 차이로 일부 packet decoding 실패 로그. SYSTEM/CHAT 이벤트 자체는 작동. 무시 가능.
- **CHZZK OAuth redirect 안 됨**: 개발자 센터에 등록한 redirect_uri 와 `PUBLIC_BASE_URL` + `/api/oauth/chzzk/callback` 가 정확히 일치해야 함 (trailing slash 주의).

---

## 6. 비용 메모

- Vercel: free hobby plan
- Railway: $5 credit / 월 (Hobby Plan). 소규모 사용 시 사실상 무료. 초과 시 사용량 기반 과금.
- 트래픽 늘면 Railway 만 유료, Vercel 은 대역폭 100GB/월 무료.

---

## 7. 트러블슈팅 명령

```bash
# Spring 로그
railway logs --service spring-app

# DB 직접 접속
railway connect MySQL

# 환경변수 확인
railway variables --service spring-app
```
