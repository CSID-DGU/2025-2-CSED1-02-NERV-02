package com.nerv.overlay.controller;

import com.nerv.overlay.dto.OverlayConfigDto;
import com.nerv.overlay.security.JwtAuthFilter.AuthPrincipal;
import com.nerv.overlay.service.OverlayConfigService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.reactive.function.client.WebClient;

import java.util.Map;

/**
 * 메인 페이지 채팅 입력 → 더미 채널에 메시지 1회 주입.
 * 사용자가 본인이 만든 텍스트의 필터링 결과를 즉시 볼 수 있게.
 */
@Slf4j
@RestController
@RequestMapping("/api/test")
@RequiredArgsConstructor
public class TestInjectController {

    private final OverlayConfigService configService;
    private final WebClient.Builder webClientBuilder;

    @Value("${chat-fetcher.base-url}")
    private String chatFetcherBaseUrl;

    public record InjectRequest(String content, String author) {}

    @PostMapping("/inject")
    public ResponseEntity<Map<String, Object>> inject(
            @AuthenticationPrincipal AuthPrincipal principal,
            @RequestBody InjectRequest req
    ) {
        Long userId = principal != null ? principal.userId() : null;
        OverlayConfigDto active = configService.getOrCreateActive(userId);
        // 더미 source 일 때만 주입 가능 (CHZZK 는 실 채팅 받으니 의미 X)
        if (!"DUMMY".equals(active.source())) {
            return ResponseEntity.badRequest().body(Map.of(
                    "error", "active overlay 가 DUMMY source 가 아닙니다. 설정에서 변경하세요.",
                    "current_source", active.source()
            ));
        }
        String channelId = active.channelId() != null && !active.channelId().isBlank()
                ? active.channelId()
                : active.overlayToken();

        WebClient client = webClientBuilder.baseUrl(chatFetcherBaseUrl).build();
        Map<?, ?> resp = client.post()
                .uri("/sources/dummy/{cid}/inject", channelId)
                .bodyValue(Map.of(
                        "content", req.content(),
                        "author", req.author() != null ? req.author() : "Tester"
                ))
                .retrieve()
                .bodyToMono(Map.class)
                .block();
        return ResponseEntity.ok(Map.of(
                "ok", true,
                "injected", resp != null && Boolean.TRUE.equals(resp.get("injected"))
        ));
    }
}
