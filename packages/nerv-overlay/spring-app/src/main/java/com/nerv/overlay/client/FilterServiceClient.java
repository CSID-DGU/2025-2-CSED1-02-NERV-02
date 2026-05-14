package com.nerv.overlay.client;

import com.nerv.overlay.dto.FilterAnalyzeRequest;
import com.nerv.overlay.dto.FilterAnalyzeResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;

import java.time.Duration;
import java.util.List;

/**
 * Python filter-service (FastAPI) 와의 HTTP 클라이언트.
 *
 * 내부 통신용이라 인증 없음. 같은 호스트/네트워크에서만 호출.
 */
@Slf4j
@Component
public class FilterServiceClient {

    private final WebClient webClient;
    private final Duration timeout;

    public FilterServiceClient(
            @Value("${filter-service.base-url}") String baseUrl,
            @Value("${filter-service.timeout-ms}") long timeoutMs
    ) {
        this.webClient = WebClient.builder()
                .baseUrl(baseUrl)
                .build();
        this.timeout = Duration.ofMillis(timeoutMs);
        log.info("[FilterServiceClient] base-url = {}", baseUrl);
    }

    /** 헬스 체크 — Python 서비스 살아있는지 */
    public Mono<Boolean> isHealthy() {
        return webClient.get()
                .uri("/health")
                .retrieve()
                .bodyToMono(Object.class)
                .map(body -> true)
                .timeout(timeout)
                .onErrorReturn(false);
    }

    /** 단일 텍스트 분석 */
    public Mono<FilterAnalyzeResponse> analyze(FilterAnalyzeRequest request) {
        return webClient.post()
                .uri("/analyze")
                .bodyValue(request)
                .retrieve()
                .bodyToMono(FilterAnalyzeResponse.class)
                .timeout(timeout);
    }

    /** 배치 분석 */
    public Mono<List<FilterAnalyzeResponse>> analyzeBatch(List<String> texts, String securityLevel) {
        return webClient.post()
                .uri("/analyze/batch")
                .bodyValue(new BatchRequestDto(texts, securityLevel))
                .retrieve()
                .bodyToFlux(FilterAnalyzeResponse.class)
                .collectList()
                .timeout(timeout);
    }

    private record BatchRequestDto(List<String> texts, String security_level) {}
}
