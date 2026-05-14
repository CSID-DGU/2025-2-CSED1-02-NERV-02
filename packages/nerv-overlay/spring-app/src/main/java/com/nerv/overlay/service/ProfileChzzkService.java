package com.nerv.overlay.service;

import com.nerv.overlay.client.ChzzkOAuthClient;
import com.nerv.overlay.dto.OverlayConfigDto;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

@Slf4j
@Service
@RequiredArgsConstructor
public class ProfileChzzkService {

    private final ChzzkOAuthClient chzzkClient;
    private final OverlayConfigService overlayConfigService;
    private final ChzzkOAuthService chzzkOAuthService;

    /**
     * OAuth 콜백 직후 호출.
     * 1) /oauth/chzzk/me 로 채널 ID 조회
     * 2) 사용자 본인 overlay 의 source=CHZZK, channel_id 자동 세팅
     */
    public OverlayConfigDto applyConnectionAfterCallback(Long userId, String accessToken) {
        ChzzkOAuthClient.MeResponse me;
        try {
            me = chzzkClient.me(accessToken);
        } catch (Exception e) {
            log.error("[ProfileChzzk] 채널 ID 조회 실패 userId={}: {}", userId, e.getMessage());
            // 채널 조회 실패해도 토큰은 저장됐으니, 사용자가 수동 재시도하도록 예외만 로그
            throw new IllegalStateException("CHZZK 채널 정보 조회 실패: " + e.getMessage(), e);
        }
        log.info("[ProfileChzzk] 본인 채널 식별: userId={} channelId={} channelName={}",
                userId, me.channelId(), me.channelName());

        return overlayConfigService.applyChzzkConnection(userId, me.channelId());
    }

    /** 연동 해제 — 토큰 삭제 + overlay 를 더미로 되돌림. */
    public OverlayConfigDto disconnect(Long userId) {
        chzzkOAuthService.disconnect(userId);
        return overlayConfigService.removeChzzkConnection(userId);
    }
}
