package com.nerv.overlay.client;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;

import java.time.Duration;
import java.util.Map;

/**
 * chat-fetcher 의 /oauth/chzzk/* 엔드포인트 호출.
 * client_secret 을 chat-fetcher 만 갖고 있어 Spring 은 위임.
 */
@Slf4j
@Component
public class ChzzkOAuthClient {

    private final WebClient webClient;
    private final Duration timeout = Duration.ofSeconds(10);

    public ChzzkOAuthClient(@Value("${chat-fetcher.base-url}") String baseUrl) {
        this.webClient = WebClient.builder().baseUrl(baseUrl).build();
        log.info("[ChzzkOAuthClient] base-url = {}", baseUrl);
    }

    /** 인가 URL 발급 */
    public AuthUrlResponse getAuthUrl(String redirectUrl, String state) {
        return webClient.post()
                .uri("/oauth/chzzk/auth-url")
                .bodyValue(Map.of(
                        "redirect_url", redirectUrl,
                        "state", state == null ? "" : state
                ))
                .retrieve()
                .bodyToMono(AuthUrlResponse.class)
                .timeout(timeout)
                .block();
    }

    /** code → access_token 교환 */
    public TokenResponse exchange(String code, String state) {
        return webClient.post()
                .uri("/oauth/chzzk/exchange")
                .bodyValue(Map.of("code", code, "state", state))
                .retrieve()
                .bodyToMono(TokenResponse.class)
                .timeout(timeout)
                .block();
    }

    /** access_token 으로 본인 채널 정보 조회 */
    public MeResponse me(String accessToken) {
        return webClient.get()
                .uri(uri -> uri.path("/oauth/chzzk/me")
                        .queryParam("access_token", accessToken)
                        .build())
                .retrieve()
                .bodyToMono(MeResponse.class)
                .timeout(timeout)
                .block();
    }

    /** refresh_token 으로 access_token 갱신 */
    public Mono<TokenResponse> refresh(String refreshToken) {
        return webClient.post()
                .uri("/oauth/chzzk/refresh")
                .bodyValue(Map.of("refresh_token", refreshToken))
                .retrieve()
                .bodyToMono(TokenResponse.class)
                .timeout(timeout);
    }

    public record AuthUrlResponse(@JsonProperty("auth_url") String authUrl, String state) {}

    public record TokenResponse(
            @JsonProperty("access_token") String accessToken,
            @JsonProperty("refresh_token") String refreshToken,
            @JsonProperty("token_type") String tokenType,
            @JsonProperty("expires_in") int expiresIn
    ) {}

    public record MeResponse(
            @JsonProperty("channel_id") String channelId,
            @JsonProperty("channel_name") String channelName
    ) {}
}
