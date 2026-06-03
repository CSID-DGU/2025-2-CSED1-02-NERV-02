-- 2차(AI) 필터 사용 여부 — 사용자별 토글. 기본값 TRUE (모델 동봉돼 있으니 켜둠).
ALTER TABLE overlay_configs
    ADD COLUMN use_ai_filter BOOLEAN NOT NULL DEFAULT TRUE AFTER show_score;
