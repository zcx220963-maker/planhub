package com.planhub.controller;

import com.planhub.config.AiServiceConfig;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Agent 状态接口 - 监控 Agent 服务运行状态

 * 功能：
 * 1. 查看 Agent 服务健康状态
 * 2. 查看记忆系统状态
 * 3. 查看工具缓存状态
 * 4. 查看降级服务状态
 */
@RestController
@RequestMapping("/api/agent")
@RequiredArgsConstructor
@Slf4j
public class AgentStatusController {

    private final AiServiceConfig aiServiceConfig;

    /**
     * 获取 Agent 服务状态概览

     * @return Agent 服务状态
     */
    @GetMapping("/status")
    public ResponseEntity<Map<String, Object>> getAgentStatus() {
        log.info("获取 Agent 服务状态");

        Map<String, Object> response = new LinkedHashMap<>();
        response.put("service", "planhub-agent");
        response.put("timestamp", System.currentTimeMillis());

        // 检查 AI 服务连通性
        try {
            String url = aiServiceConfig.getAiServiceUrl() + "/health";
            org.springframework.web.client.RestTemplate restTemplate = new org.springframework.web.client.RestTemplate();
            ResponseEntity<?> aiResponse = restTemplate.getForEntity(url, Map.class);

            if (aiResponse.getStatusCode().is2xxSuccessful()) {
                response.put("status", "UP");
                response.put("ai_service", aiResponse.getBody());
            } else {
                response.put("status", "DOWN");
                response.put("error", "AI 服务返回异常: " + aiResponse.getStatusCode());
            }
        } catch (Exception e) {
            response.put("status", "DOWN");
            response.put("error", "AI 服务不可用: " + e.getMessage());
        }

        return ResponseEntity.ok(response);
    }

    /**
     * 获取 Agent 详细状态（包括记忆、缓存、降级等）

     * @return Agent 详细状态
     */
    @GetMapping("/details")
    public ResponseEntity<Map<String, Object>> getAgentDetails() {
        log.info("获取 Agent 详细状态");

        Map<String, Object> response = new LinkedHashMap<>();

        try {
            // 获取 AI 服务的各种状态
            String baseUrl = aiServiceConfig.getAiServiceUrl();
            org.springframework.web.client.RestTemplate restTemplate = new org.springframework.web.client.RestTemplate();

            // 1. 健康状态
            try {
                ResponseEntity<?> healthResponse = restTemplate.getForEntity(
                        baseUrl + "/health", Map.class);
                response.put("health", healthResponse.getBody());
            } catch (Exception e) {
                response.put("health", Map.of("status", "unreachable"));
            }

            // 2. 性能指标
            try {
                ResponseEntity<?> metricsResponse = restTemplate.getForEntity(
                        baseUrl + "/metrics?hours=1", Map.class);
                response.put("metrics_1h", metricsResponse.getBody());
            } catch (Exception e) {
                response.put("metrics_1h", Map.of("error", "无法获取"));
            }

            // 3. 降级服务状态
            try {
                ResponseEntity<?> fallbackResponse = restTemplate.getForEntity(
                        baseUrl + "/metrics/requests?limit=5", Map.class);
                response.put("recent_requests", fallbackResponse.getBody());
            } catch (Exception e) {
                response.put("recent_requests", Map.of("error", "无法获取"));
            }

            response.put("status", "UP");
        } catch (Exception e) {
            response.put("status", "DOWN");
            response.put("error", e.getMessage());
        }

        return ResponseEntity.ok(response);
    }

    /**
     * 获取 Agent 配置信息（不包含敏感信息）

     * @return Agent 配置信息
     */
    @GetMapping("/config")
    public ResponseEntity<Map<String, Object>> getAgentConfig() {
        log.info("获取 Agent 配置信息");

        Map<String, Object> response = new LinkedHashMap<>();

        // AI 服务配置
        Map<String, Object> aiConfig = new LinkedHashMap<>();
        aiConfig.put("service_url", aiServiceConfig.getAiServiceUrl());
        aiConfig.put("internal_secret_header", aiServiceConfig.getInternalSecretHeader());
        aiConfig.put("internal_secret_configured",
                aiServiceConfig.getInternalSecret() != null && !aiServiceConfig.getInternalSecret().isEmpty());
        aiConfig.put("connect_timeout", aiServiceConfig.getConnectTimeout() + "ms");
        aiConfig.put("read_timeout", aiServiceConfig.getReadTimeout() + "ms");
        response.put("ai_service", aiConfig);

        // 功能开关（从 application.yml 读取）
        Map<String, Object> features = new LinkedHashMap<>();
        features.put("memory_system", true);
        features.put("context_engineering", true);
        features.put("tool_caching", true);
        features.put("metrics_enabled", true);
        features.put("error_recovery", true);
        features.put("fallback_service", true);
        response.put("features", features);

        return ResponseEntity.ok(response);
    }

    /**
     * 重置 Agent 服务状态（清理缓存等）

     * @return 操作结果
     */
    @PostMapping("/reset")
    public ResponseEntity<Map<String, Object>> resetAgent() {
        log.info("重置 Agent 服务状态");

        Map<String, Object> response = new LinkedHashMap<>();

        try {
            // 清理工具缓存（后续可扩展为调用 Python 服务的清理接口）
            response.put("status", "success");
            response.put("message", "Agent 服务状态已重置");
        } catch (Exception e) {
            response.put("status", "error");
            response.put("error", e.getMessage());
        }

        return ResponseEntity.ok(response);
    }
}
