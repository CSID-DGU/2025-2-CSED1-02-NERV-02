package com.nerv.overlay.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;

/**
 * Python filter-service 응답 미러.
 * snake_case 필드명을 매핑.
 */
public record FilterAnalyzeResponse(
        @JsonProperty("original_text") String originalText,
        @JsonProperty("masked_text") String maskedText,
        String action,
        double score,
        @JsonProperty("detected_words") List<DetectedWord> detectedWords,
        Flags flags
) {
    public record DetectedWord(String word, String type) {}

    public record Flags(
            @JsonProperty("has_blacklist") boolean hasBlacklist,
            @JsonProperty("has_general") boolean hasGeneral,
            @JsonProperty("has_trigger") boolean hasTrigger
    ) {}
}
