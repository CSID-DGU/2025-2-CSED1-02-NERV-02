package com.nerv.overlay.controller;

import com.nerv.overlay.dto.OverlayConfigDto;
import com.nerv.overlay.entity.ChzzkToken;
import com.nerv.overlay.security.JwtAuthFilter.AuthPrincipal;
import com.nerv.overlay.service.ChzzkOAuthService;
import com.nerv.overlay.service.ProfileChzzkService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.util.Map;
import java.util.Optional;

/**
 * 내정보 페이지 전용 — 채팅 소스 연동 상태/시작/해제.
 * SecurityConfig 가 /api/profile/** 를 인증 필요로 보호.
 */
@RestController
@RequestMapping("/api/profile")
@RequiredArgsConstructor
public class ProfileController {

    private final ChzzkOAuthService chzzkOAuthService;
    private final ProfileChzzkService profileChzzkService;

    /** 연동 상태 — 카드 표시용 */
    @GetMapping("/chzzk/status")
    public Map<String, Object> chzzkStatus(@AuthenticationPrincipal AuthPrincipal principal) {
        Optional<ChzzkToken> token = chzzkOAuthService.getCurrentToken(principal.userId());
        if (token.isEmpty()) {
            return Map.of("connected", false);
        }
        ChzzkToken t = token.get();
        return Map.of(
                "connected", true,
                "expires_at", t.getExpiresAt().toString()
        );
    }

    /**
     * 연동 시작 — 치지직 인가 URL 반환 (프론트가 새 창/리다이렉트로 이동).
     * Authorization 헤더로 본인 식별이 필요해서 /api/oauth/chzzk/start 가 아닌 별도 라우트로.
     */
    @PostMapping("/chzzk/start")
    public Map<String, String> startChzzk(@AuthenticationPrincipal AuthPrincipal principal) {
        String url = chzzkOAuthService.startAuthUrl(principal.userId());
        return Map.of("auth_url", url);
    }

    /** 해제 — 토큰 삭제 + overlay 를 더미로 되돌림 */
    @DeleteMapping("/chzzk")
    public ResponseEntity<OverlayConfigDto> disconnectChzzk(@AuthenticationPrincipal AuthPrincipal principal) {
        try {
            return ResponseEntity.ok(profileChzzkService.disconnect(principal.userId()));
        } catch (IllegalArgumentException e) {
            // overlay 가 없는 경우 — 그래도 토큰은 지웠으면 OK
            return ResponseEntity.status(HttpStatus.NO_CONTENT).build();
        }
    }
}
