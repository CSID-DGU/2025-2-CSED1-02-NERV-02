package com.nerv.overlay.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.nerv.overlay.entity.OverlayConfig;

import java.time.LocalDateTime;
import java.util.List;

/**
 * 오버레이 설정 응답 DTO. Entity 노출 X.
 */
public record OverlayConfigDto(
        Long id,
        @JsonProperty("owner_user_id") Long ownerUserId,
        @JsonProperty("overlay_token") String overlayToken,
        @JsonProperty("overlay_url") String overlayUrl,
        String name,
        @JsonProperty("channel_id") String channelId,
        @JsonProperty("channel_name") String channelName,
        String source,
        @JsonProperty("security_level") String securityLevel,
        @JsonProperty("block_display_mode") String blockDisplayMode,
        @JsonProperty("placeholder_text") String placeholderText,
        @JsonProperty("show_score") boolean showScore,
        List<String> whitelist,
        List<String> blacklist,
        @JsonProperty("created_at") LocalDateTime createdAt,
        @JsonProperty("updated_at") LocalDateTime updatedAt
) {
    public static OverlayConfigDto from(OverlayConfig entity, String publicBaseUrl) {
        List<String> whitelist = entity.getDictionary().stream()
                .filter(d -> "WHITELIST".equals(d.getListType()))
                .map(d -> d.getWord())
                .toList();
        List<String> blacklist = entity.getDictionary().stream()
                .filter(d -> "BLACKLIST".equals(d.getListType()))
                .map(d -> d.getWord())
                .toList();

        return new OverlayConfigDto(
                entity.getId(),
                entity.getOwnerUserId(),
                entity.getOverlayToken(),
                publicBaseUrl + "/overlay/" + entity.getOverlayToken(),
                entity.getName(),
                entity.getChannelId(),
                entity.getChannelName(),
                entity.getSource(),
                entity.getSecurityLevel(),
                entity.getBlockDisplayMode(),
                entity.getPlaceholderText(),
                entity.getShowScore(),
                whitelist,
                blacklist,
                entity.getCreatedAt(),
                entity.getUpdatedAt()
        );
    }
}
