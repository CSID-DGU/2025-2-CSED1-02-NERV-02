package com.nerv.overlay.service;

import com.nerv.overlay.dto.auth.AuthResponse;
import com.nerv.overlay.dto.auth.LoginRequest;
import com.nerv.overlay.dto.auth.RegisterRequest;
import com.nerv.overlay.dto.auth.UserDto;
import com.nerv.overlay.entity.User;
import com.nerv.overlay.repository.UserRepository;
import com.nerv.overlay.security.JwtTokenProvider;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Slf4j
@Service
@RequiredArgsConstructor
public class AuthService {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtTokenProvider tokenProvider;

    @Transactional
    public AuthResponse register(RegisterRequest req) {
        String username = req.username().trim().toLowerCase();
        String nickname = req.nickname().trim();

        if (userRepository.existsByUsername(username)) {
            throw new IllegalArgumentException("이미 사용 중인 아이디입니다.");
        }

        User user = User.builder()
                .username(username)
                .nickname(nickname)
                .passwordHash(passwordEncoder.encode(req.password()))
                .build();
        User saved = userRepository.save(user);
        log.info("[Auth] 회원가입: id={} username={}", saved.getId(), saved.getUsername());

        String token = tokenProvider.createToken(saved.getId(), saved.getUsername());
        return new AuthResponse(token, UserDto.from(saved));
    }

    @Transactional(readOnly = true)
    public AuthResponse login(LoginRequest req) {
        String username = req.username().trim().toLowerCase();
        User user = userRepository.findByUsername(username)
                .orElseThrow(() -> new IllegalArgumentException("아이디 또는 비밀번호가 올바르지 않습니다."));

        if (!passwordEncoder.matches(req.password(), user.getPasswordHash())) {
            throw new IllegalArgumentException("아이디 또는 비밀번호가 올바르지 않습니다.");
        }

        String token = tokenProvider.createToken(user.getId(), user.getUsername());
        log.info("[Auth] 로그인: id={} username={}", user.getId(), user.getUsername());
        return new AuthResponse(token, UserDto.from(user));
    }

    @Transactional(readOnly = true)
    public UserDto findById(Long userId) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new IllegalArgumentException("사용자를 찾을 수 없습니다."));
        return UserDto.from(user);
    }
}
