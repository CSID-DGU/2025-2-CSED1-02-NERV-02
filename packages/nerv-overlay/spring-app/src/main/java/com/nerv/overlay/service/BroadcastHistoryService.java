package com.nerv.overlay.service;

import com.nerv.overlay.entity.BroadcastSession;
import com.nerv.overlay.entity.FilteredMessage;
import com.nerv.overlay.repository.BroadcastSessionRepository;
import com.nerv.overlay.repository.FilteredMessageRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.Duration;
import java.time.LocalDateTime;
import java.util.List;

/**
 * 방송 세션 단위로 채팅 메시지 카운트와 필터링된 메시지를 히스토리에 보관.
 *
 * 동작:
 * - 사용자의 진행 중(ended_at IS NULL) 세션이 없으면 새 세션 생성, 있으면 거기에 누적
 * - 매 메시지마다 messageCount++, action ≠ NORMAL 이면 filteredCount++ + FilteredMessage 저장
 * - 마지막 메시지 후 IDLE_MINUTES 분 지나면 스케줄러가 자동 종료(ended_at 채움)
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class BroadcastHistoryService {

    /** 마지막 메시지 후 이 시간 지나면 세션 종료 처리. */
    private static final long IDLE_MINUTES = 15;

    private final BroadcastSessionRepository sessionRepo;
    private final FilteredMessageRepository messageRepo;

    /**
     * 한 채팅 메시지를 히스토리에 기록.
     * action 이 null/NORMAL/REVIEW 면 메시지 카운트만 증가, 그 외(차단류)면 본문도 저장.
     */
    @Transactional
    public void record(
            Long ownerUserId,
            String source,
            String channelId,
            String author,
            String originalText,
            String maskedText,
            String action,
            double score,
            String detectedWords
    ) {
        if (ownerUserId == null) return; // 비로그인(글로벌 더미) 은 히스토리 안 남김

        BroadcastSession session = sessionRepo
                .findFirstByOwnerUserIdAndEndedAtIsNull(ownerUserId)
                .orElseGet(() -> {
                    BroadcastSession s = BroadcastSession.builder()
                            .ownerUserId(ownerUserId)
                            .source(source)
                            .channelId(channelId)
                            .startedAt(LocalDateTime.now())
                            .lastMessageAt(LocalDateTime.now())
                            .build();
                    BroadcastSession saved = sessionRepo.save(s);
                    log.info("[History] 새 방송 세션 시작: id={} owner={} source={}",
                            saved.getId(), ownerUserId, source);
                    return saved;
                });

        session.setLastMessageAt(LocalDateTime.now());
        session.setMessageCount(session.getMessageCount() + 1);

        boolean isFiltered = action != null
                && !"NORMAL".equalsIgnoreCase(action)
                && !"REVIEW".equalsIgnoreCase(action)
                && !"ERROR".equalsIgnoreCase(action);

        if (isFiltered) {
            session.setFilteredCount(session.getFilteredCount() + 1);
            FilteredMessage msg = FilteredMessage.builder()
                    .sessionId(session.getId())
                    .author(author != null ? author : "Anonymous")
                    .originalText(originalText != null ? originalText : "")
                    .maskedText(maskedText)
                    .action(action)
                    .score(BigDecimal.valueOf(score).setScale(3, java.math.RoundingMode.HALF_UP))
                    .detectedWords(detectedWords)
                    .build();
            messageRepo.save(msg);
        }
    }

    /** 1분마다 idle 세션 자동 종료. */
    @Scheduled(fixedDelay = 60_000L)
    @Transactional
    public void closeIdleSessions() {
        LocalDateTime cutoff = LocalDateTime.now().minus(Duration.ofMinutes(IDLE_MINUTES));
        List<BroadcastSession> idle = sessionRepo.findByEndedAtIsNullAndLastMessageAtBefore(cutoff);
        if (idle.isEmpty()) return;
        for (BroadcastSession s : idle) {
            s.setEndedAt(s.getLastMessageAt());
        }
        log.info("[History] {}개 세션 자동 종료 (idle {}m)", idle.size(), IDLE_MINUTES);
    }

    @Transactional(readOnly = true)
    public List<BroadcastSession> listSessions(Long ownerUserId) {
        return sessionRepo.findByOwnerUserIdOrderByStartedAtDesc(ownerUserId);
    }

    @Transactional(readOnly = true)
    public BroadcastSession findSession(Long ownerUserId, Long sessionId) {
        BroadcastSession s = sessionRepo.findById(sessionId)
                .orElseThrow(() -> new IllegalArgumentException("세션을 찾을 수 없습니다: " + sessionId));
        if (!s.getOwnerUserId().equals(ownerUserId)) {
            throw new IllegalArgumentException("다른 사용자의 세션에 접근할 수 없습니다.");
        }
        return s;
    }

    @Transactional(readOnly = true)
    public List<FilteredMessage> listMessages(Long ownerUserId, Long sessionId) {
        findSession(ownerUserId, sessionId); // 권한 검증
        return messageRepo.findBySessionIdOrderByCreatedAtAsc(sessionId);
    }

    /** 체크박스 선택 — 한 번 true 가 되면 영구히 true (중복 재학습 방지). */
    @Transactional
    public FilteredMessage markForRelearn(Long ownerUserId, Long messageId) {
        FilteredMessage msg = messageRepo.findById(messageId)
                .orElseThrow(() -> new IllegalArgumentException("메시지를 찾을 수 없습니다: " + messageId));
        BroadcastSession s = sessionRepo.findById(msg.getSessionId()).orElseThrow();
        if (!s.getOwnerUserId().equals(ownerUserId)) {
            throw new IllegalArgumentException("다른 사용자의 메시지를 수정할 수 없습니다.");
        }
        if (!Boolean.TRUE.equals(msg.getSelectedForRelearn())) {
            msg.setSelectedForRelearn(true);
        }
        return msg;
    }
}
