package com.nerv.overlay.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;

/**
 * 클라이언트 OverlayPage 가 받는 채팅 메시지.
 * 측정을 위해 timestamp 가 풍부히 포함된다.
 */
public record OverlayChatMessage(
        String id,
        String author,

        @JsonProperty("original_text") String originalText,
        @JsonProperty("masked_text") String maskedText,
        String action,
        double score,
        @JsonProperty("detected_words") List<DetectedWordOut> detectedWords,

        // 측정용 timestamps (모두 epoch millis)
        @JsonProperty("ts_generated") long tsGenerated,
        @JsonProperty("ts_filter_start") long tsFilterStart,
        @JsonProperty("ts_filter_end") long tsFilterEnd,
        @JsonProperty("ts_sent") long tsSent
) {
    public record DetectedWordOut(String word, String type) {}
}
