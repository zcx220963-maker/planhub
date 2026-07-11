package com.planhub.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.config.annotation.authentication.configuration.AuthenticationConfiguration;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;

import jakarta.annotation.PostConstruct;

@Configuration
@EnableWebSecurity
@EnableMethodSecurity
public class SecurityConfig {

    private final JwtAuthenticationFilter jwtAuthenticationFilter;

    public SecurityConfig(JwtAuthenticationFilter jwtAuthenticationFilter) {
        this.jwtAuthenticationFilter = jwtAuthenticationFilter;
    }

    /**
     * 关键：SSS 流式返回 Flux 时，Spring MVC 会切换线程写响应。
     * 默认 SecurityContextHolder 是 ThreadLocal，新线程拿不到认证信息，
     * SecurityContextHolderFilter 二次过滤时就返回 403。
     * 改为 InheritableThreadLocal 让异步线程也能拿到认证上下文。
     */
    @PostConstruct
    public void enableAsyncSecurityContext() {
        SecurityContextHolder.setStrategyName(SecurityContextHolder.MODE_INHERITABLETHREADLOCAL);
    }

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
            .cors(cors -> cors.configurationSource(request -> {
                var corsConfig = new org.springframework.web.cors.CorsConfiguration();
                corsConfig.addAllowedOriginPattern("*");
                corsConfig.addAllowedMethod(org.springframework.http.HttpMethod.GET);
                corsConfig.addAllowedMethod(org.springframework.http.HttpMethod.POST);
                corsConfig.addAllowedMethod(org.springframework.http.HttpMethod.PUT);
                corsConfig.addAllowedMethod(org.springframework.http.HttpMethod.DELETE);
                corsConfig.addAllowedMethod(org.springframework.http.HttpMethod.OPTIONS);
                corsConfig.addAllowedHeader("*");
                corsConfig.setAllowCredentials(true);
                corsConfig.setMaxAge(3600L);
                return corsConfig;
            }))
            .csrf(AbstractHttpConfigurer::disable)
            .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .authorizeHttpRequests(auth -> auth
                // 公开接口：认证相关
                .requestMatchers("/api/auth/login", "/api/auth/register", "/api/auth/refresh").permitAll()
                // 公开接口：用户注册/登录时的测试端点
                .requestMatchers("/api/auth/register/test").permitAll()

                // 用户接口：写操作需要认证， GET /page 公开（列表展示）
                .requestMatchers("/api/users/*/follow/**").authenticated()
                .requestMatchers("/api/users/*/change-password").authenticated()
                .requestMatchers("/api/users/*/avatar").authenticated()
                .requestMatchers("/api/users/*/privacy-settings").authenticated()
                .requestMatchers(org.springframework.http.HttpMethod.PUT, "/api/users/*").authenticated()
                .requestMatchers(org.springframework.http.HttpMethod.DELETE, "/api/users/*").authenticated()
                .requestMatchers("/api/users/**").permitAll()

                // 帖子/计划：写操作需要认证，读操作部分公开
                .requestMatchers(org.springframework.http.HttpMethod.POST, "/api/posts/**").authenticated()
                .requestMatchers(org.springframework.http.HttpMethod.PUT, "/api/posts/**").authenticated()
                .requestMatchers(org.springframework.http.HttpMethod.DELETE, "/api/posts/**").authenticated()
                .requestMatchers("/api/posts/**").permitAll()

                .requestMatchers(org.springframework.http.HttpMethod.POST, "/api/plans/**").authenticated()
                .requestMatchers(org.springframework.http.HttpMethod.PUT, "/api/plans/**").authenticated()
                .requestMatchers(org.springframework.http.HttpMethod.DELETE, "/api/plans/**").authenticated()
                .requestMatchers("/api/plans/**").permitAll()

                // 活动：需要认证
                .requestMatchers("/api/activities/**").authenticated()

                // 消息通知：需要认证
                .requestMatchers("/api/notifications/**").authenticated()

                // 搜索：公开（前端首页展示需要）
                .requestMatchers("/api/search/**").permitAll()
                // 但搜索同步话题需要认证（管理员功能）
                .requestMatchers("/api/search/sync-topics").authenticated()

                // 聊天：需要认证
                .requestMatchers("/api/chat/**").authenticated()

                // AI 健康检查：公开（不泄露敏感信息）—— 必须放在 /api/ai/** 之前！
                .requestMatchers("/api/ai/health", "/api/ai/orchestrator/health", "/api/ai/assistant/health").permitAll()

                // AI 服务：需要认证
                .requestMatchers("/api/ai/**").authenticated()

                // 文件上传：需要认证
                .requestMatchers("/api/upload/**").authenticated()

                // 静态上传文件：公开（用于展示图片）
                .requestMatchers("/uploads/**").permitAll()

                // 其余接口默认需要认证
                .anyRequest().authenticated()
            )
            .addFilterBefore(jwtAuthenticationFilter, UsernamePasswordAuthenticationFilter.class);
        
        return http.build();
    }

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }

    @Bean
    public AuthenticationManager authenticationManager(AuthenticationConfiguration config) throws Exception {
        return config.getAuthenticationManager();
    }
}
