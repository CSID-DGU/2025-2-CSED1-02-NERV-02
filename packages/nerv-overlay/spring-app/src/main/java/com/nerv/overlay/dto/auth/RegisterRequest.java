package com.nerv.overlay.dto.auth;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record RegisterRequest(
        @NotBlank @Size(min = 3, max = 40) String username,
        @NotBlank @Size(min = 1, max = 40) String nickname,
        @NotBlank @Size(min = 6, max = 100) String password
) {}
