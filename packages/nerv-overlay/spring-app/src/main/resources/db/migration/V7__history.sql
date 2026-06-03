-- 방송 세션 + 필터링된 메시지 히스토리
-- 방송 단위로 묶어 보관하고, 추후 2차 모델 재학습용 후보 선택에 사용.

CREATE TABLE IF NOT EXISTS broadcast_sessions (
    id              BIGINT          AUTO_INCREMENT PRIMARY KEY,
    owner_user_id   BIGINT          NOT NULL,
    source          VARCHAR(20)     NOT NULL,                 -- CHZZK / YOUTUBE / DUMMY
    channel_id      VARCHAR(100)    NULL,
    started_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_message_at TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended_at        TIMESTAMP       NULL,                     -- NULL = 진행 중
    message_count   INT             NOT NULL DEFAULT 0,
    filtered_count  INT             NOT NULL DEFAULT 0,
    CONSTRAINT fk_session_owner FOREIGN KEY (owner_user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_session_owner_started (owner_user_id, started_at),
    INDEX idx_session_active (owner_user_id, ended_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS filtered_messages (
    id              BIGINT          AUTO_INCREMENT PRIMARY KEY,
    session_id      BIGINT          NOT NULL,
    author          VARCHAR(100)    NOT NULL,
    original_text   TEXT            NOT NULL,
    masked_text     TEXT            NULL,
    action          VARCHAR(20)     NOT NULL,                 -- REVIEW / PARTIAL_MASK / FULL_BLOCK
    score           DECIMAL(4,3)    NOT NULL DEFAULT 0.000,
    detected_words  TEXT            NULL,                     -- JSON 직렬화 (word|type 콤마 구분)
    selected_for_relearn BOOLEAN    NOT NULL DEFAULT FALSE,   -- 한 번 체크하면 영구히 true (재학습 후보)
    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_msg_session FOREIGN KEY (session_id) REFERENCES broadcast_sessions(id) ON DELETE CASCADE,
    INDEX idx_msg_session (session_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
