package com.planhub.service.impl;

import com.planhub.config.JwtUtil;
import com.planhub.dto.request.LoginRequest;
import com.planhub.dto.request.RegisterRequest;
import com.planhub.dto.response.LoginResponse;
import com.planhub.entity.User;
import com.planhub.exception.BusinessException;
import com.planhub.service.AuthService;
import com.planhub.service.UserService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

@Service
@RequiredArgsConstructor
@Slf4j
public class AuthServiceImpl implements AuthService {
    private final UserService userService;
    private final PasswordEncoder passwordEncoder;
    private final JwtUtil jwtUtil;

    @Override
    public LoginResponse login(LoginRequest request) {
        log.info("登录请求: username={}", request.getUsername());
        
        try {
            User user = userService.findByUsername(request.getUsername());
            log.info("找到用户: id={}, username={}, passwordHash={}", user.getId(), user.getUsername(), user.getPasswordHash());
            
            boolean matches = passwordEncoder.matches(request.getPassword(), user.getPasswordHash());
            log.info("密码匹配结果: {}", matches);
            
            if (!matches) {
                log.warn("密码不匹配");
                throw new BusinessException("用户名或密码错误");
            }

            String accessToken = jwtUtil.generateAccessToken(user.getId(), user.getUsername());
            String refreshToken = jwtUtil.generateRefreshToken(user.getId(), user.getUsername());
            log.info("生成token成功");

            return LoginResponse.builder()
                    .accessToken(accessToken)
                    .refreshToken(refreshToken)
                    .expiresIn(3600L)
                    .user(LoginResponse.UserResponse.builder()
                            .id(user.getId())
                            .username(user.getUsername())
                            .displayName(user.getDisplayName())
                            .avatarUrl(user.getAvatarUrl())
                            .build())
                    .build();
        } catch (Exception e) {
            log.error("登录失败: {}", e.getMessage(), e);
            throw e;
        }
    }

    @Override
    public LoginResponse register(RegisterRequest request) {
        User user = userService.register(request);
        
        String accessToken = jwtUtil.generateAccessToken(user.getId(), user.getUsername());
        String refreshToken = jwtUtil.generateRefreshToken(user.getId(), user.getUsername());

        return LoginResponse.builder()
                .accessToken(accessToken)
                .refreshToken(refreshToken)
                .expiresIn(3600L)
                .user(LoginResponse.UserResponse.builder()
                        .id(user.getId())
                        .username(user.getUsername())
                        .displayName(user.getDisplayName())
                        .avatarUrl(user.getAvatarUrl())
                        .build())
                .build();
    }

    @Override
    public LoginResponse refresh(String refreshToken) {
        if (!jwtUtil.validateToken(refreshToken)) {
            throw new BusinessException("无效的refresh token");
        }

        Long userId = jwtUtil.extractUserId(refreshToken);
        String username = jwtUtil.extractUsername(refreshToken);

        String newAccessToken = jwtUtil.generateAccessToken(userId, username);
        String newRefreshToken = jwtUtil.generateRefreshToken(userId, username);

        return LoginResponse.builder()
                .accessToken(newAccessToken)
                .refreshToken(newRefreshToken)
                .expiresIn(3600L)
                .user(LoginResponse.UserResponse.builder()
                        .id(userId)
                        .username(username)
                        .build())
                .build();
    }
}
