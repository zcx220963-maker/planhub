package com.planhub.service;

import com.planhub.dto.request.LoginRequest;
import com.planhub.dto.request.RegisterRequest;
import com.planhub.dto.response.LoginResponse;

public interface AuthService {
    LoginResponse login(LoginRequest request);

    LoginResponse register(RegisterRequest request);

    LoginResponse refresh(String refreshToken);
}
