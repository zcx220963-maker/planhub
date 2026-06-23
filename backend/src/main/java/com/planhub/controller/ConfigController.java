package com.planhub.controller;

import com.planhub.config.AiServiceConfig;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestTemplate;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * 系统配置只读接口（简历项目加分点）。
 *
 * 设计原则：
 * 1. 只返回"非敏感"信息（URL、开关、模型类型等）。
 * 2. 任何密钥（JWT Secret、AI 内部密钥、数据库密码）一律以 "***" 形式返回，
 *    只展示"是否已配置"的状态，不会泄漏真实值。
 * 3. 作为"配置中心前端页面"的数据源。
 */
@RestController
@RequestMapping("/api/config")
@RequiredArgsConstructor
@Slf4j
public class ConfigController {

    private final AiServiceConfig aiServiceConfig;

    // 直接注入 RestTemplate Bean（Bean name 为 aiRestTemplate）
    @Qualifier("aiRestTemplate")
    private final RestTemplate aiRestTemplate;

    // Spring 配置项（只读暴露，不包含密码）
    @Value("${spring.datasource.url:not-configured}")
    private String datasourceUrl;

    @Value("${spring.profiles.active:dev}")
    private String activeProfile;

    @Value("${server.port:8080}")
    private String serverPort;

    // JWT / AI 相关密钥仅展示"是否已配置"
    @Value("${jwt.secret:}")
    private String jwtSecret;

    // 特性开关配置
    @Value("${features.rag-enabled:true}")
    private boolean ragEnabled;

    @Value("${features.ai-assistant-enabled:true}")
    private boolean aiAssistantEnabled;

    @Value("${features.chat-bot-enabled:true}")
    private boolean chatBotEnabled;

    /**
     * 获取系统配置摘要（只读）。
     */
    @GetMapping
    public ResponseEntity<Map<String, Object>> getConfig() {
        log.info("获取系统配置 - ragEnabled={}, aiAssistantEnabled={}, chatBotEnabled={}", ragEnabled, aiAssistantEnabled, chatBotEnabled);
        Map<String, Object> response = new LinkedHashMap<>();

        // 1) 应用基本信息
        Map<String, Object> app = new LinkedHashMap<>();
        app.put("name", "planhub-backend");
        app.put("profile", activeProfile);
        app.put("port", serverPort);
        response.put("application", app);

        // 2) 数据库（只暴露 URL 类型，不写用户名密码）
        Map<String, Object> db = new LinkedHashMap<>();
        db.put("url_type", detectDbType(datasourceUrl));
        db.put("url_masked", maskUrl(datasourceUrl));
        response.put("database", db);

        // 3) AI 服务配置（不暴露密钥，只展示是否配置）
        Map<String, Object> ai = new LinkedHashMap<>();
        ai.put("service_url", aiServiceConfig.getAiServiceUrl());
        ai.put("internal_secret_configured",
                isNonEmpty(aiServiceConfig.getInternalSecret()) ? true : false);
        ai.put("internal_secret_header_name", aiServiceConfig.getInternalSecretHeader());
        response.put("ai_service", ai);

        // 4) 安全配置（只展示状态）
        Map<String, Object> security = new LinkedHashMap<>();
        security.put("jwt_secret_configured", isNonEmpty(jwtSecret));
        security.put("auth_mode", "JWT_BEARER_TOKEN");
        response.put("security", security);

        // 5) 特性开关（未来可扩展）
        Map<String, Object> features = new LinkedHashMap<>();
        features.put("rag_enabled", ragEnabled);
        features.put("ai_assistant_enabled", aiAssistantEnabled);
        features.put("chat_bot_enabled", chatBotEnabled);
        response.put("features", features);

        return ResponseEntity.ok(response);
    }

    /**
     * 简单健康检查。
     */
    @GetMapping("/health")
    public ResponseEntity<Map<String, Object>> health() {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("status", "UP");
        body.put("service", "planhub-backend");
        body.put("ai_service_reachable", testReachAiService());
        return ResponseEntity.ok(body);
    }

    // ─── 工具方法 ─────────────────────────────────────────────

    private boolean testReachAiService() {
        try {
            String url = aiServiceConfig.getAiServiceUrl() + "/health";
            org.springframework.http.HttpEntity<Void> entity =
                    new org.springframework.http.HttpEntity<>(buildHeaders());
            ResponseEntity<String> r = aiRestTemplate.exchange(
                    url, org.springframework.http.HttpMethod.GET, entity, String.class);
            return r.getStatusCode().is2xxSuccessful();
        } catch (Exception e) {
            log.debug("AI 服务健康检查失败: {}", e.getMessage());
            return false;
        }
    }

    private org.springframework.http.HttpHeaders buildHeaders() {
        org.springframework.http.HttpHeaders headers = new org.springframework.http.HttpHeaders();
        headers.set(aiServiceConfig.getInternalSecretHeader(), aiServiceConfig.getInternalSecret());
        return headers;
    }

    private static boolean isNonEmpty(String s) {
        return s != null && !s.isBlank();
    }

    private static String detectDbType(String url) {
        if (url == null) return "unknown";
        String u = url.toLowerCase();
        if (u.contains("mysql")) return "MySQL";
        if (u.contains("postgres")) return "PostgreSQL";
        if (u.contains("h2")) return "H2 (in-memory)";
        if (u.contains("sqlite")) return "SQLite";
        if (u.contains("oracle")) return "Oracle";
        return "unknown";
    }

    private static String maskUrl(String url) {
        if (url == null) return "not-configured";
        // 去掉可能的 username:password@ 部分
        int at = url.indexOf('@');
        if (at >= 0) {
            int scheme = url.indexOf("://");
            if (scheme >= 0 && scheme < at) {
                return url.substring(0, scheme + 3) + "***:***@" + url.substring(at + 1);
            }
        }
        return url;
    }
}
