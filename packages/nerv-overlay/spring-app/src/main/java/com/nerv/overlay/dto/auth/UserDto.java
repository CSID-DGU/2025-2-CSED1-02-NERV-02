package com.nerv.overlay.dto.auth;

import com.nerv.overlay.entity.User;

public record UserDto(
        Long id,
        String username,
        String nickname
) {
    public static UserDto from(User user) {
        return new UserDto(user.getId(), user.getUsername(), user.getNickname());
    }
}
