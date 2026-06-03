-- 히스토리 초기화
-- WS 다중 연결로 인한 record() 중복 호출 버그(2026-06-04 phs 브랜치에서 dedup 추가)로
-- 이전에 수집된 데이터에는 중복 행이 섞여 있음. 깨끗한 상태로 재수집하기 위해 비운다.
-- FK 제약(filtered_messages → broadcast_sessions) 때문에 자식부터 비워야 한다.

DELETE FROM filtered_messages;
DELETE FROM broadcast_sessions;
ALTER TABLE filtered_messages AUTO_INCREMENT = 1;
ALTER TABLE broadcast_sessions AUTO_INCREMENT = 1;
