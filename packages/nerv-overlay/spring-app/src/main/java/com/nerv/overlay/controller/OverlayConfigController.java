package com.nerv.overlay.controller;

import com.nerv.overlay.dto.OverlayConfigDto;
import com.nerv.overlay.dto.OverlayConfigRequest;
import com.nerv.overlay.security.JwtAuthFilter.AuthPrincipal;
import com.nerv.overlay.service.OverlayConfigService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/overlays")
@RequiredArgsConstructor
public class OverlayConfigController {

    private final OverlayConfigService service;

    /** 전체 목록 — 관리/디버깅용. 인증 추가 시 본인 것만 반환하도록 변경 */
    @GetMapping
    public List<OverlayConfigDto> list() {
        return service.findAll();
    }

    /** 활성 오버레이 — 로그인 사용자 본인 것 (없으면 자동 생성), 비로그인은 글로벌 더미. */
    @GetMapping("/active")
    public OverlayConfigDto active(@AuthenticationPrincipal AuthPrincipal principal) {
        Long userId = principal != null ? principal.userId() : null;
        return service.getOrCreateActive(userId);
    }

    /** 활성 오버레이 갱신 — 설정 페이지용 */
    @PatchMapping("/active")
    public OverlayConfigDto updateActive(
            @AuthenticationPrincipal AuthPrincipal principal,
            @Valid @RequestBody OverlayConfigRequest req
    ) {
        Long userId = principal != null ? principal.userId() : null;
        return service.updateActive(userId, req);
    }

    /** ID로 조회 */
    @GetMapping("/{id}")
    public OverlayConfigDto get(@PathVariable Long id) {
        return service.findById(id);
    }

    /** 토큰으로 조회 — OBS Browser Source 가 호출 */
    @GetMapping("/by-token/{token}")
    public OverlayConfigDto getByToken(@PathVariable String token) {
        return service.findByToken(token);
    }

    /** 생성 — 토큰 자동 발급. 로그인 사용자 소유로 귀속. */
    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public OverlayConfigDto create(
            @AuthenticationPrincipal AuthPrincipal principal,
            @Valid @RequestBody OverlayConfigRequest req
    ) {
        Long userId = principal != null ? principal.userId() : null;
        return service.create(userId, req);
    }

    /** 부분 갱신 — null 필드는 변경 안 함 */
    @PatchMapping("/{id}")
    public OverlayConfigDto update(@PathVariable Long id, @Valid @RequestBody OverlayConfigRequest req) {
        return service.update(id, req);
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(@PathVariable Long id) {
        service.delete(id);
        return ResponseEntity.noContent().build();
    }
}
