package com.planhub.controller;

import com.planhub.dto.request.LoginRequest;
import com.planhub.dto.request.RegisterRequest;
import com.planhub.dto.response.ApiResponse;
import com.planhub.dto.response.LoginResponse;
import com.planhub.entity.User;
import com.planhub.service.AuthService;
import com.planhub.service.UserService;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/auth")
public class AuthController {
    private final AuthService authService;
    private final UserService userService;

    public AuthController(AuthService authService, UserService userService) {
        this.authService = authService;
        this.userService = userService;
    }

    @PostMapping("/login")
    public ResponseEntity<ApiResponse<LoginResponse>> login(@Valid @RequestBody LoginRequest request) {
        LoginResponse response = authService.login(request);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @PostMapping("/register")
    public ResponseEntity<ApiResponse<LoginResponse>> register(@Valid @RequestBody RegisterRequest request) {
        System.out.println("=== AuthController.register 被调用 ===");
        System.out.println("请求数据: " + request);
        LoginResponse response = authService.register(request);
        System.out.println("=== 注册成功 ===");
        return ResponseEntity.ok(ApiResponse.success(response, "注册成功"));
    }

    @PostMapping("/register/test")
    public ResponseEntity<String> registerTest(@RequestBody String data) {
        System.out.println("=== 测试端点被调用 ===");
        System.out.println("原始数据: " + data);
        return ResponseEntity.ok("测试成功");
    }

    @PostMapping("/refresh")
    public ResponseEntity<ApiResponse<LoginResponse>> refresh(@RequestHeader("Authorization") String token) {
        String refreshToken = token.replace("Bearer ", "");
        LoginResponse response = authService.refresh(refreshToken);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @GetMapping("/me")
    public ResponseEntity<ApiResponse<User>> getCurrentUser(Authentication authentication) {
        Long userId = (Long) authentication.getPrincipal();
        User user = userService.findById(userId);
        return ResponseEntity.ok(ApiResponse.success(user));
    }
}
