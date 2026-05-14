package com.nerv.overlay.config;

import com.nerv.overlay.websocket.OverlayWebSocketHandler;
import lombok.RequiredArgsConstructor;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.socket.config.annotation.EnableWebSocket;
import org.springframework.web.socket.config.annotation.WebSocketConfigurer;
import org.springframework.web.socket.config.annotation.WebSocketHandlerRegistry;

@Configuration
@EnableWebSocket
@RequiredArgsConstructor
public class WebSocketConfig implements WebSocketConfigurer {

    private final OverlayWebSocketHandler handler;

    @Override
    public void registerWebSocketHandlers(WebSocketHandlerRegistry registry) {
        // /ws/overlay/{token}
        registry.addHandler(handler, "/ws/overlay/*")
                .setAllowedOriginPatterns("*");  // 데모용. 운영에서는 도메인 화이트리스트.
    }
}
