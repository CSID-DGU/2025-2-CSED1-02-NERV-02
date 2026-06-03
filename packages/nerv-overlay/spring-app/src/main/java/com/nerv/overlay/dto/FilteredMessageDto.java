package com.nerv.overlay.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.nerv.overlay.entity.FilteredMessage;

import java.time.LocalDateTime;

public record FilteredMessageDto(
        Long id,
        String author,
        @JsonProperty("original_text") String originalText,
        @JsonProperty("masked_text") String maskedText,
        String action,
        Double score,
        @JsonProperty("detected_words") String detectedWords,
        @JsonProperty("selected_for_relearn") boolean selectedForRelearn,
        @JsonProperty("created_at") LocalDateTime createdAt
) {
    public static FilteredMessageDto from(FilteredMessage m) {
        return new FilteredMessageDto(
                m.getId(),
                m.getAuthor(),
                m.getOriginalText(),
                m.getMaskedText(),
                m.getAction(),
                m.getScore() != null ? m.getScore().doubleValue() : 0.0,
                m.getDetectedWords(),
                Boolean.TRUE.equals(m.getSelectedForRelearn()),
                m.getCreatedAt()
        );
    }
}
