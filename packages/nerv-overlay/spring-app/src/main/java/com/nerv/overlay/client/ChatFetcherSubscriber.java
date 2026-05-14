package com.nerv.overlay.client;

import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.socket.WebSocketHandler;
import org.springframework.web.reactive.socket.WebSocketMessage;
import org.springframework.web.reactive.socket.client.ReactorNettyWebSocketClient;
import org.springframework.web.reactive.socket.client.WebSocketClient;
import reactor.core.Disposable;
import reactor.core.publisher.Mono;

import java.net.URI;
import java.util.Map;
import java.util.function.Consumer;

/**
 * chat-fetcher 의 WebSocket 엔드포인트에 구독하는 클라이언트.
 *
 * 사용 패턴:
 *   Disposable sub = subscriber.subscribe("chzzk", "channel-id", message -> {
 *       // 메시지 도착 시 호출
 *   });
 *   // 종료 시
 *   sub.dispose();
 */
@Slf4j
@Component
public class ChatFetcherSubscriber {

    private final WebSocketClient client = new ReactorNettyWebSocketClient();
    private final ObjectMapper objectMapper;
    private final String wsBase;

    public ChatFetcherSubscriber(
            ObjectMapper objectMapper,
            @Value("${chat-fetcher.ws-url}") String wsBase
    ) {
        this.objectMapper = objectMapper;
        this.wsBase = wsBase.replaceAll("/+$", "");
        log.info("[ChatFetcherSubscriber] ws-url = {}", this.wsBase);
    }

    /** chat-fetcher 의 채널 메시지를 구독. 종료 시 반환된 Disposable 호출. */
    public Disposable subscribe(String source, String channelId, Consumer<Map<String, Object>> onMessage) {
        return subscribe(source, channelId, null, null, onMessage);
    }

    /** OAuth 토큰을 query param 으로 전달하는 변형 (CHZZK 등). */
    public Disposable subscribe(
            String source,
            String channelId,
            String accessToken,
            String refreshToken,
            Consumer<Map<String, Object>> onMessage
    ) {
        StringBuilder uriStr = new StringBuilder(wsBase)
                .append("/ws/").append(source).append("/").append(channelId);
        if (accessToken != null && !accessToken.isBlank()) {
            uriStr.append("?access_token=").append(accessToken);
            if (refreshToken != null && !refreshToken.isBlank()) {
                uriStr.append("&refresh_token=").append(refreshToken);
            }
        }
        URI uri = URI.create(uriStr.toString());
        log.info("[ChatFetcherSubscriber] connecting → {}/{} (token={})",
                source, channelId, accessToken != null ? "yes" : "no");

        WebSocketHandler handler = session ->
                session.receive()
                        .map(WebSocketMessage::getPayloadAsText)
                        .doOnNext(payload -> {
                            try {
                                @SuppressWarnings("unchecked")
                                Map<String, Object> msg = objectMapper.readValue(payload, Map.class);
                                onMessage.accept(msg);
                            } catch (Exception e) {
                                log.warn("[ChatFetcherSubscriber] parse 실패: {}", e.getMessage());
                            }
                        })
                        .then();

        return client.execute(uri, handler)
                .doOnError(e -> log.warn("[ChatFetcherSubscriber] WS 에러 ({}/{}): {}",
                        source, channelId, e.getMessage()))
                .onErrorResume(e -> Mono.empty())
                .subscribe();
    }
}
