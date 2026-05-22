-- 치지직 연동 시 본인 채널 표시명 저장 (UI 에서 channelId 대신 노출)
ALTER TABLE overlay_configs
    ADD COLUMN channel_name VARCHAR(100) NULL AFTER channel_id;
