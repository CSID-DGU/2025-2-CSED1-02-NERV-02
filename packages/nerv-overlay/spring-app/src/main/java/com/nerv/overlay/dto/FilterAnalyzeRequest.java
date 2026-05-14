package com.nerv.overlay.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.NotBlank;

public record FilterAnalyzeRequest(
        @NotBlank String text,
        @JsonProperty("security_level") String securityLevel
) {
    public FilterAnalyzeRequest(String text) {
        this(text, "MEDIUM");
    }
}
