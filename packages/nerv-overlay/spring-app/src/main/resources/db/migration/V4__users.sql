-- 회원 계정.
CREATE TABLE IF NOT EXISTS users (
    id              BIGINT          AUTO_INCREMENT PRIMARY KEY,
    username        VARCHAR(40)     NOT NULL UNIQUE,
    nickname        VARCHAR(40)     NOT NULL,
    password_hash   VARCHAR(255)    NOT NULL,
    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 향후 user-overlay 1:1 또는 1:N 관계 도입 시 overlay_configs 에 user_id 추가 예정.
-- 지금은 단일 활성 오버레이 모델 유지 (user_id 컬럼은 추가 안 함).
