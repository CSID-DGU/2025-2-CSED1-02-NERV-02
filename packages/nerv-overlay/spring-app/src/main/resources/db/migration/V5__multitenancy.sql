-- 사용자별 오버레이 + 사용자별 치지직 토큰
-- owner_user_id NULL = 비로그인용 글로벌 더미 row
-- chzzk_tokens.user_id 는 NOT NULL — 토큰은 항상 사용자에 속함

ALTER TABLE overlay_configs
    ADD COLUMN owner_user_id BIGINT NULL AFTER id,
    ADD CONSTRAINT fk_overlay_owner FOREIGN KEY (owner_user_id) REFERENCES users(id) ON DELETE CASCADE,
    ADD INDEX idx_overlay_owner (owner_user_id);

-- 한 사용자당 한 row 만. 기존 row 는 user_id NULL → 정리.
DELETE FROM chzzk_tokens;

ALTER TABLE chzzk_tokens
    ADD COLUMN user_id BIGINT NOT NULL AFTER id,
    ADD CONSTRAINT fk_chzzk_token_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    ADD UNIQUE KEY uq_chzzk_token_user (user_id);
