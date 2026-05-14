package com.nerv.overlay.service;

import com.nerv.overlay.client.ChzzkOAuthClient;
import com.nerv.overlay.entity.ChzzkToken;
import com.nerv.overlay.repository.ChzzkTokenRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
@RequiredArgsConstructor
public class ChzzkOAuthService {

    private final ChzzkOAuthClient client;
    private final ChzzkTokenRepository repository;

    @Value("${app.public-base-url}")
    private String publicBaseUrl;

    /** state → userId 매핑. callback 에서 어느 유저인지 식별. (5분 TTL) */
    private final ConcurrentHashMap<String, Long> pendingStates = new ConcurrentHashMap<>();
    private final ScheduledExecutorService scheduler = Executors.newSingleThreadScheduledExecutor(r -> {
        Thread t = new Thread(r, "chzzk-oauth-state-cleanup");
        t.setDaemon(true);
        return t;
    });

    /** 인가 URL 생성. state → userId 임시 저장. */
    public String startAuthUrl(Long userId) {
        String redirectUrl = publicBaseUrl + "/api/oauth/chzzk/callback";
        ChzzkOAuthClient.AuthUrlResponse resp = client.getAuthUrl(redirectUrl, null);
        pendingStates.put(resp.state(), userId);
        scheduler.schedule(() -> pendingStates.remove(resp.state()), 5, TimeUnit.MINUTES);
        log.info("[ChzzkOAuth] auth url 발급, userId={} state={}", userId, resp.state());
        return resp.authUrl();
    }

    /** code/state 받아 토큰 교환 후 해당 사용자에 저장. 반환: (token, userId) */
    @Transactional
    public ResolvedToken handleCallback(String code, String state) {
        Long userId = pendingStates.remove(state);
        if (userId == null) {
            throw new IllegalStateException("invalid or expired state: " + state);
        }
        ChzzkOAuthClient.TokenResponse tokens = client.exchange(code, state);
        ChzzkToken saved = saveToken(userId, tokens);
        return new ResolvedToken(saved, userId);
    }

    @Transactional
    public ChzzkToken saveToken(Long userId, ChzzkOAuthClient.TokenResponse tokens) {
        // 기존 토큰 있으면 갱신, 없으면 생성
        ChzzkToken entity = repository.findByUserId(userId).orElseGet(() ->
                ChzzkToken.builder().userId(userId).build());
        entity.setUserId(userId);
        entity.setAccessToken(tokens.accessToken());
        entity.setRefreshToken(tokens.refreshToken());
        entity.setExpiresAt(LocalDateTime.now().plusSeconds(tokens.expiresIn()));
        ChzzkToken saved = repository.save(entity);
        log.info("[ChzzkOAuth] 토큰 저장: userId={} expires_at={}", userId, saved.getExpiresAt());
        return saved;
    }

    @Transactional(readOnly = true)
    public Optional<ChzzkToken> getCurrentToken(Long userId) {
        return repository.findByUserId(userId);
    }

    /** 만료 임박이면 갱신, 아니면 그대로 반환. */
    @Transactional
    public Optional<ChzzkToken> getValidToken(Long userId) {
        Optional<ChzzkToken> tokenOpt = repository.findByUserId(userId);
        if (tokenOpt.isEmpty()) return Optional.empty();
        ChzzkToken token = tokenOpt.get();

        if (token.getExpiresAt().isBefore(LocalDateTime.now().plusMinutes(5))) {
            try {
                ChzzkOAuthClient.TokenResponse refreshed = client.refresh(token.getRefreshToken()).block();
                if (refreshed != null) {
                    token.setAccessToken(refreshed.accessToken());
                    token.setRefreshToken(refreshed.refreshToken());
                    token.setExpiresAt(LocalDateTime.now().plusSeconds(refreshed.expiresIn()));
                    log.info("[ChzzkOAuth] 토큰 갱신: userId={}", userId);
                }
            } catch (Exception e) {
                log.warn("[ChzzkOAuth] refresh 실패 userId={}: {}", userId, e.getMessage());
                return Optional.empty();
            }
        }
        return Optional.of(token);
    }

    @Transactional
    public void disconnect(Long userId) {
        repository.deleteByUserId(userId);
        log.info("[ChzzkOAuth] 연동 해제: userId={}", userId);
    }

    public record ResolvedToken(ChzzkToken token, Long userId) {}
}
