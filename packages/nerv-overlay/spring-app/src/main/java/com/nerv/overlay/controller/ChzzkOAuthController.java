package com.nerv.overlay.controller;

import com.nerv.overlay.entity.ChzzkToken;
import com.nerv.overlay.security.JwtAuthFilter.AuthPrincipal;
import com.nerv.overlay.service.ChzzkOAuthService;
import com.nerv.overlay.service.ProfileChzzkService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.net.URI;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.util.Map;
import java.util.Optional;

@Slf4j
@RestController
@RequestMapping("/api/oauth/chzzk")
@RequiredArgsConstructor
public class ChzzkOAuthController {

    private final ChzzkOAuthService service;
    private final ProfileChzzkService profileChzzkService;

    @Value("${app.frontend-base-url:http://localhost:5173}")
    private String frontendBaseUrl;

    /**
     * 인가 시작 — 로그인 사용자만 가능. CHZZK 로그인 페이지로 redirect.
     * SecurityConfig 가 보호하므로 토큰 없으면 403.
     */
    @GetMapping("/start")
    public ResponseEntity<Void> start(@AuthenticationPrincipal AuthPrincipal principal) {
        if (principal == null) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).build();
        }
        String url = service.startAuthUrl(principal.userId());
        return ResponseEntity.status(HttpStatus.FOUND).location(URI.create(url)).build();
    }

    /**
     * CHZZK → 우리 callback. 토큰 교환 + 채널 ID 자동 조회 + overlay_configs 갱신.
     * state 안에 userId 가 매핑돼있어 익명 GET 도 허용 (브라우저 redirect).
     */
    @GetMapping("/callback")
    public ResponseEntity<Void> callback(
            @RequestParam String code,
            @RequestParam String state
    ) {
        try {
            ChzzkOAuthService.ResolvedToken resolved = service.handleCallback(code, state);
            // 채널 ID 조회 + overlay 갱신은 ProfileChzzkService 에 위임
            profileChzzkService.applyConnectionAfterCallback(resolved.userId(), resolved.token().getAccessToken());
            return ResponseEntity.status(HttpStatus.FOUND)
                    .location(URI.create(frontendBaseUrl + "/profile?chzzk=connected"))
                    .build();
        } catch (Exception e) {
            log.warn("[ChzzkOAuth] callback 실패: {}", e.getMessage());
            String encoded = URLEncoder.encode(e.getMessage() == null ? "unknown" : e.getMessage(),
                    StandardCharsets.UTF_8);
            return ResponseEntity.status(HttpStatus.FOUND)
                    .location(URI.create(frontendBaseUrl + "/profile?chzzk=error&msg=" + encoded))
                    .build();
        }
    }

    /** 본인 토큰 상태 — 프론트 표시용. 비로그인 → connected:false */
    @GetMapping("/status")
    public Map<String, Object> status(@AuthenticationPrincipal AuthPrincipal principal) {
        if (principal == null) {
            return Map.of("connected", false);
        }
        Optional<ChzzkToken> token = service.getCurrentToken(principal.userId());
        if (token.isEmpty()) {
            return Map.of("connected", false);
        }
        ChzzkToken t = token.get();
        return Map.of(
                "connected", true,
                "expires_at", t.getExpiresAt().toString(),
                "expired", t.getExpiresAt().isBefore(LocalDateTime.now())
        );
    }
}
