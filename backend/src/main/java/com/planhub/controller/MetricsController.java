package com.planhub.controller;

import com.planhub.config.AiServiceConfig;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * 性能指标接口（简历项目加分点）。
 *
 * 设计原则：
 * 1. 从 Python AI 服务获取性能指标
 * 2. 提供系统运行状态监控
 * 3. 支持实时和历史数据查询
 */
@RestController
@RequestMapping("/api/metrics")
@RequiredArgsConstructor
@Slf4j
public class MetricsController {

    private final AiServiceConfig aiServiceConfig;

    /**
     * 获取性能指标统计
     *
     * @param hours 统计最近 N 小时，默认 24 小时
     * @return 性能指标
     */
    @GetMapping
    public ResponseEntity<Map<String, Object>> getMetrics(
            @RequestParam(defaultValue = "24") int hours) {
        log.info("获取性能指标，时间范围: {} 小时", hours);

        Map<String, Object> response = new LinkedHashMap<>();

        try {
            // 调用 Python AI 服务的指标接口
            String url = aiServiceConfig.getAiServiceUrl() + "/metrics?hours=" + hours;

            org.springframework.web.client.RestTemplate restTemplate = new org.springframework.web.client.RestTemplate();
            ResponseEntity<?> aiResponse = restTemplate.getForEntity(url, Map.class);

            if (aiResponse.getStatusCode().is2xxSuccessful()) {
                // 安全地转换为 Map<String, Object>
                Map<String, Object> body = new LinkedHashMap<>();
                Object responseBody = aiResponse.getBody();
                if (responseBody instanceof Map<?, ?>) {
                    Map<?, ?> mapBody = (Map<?, ?>) responseBody;
                    mapBody.forEach((k, v) -> {
                        if (k != null) {
                            body.put(String.valueOf(k), v);
                        }
                    });
                }
                response.putAll(body);
                response.put("source", "ai_service");
            } else {
                log.warn("AI 服务指标接口返回异常: {}", aiResponse.getStatusCode());
                response.put("error", "AI 服务不可用");
                response.put("source", "local");
            }
        } catch (Exception e) {
            log.error("获取性能指标失败: {}", e.getMessage());
            response.put("error", e.getMessage());
            response.put("source", "local");
        }

        // 添加本地系统指标
        response.put("system", getSystemMetrics());
        response.put("timestamp", System.currentTimeMillis());

        return ResponseEntity.ok(response);
    }

    /**
     * 获取最近的请求列表
     *
     * @param limit 返回数量，默认 10
     * @return 请求列表
     */
    @GetMapping("/requests")
    public ResponseEntity<Map<String, Object>> getRecentRequests(
            @RequestParam(defaultValue = "10") int limit) {
        log.info("获取最近请求，数量: {}", limit);

        Map<String, Object> response = new LinkedHashMap<>();

        try {
            String url = aiServiceConfig.getAiServiceUrl() + "/metrics/requests?limit=" + limit;

            org.springframework.web.client.RestTemplate restTemplate = new org.springframework.web.client.RestTemplate();
            ResponseEntity<?> aiResponse = restTemplate.getForEntity(url, Map.class);

            if (aiResponse.getStatusCode().is2xxSuccessful() && aiResponse.getBody() != null) {
                Object body = aiResponse.getBody();
                if (body instanceof Map<?, ?>) {
                    Object requests = ((Map<?, ?>) body).get("requests");
                    response.put("requests", requests != null ? requests : java.util.List.of());
                } else {
                    response.put("requests", java.util.List.of());
                }
            } else {
                response.put("requests", java.util.List.of());
            }
        } catch (Exception e) {
            log.error("获取最近请求失败: {}", e.getMessage());
            response.put("requests", java.util.Collections.emptyList());
            response.put("error", e.getMessage());
        }

        return ResponseEntity.ok(response);
    }

    /**
     * 获取慢请求列表
     *
     * @param threshold 耗时阈值（秒），默认 5 秒
     * @param hours     时间范围（小时），默认 24 小时
     * @return 慢请求列表
     */
    @GetMapping("/slow")
    public ResponseEntity<Map<String, Object>> getSlowRequests(
            @RequestParam(defaultValue = "5.0") double threshold,
            @RequestParam(defaultValue = "24") int hours) {
        log.info("获取慢请求，阈值: {}s, 时间范围: {} 小时", threshold, hours);

        Map<String, Object> response = new LinkedHashMap<>();

        try {
            String url = aiServiceConfig.getAiServiceUrl() + "/metrics/slow?threshold=" + threshold + "&hours=" + hours;

            org.springframework.web.client.RestTemplate restTemplate = new org.springframework.web.client.RestTemplate();
            ResponseEntity<?> aiResponse = restTemplate.getForEntity(url, Map.class);

            if (aiResponse.getStatusCode().is2xxSuccessful() && aiResponse.getBody() != null) {
                Object body = aiResponse.getBody();
                if (body instanceof Map<?, ?>) {
                    Object slowRequests = ((Map<?, ?>) body).get("slow_requests");
                    response.put("slow_requests", slowRequests != null ? slowRequests : java.util.List.of());
                } else {
                    response.put("slow_requests", java.util.List.of());
                }
            } else {
                response.put("slow_requests", java.util.List.of());
            }
        } catch (Exception e) {
            log.error("获取慢请求失败: {}", e.getMessage());
            response.put("slow_requests", java.util.List.of());
            response.put("error", e.getMessage());
        }

        return ResponseEntity.ok(response);
    }

    /**
     * 获取错误请求列表
     *
     * @param hours 时间范围（小时），默认 24 小时
     * @return 错误请求列表
     */
    @GetMapping("/errors")
    public ResponseEntity<Map<String, Object>> getErrorRequests(
            @RequestParam(defaultValue = "24") int hours) {
        log.info("获取错误请求，时间范围: {} 小时", hours);

        Map<String, Object> response = new LinkedHashMap<>();

        try {
            String url = aiServiceConfig.getAiServiceUrl() + "/metrics/errors?hours=" + hours;

            org.springframework.web.client.RestTemplate restTemplate = new org.springframework.web.client.RestTemplate();
            ResponseEntity<?> aiResponse = restTemplate.getForEntity(url, Map.class);

            if (aiResponse.getStatusCode().is2xxSuccessful() && aiResponse.getBody() != null) {
                Object body = aiResponse.getBody();
                if (body instanceof Map<?, ?>) {
                    Object errorRequests = ((Map<?, ?>) body).get("error_requests");
                    response.put("error_requests", errorRequests != null ? errorRequests : java.util.List.of());
                } else {
                    response.put("error_requests", java.util.List.of());
                }
            } else {
                response.put("error_requests", java.util.List.of());
            }
        } catch (Exception e) {
            log.error("获取错误请求失败: {}", e.getMessage());
            response.put("error_requests", java.util.List.of());
            response.put("error", e.getMessage());
        }

        return ResponseEntity.ok(response);
    }

    /**
     * 获取系统健康状态
     *
     * @return 健康状态
     */
    @GetMapping("/health")
    public ResponseEntity<Map<String, Object>> getHealth() {
        log.info("获取系统健康状态");

        Map<String, Object> response = new LinkedHashMap<>();
        response.put("status", "UP");
        response.put("service", "planhub-backend");
        response.put("timestamp", System.currentTimeMillis());

        // 检查 AI 服务连通性
        try {
            String url = aiServiceConfig.getAiServiceUrl() + "/health";
            org.springframework.web.client.RestTemplate restTemplate = new org.springframework.web.client.RestTemplate();
            ResponseEntity<?> aiResponse = restTemplate.getForEntity(url, Map.class);

            response.put("ai_service_reachable", aiResponse.getStatusCode().is2xxSuccessful());
            if (aiResponse.getBody() != null) {
                Object body = aiResponse.getBody();
                if (body instanceof Map<?, ?>) {
                    Object status = ((Map<?, ?>) body).get("status");
                    response.put("ai_service_status", status);
                }
            }
        } catch (Exception e) {
            log.warn("AI 服务健康检查失败: {}", e.getMessage());
            response.put("ai_service_reachable", false);
            response.put("ai_service_error", e.getMessage());
        }

        return ResponseEntity.ok(response);
    }

    /**
     * 获取本地系统指标
     */
    private Map<String, Object> getSystemMetrics() {
        Map<String, Object> metrics = new LinkedHashMap<>();

        // JVM 信息
        Runtime runtime = Runtime.getRuntime();
        metrics.put("jvm_total_memory", runtime.totalMemory() / (1024 * 1024) + " MB");
        metrics.put("jvm_free_memory", runtime.freeMemory() / (1024 * 1024) + " MB");
        metrics.put("jvm_used_memory", (runtime.totalMemory() - runtime.freeMemory()) / (1024 * 1024) + " MB");
        metrics.put("jvm_max_memory", runtime.maxMemory() / (1024 * 1024) + " MB");

        // CPU 信息
        metrics.put("available_processors", runtime.availableProcessors());

        // 系统信息
        metrics.put("java_version", System.getProperty("java.version"));
        metrics.put("os_name", System.getProperty("os.name"));
        metrics.put("os_version", System.getProperty("os.version"));

        return metrics;
    }
}
