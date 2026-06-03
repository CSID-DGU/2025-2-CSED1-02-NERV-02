package com.nerv.overlay.controller;

import com.nerv.overlay.dto.BroadcastSessionDto;
import com.nerv.overlay.dto.FilteredMessageDto;
import com.nerv.overlay.security.JwtAuthFilter.AuthPrincipal;
import com.nerv.overlay.service.BroadcastHistoryService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * 방송 히스토리 API — 인증 필요. SecurityConfig 에서 /api/history/** 를 보호하도록 설정.
 */
@RestController
@RequestMapping("/api/history")
@RequiredArgsConstructor
public class HistoryController {

    private final BroadcastHistoryService historyService;

    /** 본인의 방송 세션 목록 (최신 시작순). */
    @GetMapping("/sessions")
    public List<BroadcastSessionDto> sessions(@AuthenticationPrincipal AuthPrincipal principal) {
        return historyService.listSessions(principal.userId()).stream()
                .map(BroadcastSessionDto::from)
                .toList();
    }

    /** 한 세션의 필터링된 메시지 목록. */
    @GetMapping("/sessions/{sessionId}/messages")
    public List<FilteredMessageDto> messages(
            @AuthenticationPrincipal AuthPrincipal principal,
            @PathVariable Long sessionId
    ) {
        return historyService.listMessages(principal.userId(), sessionId).stream()
                .map(FilteredMessageDto::from)
                .toList();
    }

    /** 메시지를 재학습 후보로 선택 (한 번 true 가 되면 영구 유지). */
    @PostMapping("/messages/{messageId}/select")
    public FilteredMessageDto select(
            @AuthenticationPrincipal AuthPrincipal principal,
            @PathVariable Long messageId
    ) {
        return FilteredMessageDto.from(historyService.markForRelearn(principal.userId(), messageId));
    }

    /**
     * 재학습 트리거 — 현재는 잠금 상태. UI 만 갖춰두고 실제 동작은 후속 작업.
     */
    @PostMapping("/relearn")
    public ResponseEntity<Map<String, Object>> relearn() {
        return ResponseEntity.status(HttpStatus.NOT_IMPLEMENTED)
                .body(Map.of(
                        "status", "locked",
                        "message", "재학습 기능은 아직 활성화되지 않았습니다."
                ));
    }
}
