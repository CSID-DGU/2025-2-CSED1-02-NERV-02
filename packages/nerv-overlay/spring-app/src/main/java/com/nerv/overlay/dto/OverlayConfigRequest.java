package com.nerv.overlay.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

import java.util.List;

/**
 * 오버레이 설정 생성/수정 요청.
 * 모든 필드 optional. null 이면 기본값 사용.
 */
public record OverlayConfigRequest(
        @Size(max = 100) String name,

        @JsonProperty("channel_id")
        @Size(max = 100) String channelId,

        @Pattern(regexp = "DUMMY|CHZZK|YOUTUBE", message = "DUMMY/CHZZK/YOUTUBE 중 하나여야 합니다")
        String source,

        @JsonProperty("security_level")
        @Pattern(regexp = "LOW|MEDIUM|HIGH", message = "LOW/MEDIUM/HIGH 중 하나여야 합니다")
        String securityLevel,

        @JsonProperty("block_display_mode")
        @Pattern(regexp = "MASK|HIDE|PLACEHOLDER", message = "MASK/HIDE/PLACEHOLDER 중 하나여야 합니다")
        String blockDisplayMode,

        @JsonProperty("placeholder_text")
        @Size(max = 50) String placeholderText,

        @JsonProperty("show_score")
        Boolean showScore,

        List<@NotBlank @Size(max = 100) String> whitelist,
        List<@NotBlank @Size(max = 100) String> blacklist
) {}
