package com.nerv.overlay.dto;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.NotBlank;

import java.util.List;

@JsonInclude(JsonInclude.Include.NON_NULL)
public record FilterAnalyzeRequest(
        @NotBlank String text,
        @JsonProperty("security_level") String securityLevel,
        List<String> whitelist,
        List<String> blacklist
) {
    public FilterAnalyzeRequest(String text) {
        this(text, "MEDIUM", null, null);
    }

    public FilterAnalyzeRequest(String text, String securityLevel) {
        this(text, securityLevel, null, null);
    }
}
