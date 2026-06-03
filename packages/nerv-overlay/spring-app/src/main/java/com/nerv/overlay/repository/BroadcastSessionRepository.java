package com.nerv.overlay.repository;

import com.nerv.overlay.entity.BroadcastSession;
import org.springframework.data.jpa.repository.JpaRepository;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

public interface BroadcastSessionRepository extends JpaRepository<BroadcastSession, Long> {

    /** 사용자의 현재 진행 중(ended_at IS NULL) 세션. */
    Optional<BroadcastSession> findFirstByOwnerUserIdAndEndedAtIsNull(Long ownerUserId);

    /** 사용자의 전체 세션 (최신 시작순) — 히스토리 목록. */
    List<BroadcastSession> findByOwnerUserIdOrderByStartedAtDesc(Long ownerUserId);

    /** 자동 종료 스케줄러용 — last_message_at 이 cutoff 보다 오래된 진행 중 세션. */
    List<BroadcastSession> findByEndedAtIsNullAndLastMessageAtBefore(LocalDateTime cutoff);
}
