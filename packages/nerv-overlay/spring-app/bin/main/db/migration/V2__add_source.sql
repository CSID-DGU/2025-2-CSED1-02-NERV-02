-- chat source: DUMMY / CHZZK / YOUTUBE
ALTER TABLE overlay_configs
    ADD COLUMN source VARCHAR(20) NOT NULL DEFAULT 'DUMMY' AFTER channel_id;
