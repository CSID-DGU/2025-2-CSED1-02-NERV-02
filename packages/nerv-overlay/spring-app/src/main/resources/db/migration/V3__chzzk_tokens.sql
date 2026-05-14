-- 치지직 OAuth 토큰 저장.
-- 인증 도입 전 단계라 단일 row 만 유지 (latest active token).
CREATE TABLE IF NOT EXISTS chzzk_tokens (
    id              BIGINT          AUTO_INCREMENT PRIMARY KEY,
    access_token    TEXT            NOT NULL,
    refresh_token   TEXT            NOT NULL,
    expires_at      TIMESTAMP       NOT NULL,
    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
