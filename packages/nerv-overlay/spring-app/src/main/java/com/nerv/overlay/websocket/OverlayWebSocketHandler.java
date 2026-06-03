package com.nerv.overlay.websocket;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.nerv.overlay.client.ChatFetcherSubscriber;
import com.nerv.overlay.client.FilterServiceClient;
import com.nerv.overlay.dto.FilterAnalyzeRequest;
import com.nerv.overlay.dto.OverlayChatMessage;
import com.nerv.overlay.dto.OverlayConfigDto;
import com.nerv.overlay.entity.ChzzkToken;
import com.nerv.overlay.service.BroadcastHistoryService;
import com.nerv.overlay.service.ChzzkOAuthService;
import com.nerv.overlay.service.OverlayConfigService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.handler.TextWebSocketHandler;
import reactor.core.Disposable;
import reactor.core.publisher.Mono;

import java.io.IOException;
import java.net.URI;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * /ws/overlay/{token} 엔드포인트.
 *
 * 동작:
 *  - 연결 시 token → OverlayConfig 조회 → chat-fetcher 의 source/channel 구독
 *  - chat-fetcher 메시지 도착 → filter-service 호출 → 클라이언트에 push
 *  - 연결 종료 시 chat-fetcher 구독 해제
 *
 * channel_id 가 비어있으면 source 와 무관하게 더미 채널 (overlay_token 자체) 사용.
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class OverlayWebSocketHandler extends TextWebSocketHandler {

    private final OverlayConfigService configService;
    private final FilterServiceClient filterClient;
    private final ChatFetcherSubscriber chatFetcher;
    private final ChzzkOAuthService chzzkOAuthService;
    private final BroadcastHistoryService historyService;
    private final ObjectMapper objectMapper;

    private final Map<String, SessionContext> sessions = new ConcurrentHashMap<>();

    @Override
    public void afterConnectionEstablished(WebSocketSession session) throws Exception {
        String token = extractToken(session.getUri());
        if (token == null) {
            session.close(CloseStatus.BAD_DATA.withReason("token missing"));
            return;
        }

        OverlayConfigDto config;
        try {
            config = configService.findByToken(token);
        } catch (IllegalArgumentException e) {
            session.close(CloseStatus.NOT_ACCEPTABLE.withReason("overlay not found"));
            return;
        }

        String source = config.source().toLowerCase();        // dummy/chzzk/youtube
        String channelId = config.channelId() != null && !config.channelId().isBlank()
                ? config.channelId()
                : config.overlayToken();                       // dummy 일 때 fallback

        // CHZZK 인 경우 OAuth 토큰 필요
        String accessToken = null;
        String refreshToken = null;
        if ("chzzk".equals(source)) {
            Long ownerId = config.ownerUserId();
            if (ownerId == null) {
                session.close(CloseStatus.NOT_ACCEPTABLE.withReason("chzzk overlay missing owner"));
                return;
            }
            ChzzkToken chzzkToken = chzzkOAuthService.getValidToken(ownerId).orElse(null);
            if (chzzkToken == null) {
                session.close(CloseStatus.NOT_ACCEPTABLE.withReason("chzzk not connected"));
                return;
            }
            accessToken = chzzkToken.getAccessToken();
            refreshToken = chzzkToken.getRefreshToken();
        }

        // 메시지 수신 시 filter-service 호출 → 클라이언트로 push
        // token 을 클로저에 캡처해서 매 메시지마다 최신 config(B/W list 등) 를 다시 로드.
        final String capturedToken = token;
        Disposable subscription = chatFetcher.subscribe(source, channelId, accessToken, refreshToken, raw -> {
            handleIncomingMessage(session, capturedToken, raw);
        });

        sessions.put(session.getId(), new SessionContext(session, capturedToken, subscription));
        log.info("[WS] open — sessionId={} token={} source={} channel={}",
                session.getId(), token, source, channelId);
    }

    @Override
    public void afterConnectionClosed(WebSocketSession session, CloseStatus status) {
        SessionContext ctx = sessions.remove(session.getId());
        if (ctx != null && ctx.subscription != null) {
            ctx.subscription.dispose();
        }
        log.info("[WS] close — sessionId={} status={}", session.getId(), status);
    }

    /** chat-fetcher 메시지 처리 — filter 호출 후 클라이언트로 보냄.
     *
     * 매 호출마다 token 으로 최신 config 를 다시 조회해 B/W list / 보안수준 변경이
     * WS 재연결 없이 즉시 반영되도록 한다.
     */
    private void handleIncomingMessage(WebSocketSession session, String token, Map<String, Object> raw) {
        SessionContext ctx = sessions.get(session.getId());
        if (ctx == null || !session.isOpen()) return;

        // 매 메시지마다 최신 config — 설정 페이지 저장 후 즉시 반영됨
        OverlayConfigDto config;
        try {
            config = configService.findByToken(token);
        } catch (Exception e) {
            log.warn("[WS] config 재로드 실패: {}", e.getMessage());
            return;
        }

        String id = String.valueOf(raw.getOrDefault("id", ""));
        String author = String.valueOf(raw.getOrDefault("author", "Anonymous"));
        String content = String.valueOf(raw.getOrDefault("content", ""));
        long tsGenerated = ((Number) raw.getOrDefault("ts_received_ms", System.currentTimeMillis())).longValue();
        long tsFilterStart = System.currentTimeMillis();

        filterClient.analyze(new FilterAnalyzeRequest(
                content,
                config.securityLevel(),
                config.whitelist(),
                config.blacklist(),
                config.useAiFilter()))
                .map(filterResp -> {
                    long tsFilterEnd = System.currentTimeMillis();
                    return new OverlayChatMessage(
                            id, author,
                            filterResp.originalText(),
                            filterResp.maskedText(),
                            filterResp.action(),
                            filterResp.score(),
                            filterResp.detectedWords().stream()
                                    .map(d -> new OverlayChatMessage.DetectedWordOut(d.word(), d.type()))
                                    .toList(),
                            tsGenerated,
                            tsFilterStart,
                            tsFilterEnd,
                            System.currentTimeMillis()
                    );
                })
                .doOnSuccess(payload -> {
                    sendJson(session, payload);
                    // 로그인 사용자의 채팅이면 히스토리에 기록 (NORMAL/REVIEW 는 카운트만, 차단류는 본문도)
                    Long ownerId = config.ownerUserId();
                    if (ownerId != null && payload != null) {
                        try {
                            String detected = payload.detectedWords().stream()
                                    .map(d -> d.word() + "|" + d.type())
                                    .reduce((a, b) -> a + "," + b)
                                    .orElse(null);
                            historyService.record(
                                    ownerId,
                                    payload.id(),                 // msgId — dedup 용
                                    config.source(),
                                    config.channelId(),
                                    payload.author(),
                                    payload.originalText(),
                                    payload.maskedText(),
                                    payload.action(),
                                    payload.score(),
                                    detected
                            );
                        } catch (Exception e) {
                            log.warn("[WS] 히스토리 기록 실패: {}", e.getMessage());
                        }
                    }
                })
                .onErrorResume(e -> {
                    log.warn("[WS] filter 호출 실패: {}", e.getMessage());
                    return Mono.empty();
                })
                .subscribe();
    }

    private void sendJson(WebSocketSession session, Object payload) {
        try {
            String json = objectMapper.writeValueAsString(payload);
            synchronized (session) {
                if (session.isOpen()) {
                    session.sendMessage(new TextMessage(json));
                }
            }
        } catch (IOException e) {
            log.warn("[WS] 전송 실패: {}", e.getMessage());
        }
    }

    private static String extractToken(URI uri) {
        if (uri == null) return null;
        String path = uri.getPath();
        int idx = path.lastIndexOf('/');
        if (idx < 0 || idx == path.length() - 1) return null;
        return path.substring(idx + 1);
    }

    private record SessionContext(WebSocketSession session, String token, Disposable subscription) {}
}
