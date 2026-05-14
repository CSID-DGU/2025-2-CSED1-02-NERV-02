package com.nerv.overlay.dto.auth;

public record AuthResponse(
        String token,
        UserDto user
) {}
