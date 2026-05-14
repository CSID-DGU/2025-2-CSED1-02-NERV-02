package com.nerv.overlay.controller;

import com.nerv.overlay.client.FilterServiceClient;
import com.nerv.overlay.dto.FilterAnalyzeRequest;
import com.nerv.overlay.dto.FilterAnalyzeResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import reactor.core.publisher.Mono;

import java.util.Map;

@RestController
@RequestMapping("/api")
@RequiredArgsConstructor
public class HealthController {

    private final FilterServiceClient filterClient;

    /** 자체 헬스 체크 */
    @GetMapping("/hello")
    public Map<String, String> hello() {
        return Map.of(
                "service", "nerv-overlay-spring",
                "status", "ok"
        );
    }

    /** filter-service 까지 포함한 헬스 체크 */
    @GetMapping("/health/full")
    public Mono<Map<String, Object>> fullHealth() {
        return filterClient.isHealthy()
                .map(filterUp -> Map.of(
                        "spring", "ok",
                        "filter-service", filterUp ? "ok" : "down"
                ));
    }

    /** filter-service 통합 검증용 — 텍스트 분석 위임 */
    @PostMapping("/filter/test")
    public Mono<FilterAnalyzeResponse> testFilter(@RequestBody FilterAnalyzeRequest request) {
        return filterClient.analyze(request);
    }
}
