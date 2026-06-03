package com.nerv.overlay.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.nerv.overlay.entity.BroadcastSession;

import java.time.LocalDateTime;

public record BroadcastSessionDto(
        Long id,
        String source,
        @JsonProperty("channel_id") String channelId,
        @JsonProperty("started_at") LocalDateTime startedAt,
        @JsonProperty("last_message_at") LocalDateTime lastMessageAt,
        @JsonProperty("ended_at") LocalDateTime endedAt,
        @JsonProperty("message_count") Integer messageCount,
        @JsonProperty("filtered_count") Integer filteredCount,
        @JsonProperty("is_active") boolean isActive
) {
    public static BroadcastSessionDto from(BroadcastSession s) {
        return new BroadcastSessionDto(
                s.getId(),
                s.getSource(),
                s.getChannelId(),
                s.getStartedAt(),
                s.getLastMessageAt(),
                s.getEndedAt(),
                s.getMessageCount(),
                s.getFilteredCount(),
                s.getEndedAt() == null
        );
    }
}
