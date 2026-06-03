package com.nerv.overlay.service;

import com.nerv.overlay.entity.BroadcastSession;
import com.nerv.overlay.entity.FilteredMessage;
import com.nerv.overlay.repository.BroadcastSessionRepository;
import com.nerv.overlay.repository.FilteredMessageRepository;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Lazy;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.Duration;
import java.time.LocalDateTime;
import java.util.List;
import java.util.concurrent.ConcurrentHashMap;

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

    /** 마지막 메시지 후 이 시간 지나면 세션 종료 처리. 방송 OFF 인식 속도. */
    private static final long IDLE_MINUTES = 3;

    private final BroadcastSessionRepository sessionRepo;
    private final FilteredMessageRepository messageRepo;

    /**
     * 사용자별 lock — 같은 ownerUserId 에 대해 동시 record() 가 들어와
     * 새 세션이 중복 생성되는 race condition 방지.
     */
    private final ConcurrentHashMap<Long, Object> userLocks = new ConcurrentHashMap<>();

    /**
     * 사용자별 최근 본 메시지 ID 큐 — 같은 메시지가 여러 WS 세션으로 동시 수신되어
     * record() 가 중복 호출되는 케이스 방지 (메인 페이지 + OBS Browser Source 동시 사용 등).
     * LinkedHashMap 의 accessOrder 활용으로 LRU 비슷한 만료.
     */
    private static final int DEDUP_WINDOW = 200;
    private final ConcurrentHashMap<Long, java.util.LinkedHashSet<String>> recentMsgIds =
            new ConcurrentHashMap<>();

    /** self-injection — @Transactional proxy 호출용 (synchronized 바깥에서 트랜잭션 시작/커밋). */
    @Lazy
    @Autowired
    private BroadcastHistoryService self;

    /**
     * 한 채팅 메시지를 히스토리에 기록.
     * action 이 null/NORMAL/REVIEW 면 메시지 카운트만 증가, 그 외(차단류)면 본문도 저장.
     *
     * 트랜잭션은 recordInternal 에서 시작. synchronized 가 트랜잭션 commit 전에
     * 다른 스레드를 막아주어, "find 후 없으면 create" 패턴이 한 사용자에 대해 직렬화됨.
     */
    public void record(
            Long ownerUserId,
            String msgId,
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
        Object lock = userLocks.computeIfAbsent(ownerUserId, k -> new Object());
        synchronized (lock) {
            // dedup — 같은 사용자/같은 msgId 가 짧은 시간 내 두 번 들어오면 (다중 WS) 무시
            if (msgId != null && !msgId.isBlank()) {
                java.util.LinkedHashSet<String> seen = recentMsgIds
                        .computeIfAbsent(ownerUserId, k -> new java.util.LinkedHashSet<>());
                if (!seen.add(msgId)) {
                    log.debug("[History] 중복 메시지 dedup: owner={} msgId={}", ownerUserId, msgId);
                    return;
                }
                if (seen.size() > DEDUP_WINDOW) {
                    java.util.Iterator<String> it = seen.iterator();
                    it.next();
                    it.remove();
                }
            }
            self.recordInternal(ownerUserId, source, channelId, author,
                    originalText, maskedText, action, score, detectedWords);
        }
    }

    @Transactional
    public void recordInternal(
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

    /**
     * 서버 기동 시 과거에 잘못 만들어진 중복 활성 세션 정리.
     * 같은 사용자에 active(ended_at IS NULL) 세션이 2개 이상이면 가장 최신 1개만 남기고
     * 나머지는 last_message_at 으로 ended_at 채워서 종료 처리.
     */
    @PostConstruct
    public void cleanupOrphanActiveSessions() {
        List<BroadcastSession> all = sessionRepo.findAll().stream()
                .filter(s -> s.getEndedAt() == null)
                .toList();
        java.util.Map<Long, List<BroadcastSession>> byUser = new java.util.HashMap<>();
        for (BroadcastSession s : all) {
            byUser.computeIfAbsent(s.getOwnerUserId(), k -> new java.util.ArrayList<>()).add(s);
        }
        int merged = 0;
        for (List<BroadcastSession> group : byUser.values()) {
            if (group.size() <= 1) continue;
            group.sort((a, b) -> b.getStartedAt().compareTo(a.getStartedAt()));
            // 첫 번째 = 가장 최신 → 유지. 나머지 = 강제 종료.
            for (int i = 1; i < group.size(); i++) {
                BroadcastSession s = group.get(i);
                s.setEndedAt(s.getLastMessageAt());
                sessionRepo.save(s);
                merged++;
            }
        }
        if (merged > 0) {
            log.info("[History] 기동 시 중복 활성 세션 {}건 정리 완료", merged);
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
