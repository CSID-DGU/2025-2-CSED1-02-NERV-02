-- NERV Overlay 초기 스키마
-- Phase 2-A 단계: 인증 X, 단일 설정 CRUD 모델

-- 오버레이 설정: 사용자가 만든 채팅 오버레이 1개당 row 1개
CREATE TABLE IF NOT EXISTS overlay_configs (
    id              BIGINT          AUTO_INCREMENT PRIMARY KEY,
    overlay_token   VARCHAR(32)     NOT NULL UNIQUE COMMENT '공개 URL 슬러그',
    name            VARCHAR(100)    NOT NULL DEFAULT '내 오버레이',

    -- 채널 (치지직)
    channel_id      VARCHAR(100)    NULL,

    -- 필터 설정
    security_level      VARCHAR(10)     NOT NULL DEFAULT 'MEDIUM',
    block_display_mode  VARCHAR(20)     NOT NULL DEFAULT 'MASK',  -- MASK / HIDE / PLACEHOLDER
    placeholder_text    VARCHAR(50)     NOT NULL DEFAULT '[필터됨]',
    show_score          BOOLEAN         NOT NULL DEFAULT FALSE,

    -- 시각 설정 (Phase 후반에서 확장)
    style_config_json   TEXT            NULL,

    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_overlay_token (overlay_token)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 사용자별 화이트/블랙리스트
CREATE TABLE IF NOT EXISTS overlay_dictionary (
    id              BIGINT          AUTO_INCREMENT PRIMARY KEY,
    overlay_id      BIGINT          NOT NULL,
    word            VARCHAR(100)    NOT NULL,
    list_type       VARCHAR(20)     NOT NULL,  -- WHITELIST / BLACKLIST
    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE KEY uq_overlay_word (overlay_id, word, list_type),
    INDEX idx_overlay_id (overlay_id),
    CONSTRAINT fk_dict_overlay FOREIGN KEY (overlay_id) REFERENCES overlay_configs(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
