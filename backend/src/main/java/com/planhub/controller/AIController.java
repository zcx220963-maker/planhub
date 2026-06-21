package com.planhub.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.planhub.config.AiServiceConfig;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.core.io.Resource;
import org.springframework.http.*;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContext;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.HttpServerErrorException;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.servlet.mvc.method.annotation.StreamingResponseBody;

import jakarta.servlet.http.HttpServletRequest;
import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.stream.Collectors;

/**
 * AI 服务转发控制器（安全网关）
 * 
 * 安全架构：
 * 1. 前端只调用 Java 后端的 /api/ai/** 端点
 * 2. Java 通过 Spring Security 验证用户的 JWT Token
 * 3. 验证通过后，Java 提取 user_id，转发请求到 Python AI 服务
 * 4. 转发时携带内部密钥 (X-Internal-Api-Secret)
 * 5. Python AI 服务只监听 127.0.0.1，只信任携带正确内部密钥的请求
 * 6. JWT 密钥永远不会出现在 Python 服务的配置中
 */
@RestController
@RequestMapping("/api/ai")
@RequiredArgsConstructor
@Slf4j
public class AIController {

    private final RestTemplate aiRestTemplate;
    private final AiServiceConfig aiServiceConfig;
    private final ObjectMapper objectMapper = new ObjectMapper();

    /**
     * 构建内部请求的 Header，包含用户的 JWT Authorization
     */
    private HttpHeaders buildInternalHeaders(String contentType, String jwtToken) {
        HttpHeaders headers = new HttpHeaders();
        headers.set(aiServiceConfig.getInternalSecretHeader(), aiServiceConfig.getInternalSecret());
        // 传递用户的 JWT token，使 Python 端的工具函数可以调用 Java 后端 API
        if (jwtToken != null && !jwtToken.isEmpty()) {
            headers.set("Authorization", "Bearer " + jwtToken);
            log.debug("传递 JWT Authorization Header 到 Python AI 服务");
        } else {
            log.warn("请求中没有 JWT token，Python AI 服务将无法调用需认证的 Java 后端 API");
        }
        if (contentType != null) {
            headers.setContentType(MediaType.parseMediaType(contentType));
        }
        return headers;
    }

    /**
     * 从 HttpServletRequest 中提取 JWT token
     */
    private String extractJwtToken(HttpServletRequest request) {
        if (request == null) return null;
        String bearerToken = request.getHeader("Authorization");
        if (bearerToken != null && bearerToken.startsWith("Bearer ")) {
            return bearerToken.substring(7);
        }
        return null;
    }

    /**
     * 从 Authentication 中获取用户 ID
     */
    private String getCurrentUserId(Authentication authentication) {
        if (authentication != null && authentication.getPrincipal() != null) {
            return String.valueOf(authentication.getPrincipal());
        }
        return "anonymous";
    }

    // ============ 通用转发方法 ============

    /**
     * 转发 JSON POST 请求
     */
    private ResponseEntity<Map<String, Object>> forwardJsonPost(
            String path,
            @RequestBody(required = false) Map<String, Object> body,
            Authentication authentication,
            HttpServletRequest request) {
        
        String url = aiServiceConfig.getAiServiceUrl() + path;
        String userId = getCurrentUserId(authentication);
        String jwtToken = extractJwtToken(request);
        
        // 确保请求体中包含 user_id
        if (body == null) {
            body = new HashMap<>();
        }
        body.putIfAbsent("user_id", userId);
        
        log.debug("转发 AI 请求: POST {} userId={}", url, userId);
        
        try {
            HttpHeaders headers = buildInternalHeaders(MediaType.APPLICATION_JSON_VALUE, jwtToken);
            HttpEntity<Map<String, Object>> entity = new HttpEntity<>(body, headers);
            
            @SuppressWarnings("unchecked")
            ResponseEntity<Map<String, Object>> response = (ResponseEntity<Map<String, Object>>) (ResponseEntity<?>) aiRestTemplate.postForEntity(url, entity, Map.class);

            // 保持原样返回
            return new ResponseEntity<>(response.getBody(), response.getStatusCode());
        } catch (HttpClientErrorException | HttpServerErrorException e) {
            log.error("AI 服务返回错误: {} - {}", e.getStatusCode(), e.getResponseBodyAsString());
            Map<String, Object> errorBody = new HashMap<>();
            errorBody.put("error", "AI service error: " + e.getStatusCode());
            errorBody.put("detail", e.getResponseBodyAsString());
            return new ResponseEntity<>(errorBody, e.getStatusCode());
        } catch (ResourceAccessException e) {
            log.error("无法连接到 AI 服务: {}", e.getMessage());
            Map<String, Object> errorBody = new HashMap<>();
            errorBody.put("error", "AI service unavailable");
            errorBody.put("detail", "请确认 Python AI 服务已启动");
            return new ResponseEntity<>(errorBody, HttpStatus.SERVICE_UNAVAILABLE);
        } catch (Exception e) {
            log.error("转发 AI 请求失败: {}", e.getMessage(), e);
            Map<String, Object> errorBody = new HashMap<>();
            errorBody.put("error", "Forward request failed");
            errorBody.put("detail", e.getMessage());
            return new ResponseEntity<>(errorBody, HttpStatus.INTERNAL_SERVER_ERROR);
        }
    }

    /**
     * 转发 GET 请求
     */
    private ResponseEntity<Map<String, Object>> forwardGet(String path, Authentication authentication, HttpServletRequest request) {
        String userId = getCurrentUserId(authentication);
        String url = aiServiceConfig.getAiServiceUrl() + path;
        // 将 user_id 作为 query param 传递给 Python（Python 端从 query param 读取）
        if (url.contains("?")) {
            url += "&user_id=" + userId;
        } else {
            url += "?user_id=" + userId;
        }
        String jwtToken = extractJwtToken(request);
        log.debug("转发 AI 请求: GET {}, userId={}", url, userId);

        try {
            HttpHeaders headers = buildInternalHeaders(null, jwtToken);
            HttpEntity<String> entity = new HttpEntity<>(headers);

            @SuppressWarnings({"unchecked", "rawtypes"})
            ResponseEntity<Map<String, Object>> response = (ResponseEntity<Map<String, Object>>) (ResponseEntity<?>) aiRestTemplate.exchange(
                url, HttpMethod.GET, entity, Map.class);

            return new ResponseEntity<>(response.getBody(), response.getStatusCode());
        } catch (HttpClientErrorException | HttpServerErrorException e) {
            log.error("AI 服务返回错误: {} - {}", e.getStatusCode(), e.getResponseBodyAsString());
            Map<String, Object> errorBody = new HashMap<>();
            errorBody.put("error", "AI service error: " + e.getStatusCode());
            errorBody.put("detail", e.getResponseBodyAsString());
            return new ResponseEntity<>(errorBody, e.getStatusCode());
        } catch (ResourceAccessException e) {
            log.error("无法连接到 AI 服务: {}", e.getMessage());
            Map<String, Object> errorBody = new HashMap<>();
            errorBody.put("error", "AI service unavailable");
            errorBody.put("detail", "请确认 Python AI 服务已启动");
            return new ResponseEntity<>(errorBody, HttpStatus.SERVICE_UNAVAILABLE);
        } catch (Exception e) {
            log.error("转发 AI 请求失败: {}", e.getMessage(), e);
            Map<String, Object> errorBody = new HashMap<>();
            errorBody.put("error", "Forward request failed");
            errorBody.put("detail", e.getMessage());
            return new ResponseEntity<>(errorBody, HttpStatus.INTERNAL_SERVER_ERROR);
        }
    }

    /**
     * 转发 DELETE 请求
     */
    private ResponseEntity<Map<String, Object>> forwardDelete(String path, Authentication authentication, HttpServletRequest request) {
        String userId = getCurrentUserId(authentication);
        String url = aiServiceConfig.getAiServiceUrl() + path;
        // 将 user_id 作为 query param 传递给 Python（Python 端从 query param 读取）
        if (url.contains("?")) {
            url += "&user_id=" + userId;
        } else {
            url += "?user_id=" + userId;
        }
        String jwtToken = extractJwtToken(request);
        log.debug("转发 AI 请求: DELETE {}, userId={}", url, userId);

        try {
            HttpHeaders headers = buildInternalHeaders(null, jwtToken);
            HttpEntity<String> entity = new HttpEntity<>(headers);

            @SuppressWarnings("unchecked")
            ResponseEntity<Map> response = aiRestTemplate.exchange(
                url, HttpMethod.DELETE, entity, Map.class);
            
            return new ResponseEntity<>(response.getBody(), response.getStatusCode());
        } catch (HttpClientErrorException | HttpServerErrorException e) {
            log.error("AI 服务返回错误: {} - {}", e.getStatusCode(), e.getResponseBodyAsString());
            Map<String, Object> errorBody = new HashMap<>();
            errorBody.put("error", "AI service error: " + e.getStatusCode());
            errorBody.put("detail", e.getResponseBodyAsString());
            return new ResponseEntity<>(errorBody, e.getStatusCode());
        } catch (ResourceAccessException e) {
            log.error("无法连接到 AI 服务: {}", e.getMessage());
            Map<String, Object> errorBody = new HashMap<>();
            errorBody.put("error", "AI service unavailable");
            errorBody.put("detail", "请确认 Python AI 服务已启动");
            return new ResponseEntity<>(errorBody, HttpStatus.SERVICE_UNAVAILABLE);
        } catch (Exception e) {
            log.error("转发 AI 请求失败: {}", e.getMessage(), e);
            Map<String, Object> errorBody = new HashMap<>();
            errorBody.put("error", "Forward request failed");
            errorBody.put("detail", e.getMessage());
            return new ResponseEntity<>(errorBody, HttpStatus.INTERNAL_SERVER_ERROR);
        }
    }

    // ============ 对话机器人 (Chat) ============

    @PostMapping("/chat/stream")
    public ResponseEntity<StreamingResponseBody> chatStream(
            @RequestBody Map<String, Object> body,
            Authentication authentication,
            HttpServletRequest request) {

        String url = aiServiceConfig.getAiServiceUrl() + "/chat/stream";
        String userId = getCurrentUserId(authentication);
        String jwtToken = extractJwtToken(request);
        body.putIfAbsent("user_id", userId);
        String jsonBody;
        try {
            jsonBody = objectMapper.writeValueAsString(body);
        } catch (Exception e) {
            log.error("JSON 序列化失败: {}", e.getMessage());
            return buildSseError("抱歉，请求参数处理失败，请稍后重试。");
        }

        log.debug("转发流式对话: userId={}", userId);

        // 捕获当前 SecurityContext（ThreadLocal），在异步线程中显式恢复，
        // 否则 Spring Security 的异步分发检查会抛出 AccessDeniedException
        SecurityContext capturedContext = SecurityContextHolder.getContext();
        String secretHeader = aiServiceConfig.getInternalSecretHeader();
        String secretValue = aiServiceConfig.getInternalSecret();

        StreamingResponseBody stream = outputStream -> {
            // 关键：在异步线程显式恢复 SecurityContext
            if (capturedContext != null) {
                SecurityContextHolder.setContext(capturedContext);
            }

            HttpURLConnection conn = null;
            try {
                java.net.URL targetUrl = new java.net.URL(url);
                conn = (HttpURLConnection) targetUrl.openConnection();
                conn.setRequestMethod("POST");
                conn.setDoOutput(true);
                conn.setDoInput(true);
                conn.setConnectTimeout(5000);
                conn.setReadTimeout(300000);
                conn.setUseCaches(false);

                // 设置请求头 - 带内部密钥
                conn.setRequestProperty("Content-Type", "application/json");
                conn.setRequestProperty(secretHeader, secretValue);
                if (jwtToken != null && !jwtToken.isEmpty()) {
                    conn.setRequestProperty("Authorization", "Bearer " + jwtToken);
                }

                // 发送请求体
                try (java.io.OutputStream os = conn.getOutputStream()) {
                    os.write(jsonBody.getBytes(StandardCharsets.UTF_8));
                    os.flush();
                }

                // 检查响应状态
                int status = conn.getResponseCode();
                log.debug("Python AI 服务响应状态: {}", status);

                // 选择输入流（200-299 用 getInputStream，否则 getErrorStream）
                InputStream is = (status >= 200 && status < 300) ? conn.getInputStream() : conn.getErrorStream();
                if (is == null) {
                    log.error("Python AI 服务无响应流，status={}", status);
                    writeSseMessage(outputStream, "抱歉，AI 服务无响应，请稍后重试。");
                    return;
                }

                // 真正的逐行 SSE 转发
                try (InputStreamReader isr = new InputStreamReader(is, StandardCharsets.UTF_8);
                     BufferedReader br = new BufferedReader(isr)) {

                    String line;
                    boolean gotAnyData = false;
                    while ((line = br.readLine()) != null) {
                        if (line.startsWith("data:")) {
                            gotAnyData = true;
                            outputStream.write((line + "\n\n").getBytes(StandardCharsets.UTF_8));
                            outputStream.flush();
                        }
                    }

                    if (!gotAnyData) {
                        log.warn("Python AI 服务未返回任何 SSE data 行");
                        writeSseMessage(outputStream, "AI 服务未返回有效内容，请稍后重试。");
                    }
                }

            } catch (java.net.ConnectException ce) {
                log.error("无法连接到 Python AI 服务({}): {}", url, ce.getMessage());
                writeSseMessage(outputStream, "抱歉，AI 服务未启动，请联系管理员。");
            } catch (java.net.SocketTimeoutException te) {
                log.error("连接 Python AI 服务超时: {}", te.getMessage());
                writeSseMessage(outputStream, "抱歉，AI 服务响应超时，请稍后重试。");
            } catch (Exception e) {
                log.error("SSE 流转发异常: {}", e.getMessage(), e);
                writeSseMessage(outputStream, "抱歉，发生了错误，请稍后重试。");
            } finally {
                // 清理异步线程的 SecurityContext（避免内存泄漏）
                SecurityContextHolder.clearContext();
                if (conn != null) {
                    try {
                        conn.disconnect();
                    } catch (Exception ignored) {
                    }
                }
            }
        };

        HttpHeaders responseHeaders = new HttpHeaders();
        responseHeaders.setContentType(MediaType.TEXT_EVENT_STREAM);
        responseHeaders.setCacheControl(CacheControl.noCache());
        responseHeaders.setConnection("keep-alive");
        responseHeaders.set("X-Accel-Buffering", "no");

        return new ResponseEntity<>(stream, responseHeaders, HttpStatus.OK);
    }

    // ---- SSE 工具方法 ----
    private ResponseEntity<StreamingResponseBody> buildSseError(String message) {
        StreamingResponseBody errorStream = outputStream -> writeSseMessage(outputStream, message);
        HttpHeaders responseHeaders = new HttpHeaders();
        responseHeaders.setContentType(MediaType.TEXT_EVENT_STREAM);
        responseHeaders.setCacheControl(CacheControl.noCache());
        return new ResponseEntity<>(errorStream, responseHeaders, HttpStatus.OK);
    }

    private void writeSseMessage(java.io.OutputStream outputStream, String content) throws java.io.IOException {
        String data = "data: {\"content\": \"" + content + "\", \"done\": true}\n\ndata: [DONE]\n\n";
        outputStream.write(data.getBytes(StandardCharsets.UTF_8));
        outputStream.flush();
    }

    @PostMapping("/chat/chat")
    public ResponseEntity<Map<String, Object>> chatNonStream(
            @RequestBody Map<String, Object> body,
            Authentication authentication,
            HttpServletRequest request) {
        return forwardJsonPost("/chat/chat", body, authentication, request);
    }

    @PostMapping("/chat")
    public ResponseEntity<Map<String, Object>> chatSimple(
            @RequestBody Map<String, Object> body,
            Authentication authentication,
            HttpServletRequest request) {
        return forwardJsonPost("/chat", body, authentication, request);
    }

    @GetMapping("/chat/history/{sessionId}")
    public ResponseEntity<Map<String, Object>> getChatHistory(
            @PathVariable String sessionId,
            Authentication authentication,
            HttpServletRequest request) {
        return forwardGet("/chat/history/" + sessionId, authentication, request);
    }

    // ============ 计划生成 (Plan Generator) ============

    @PostMapping("/chat/plan")
    public ResponseEntity<Map<String, Object>> chatPlan(
            @RequestBody Map<String, Object> body,
            Authentication authentication,
            HttpServletRequest request) {
        return forwardJsonPost("/chat/plan", body, authentication, request);
    }

    // ============ 智能社区助手 (Assistant) ============

    @PostMapping("/assistant/execute")
    public ResponseEntity<Map<String, Object>> executeAssistant(
            @RequestBody Map<String, Object> body,
            Authentication authentication,
            HttpServletRequest request) {
        return forwardJsonPost("/assistant/execute", body, authentication, request);
    }

    @PostMapping("/assistant")
    public ResponseEntity<Map<String, Object>> assistantSimple(
            @RequestBody Map<String, Object> body,
            Authentication authentication,
            HttpServletRequest request) {
        return forwardJsonPost("/assistant", body, authentication, request);
    }

    @GetMapping("/assistant/history/{sessionId}")
    public ResponseEntity<Map<String, Object>> getAssistantHistory(
            @PathVariable String sessionId,
            Authentication authentication,
            HttpServletRequest request) {
        return forwardGet("/assistant/history/" + sessionId, authentication, request);
    }

    @GetMapping("/assistant/health")
    public ResponseEntity<Map<String, Object>> assistantHealth(HttpServletRequest request) {
        return forwardGet("/assistant/health", null, request);
    }

    // ============ RAG 知识库 ============

    @PostMapping("/rag/query")
    public ResponseEntity<Map<String, Object>> ragQuery(
            @RequestBody Map<String, Object> body,
            Authentication authentication,
            HttpServletRequest request) {
        return forwardJsonPost("/rag/query", body, authentication, request);
    }

    @PostMapping("/rag/upload")
    public ResponseEntity<Map<String, Object>> ragUpload(
            @RequestParam("file") MultipartFile file,
            Authentication authentication,
            HttpServletRequest request) {
        
        String url = aiServiceConfig.getAiServiceUrl() + "/rag/upload";
        String userId = getCurrentUserId(authentication);
        String jwtToken = extractJwtToken(request);
        
        log.debug("上传文档到知识库: fileName={}, userId={}", file.getOriginalFilename(), userId);
        
        try {
            HttpHeaders headers = buildInternalHeaders(MediaType.MULTIPART_FORM_DATA_VALUE, jwtToken);
            
            // 构建 multipart 请求体
            MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
            
            // 处理文件上传
            final byte[] fileBytes = file.getBytes();
            final String fileName = file.getOriginalFilename() != null ? file.getOriginalFilename() : "document";
            final String fileContentType = file.getContentType() != null ? file.getContentType() : "application/octet-stream";
            
            body.add("file", new org.springframework.http.HttpEntity<>(fileBytes, new HttpHeaders() {{
                setContentType(MediaType.parseMediaType(fileContentType));
                setContentDispositionFormData("file", fileName);
            }}));

            // 传递 user_id 给 Python（Python 端从 Form 参数读取）
            body.add("user_id", userId);

            ResponseEntity<Map> response = aiRestTemplate.postForEntity(url, new HttpEntity<>(body, headers), Map.class);
            return new ResponseEntity<>(response.getBody(), response.getStatusCode());
        } catch (Exception e) {
            log.error("上传文档失败: {}", e.getMessage(), e);
            Map<String, Object> errorBody = new HashMap<>();
            errorBody.put("error", "Upload failed");
            errorBody.put("detail", e.getMessage());
            return new ResponseEntity<>(errorBody, HttpStatus.INTERNAL_SERVER_ERROR);
        }
    }

    @PostMapping("/rag/upload/batch")
    public ResponseEntity<Map<String, Object>> ragUploadBatch(
            @RequestParam("files") MultipartFile[] files,
            Authentication authentication,
            HttpServletRequest request) {
        
        String url = aiServiceConfig.getAiServiceUrl() + "/rag/upload/batch";
        String userId = getCurrentUserId(authentication);
        String jwtToken = extractJwtToken(request);
        
        log.debug("批量上传文档到知识库: fileCount={}, userId={}", files.length, userId);
        
        try {
            HttpHeaders headers = buildInternalHeaders(MediaType.MULTIPART_FORM_DATA_VALUE, jwtToken);
            
            // 构建 multipart 请求体
            MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
            
            // 处理多个文件上传
            for (int i = 0; i < files.length; i++) {
                MultipartFile file = files[i];
                final byte[] fileBytes = file.getBytes();
                final String fileName = file.getOriginalFilename() != null ? file.getOriginalFilename() : "document_" + i;
                final String fileContentType = file.getContentType() != null ? file.getContentType() : "application/octet-stream";
                
                body.add("files", new org.springframework.http.HttpEntity<>(fileBytes, new HttpHeaders() {{
                    setContentType(MediaType.parseMediaType(fileContentType));
                    setContentDispositionFormData("files", fileName);
                }}));
            }

            // 传递 user_id 给 Python（Python 端从 Form 参数读取）
            body.add("user_id", userId);

            HttpEntity<MultiValueMap<String, Object>> entity = new HttpEntity<>(body, headers);

            @SuppressWarnings("unchecked")
            ResponseEntity<Map> response = aiRestTemplate.postForEntity(url, entity, Map.class);

            return new ResponseEntity<>(response.getBody(), response.getStatusCode());
        } catch (HttpClientErrorException | HttpServerErrorException e) {
            log.error("AI 服务返回错误: {} - {}", e.getStatusCode(), e.getResponseBodyAsString());
            Map<String, Object> errorBody = new HashMap<>();
            errorBody.put("success", false);
            errorBody.put("message", "上传失败: " + e.getResponseBodyAsString());
            return new ResponseEntity<>(errorBody, e.getStatusCode());
        } catch (Exception e) {
            log.error("上传文档失败: {}", e.getMessage(), e);
            Map<String, Object> errorBody = new HashMap<>();
            errorBody.put("success", false);
            errorBody.put("message", "上传失败: " + e.getMessage());
            return new ResponseEntity<>(errorBody, HttpStatus.INTERNAL_SERVER_ERROR);
        }
    }

    @GetMapping("/rag/documents")
    public ResponseEntity<Map<String, Object>> ragGetDocuments(
            Authentication authentication,
            HttpServletRequest request) {
        return forwardGet("/rag/documents", authentication, request);
    }

    @DeleteMapping("/rag/documents/{docId}")
    public ResponseEntity<Map<String, Object>> ragDeleteDocument(
            @PathVariable String docId,
            Authentication authentication,
            HttpServletRequest request) {
        return forwardDelete("/rag/documents/" + docId, authentication, request);
    }

    @DeleteMapping("/rag/clear")
    public ResponseEntity<Map<String, Object>> ragClear(
            Authentication authentication,
            HttpServletRequest request) {
        return forwardDelete("/rag/clear", authentication, request);
    }

    @GetMapping("/rag/stats")
    public ResponseEntity<Map<String, Object>> ragStats(
            Authentication authentication,
            HttpServletRequest request) {
        return forwardGet("/rag/stats", authentication, request);
    }

    @GetMapping("/rag/document/{docId}")
    public ResponseEntity<Map<String, Object>> ragGetDocument(
            @PathVariable String docId,
            Authentication authentication,
            HttpServletRequest request) {
        return forwardGet("/rag/document/" + docId, authentication, request);
    }

    @PostMapping("/rag/reindex")
    public ResponseEntity<Map<String, Object>> ragReindex(
            Authentication authentication,
            HttpServletRequest request) {
        return forwardJsonPost("/rag/reindex", new HashMap<>(), authentication, request);
    }

    @PostMapping("/rag/load-directory")
    public ResponseEntity<Map<String, Object>> ragLoadDirectory(
            @RequestParam String directoryPath,
            Authentication authentication,
            HttpServletRequest request) {
        Map<String, Object> body = new HashMap<>();
        body.put("directory_path", directoryPath);
        return forwardJsonPost("/rag/load-directory", body, authentication, request);
    }

    // ============ LangGraph 智能编排 (Orchestrator) ============

    @PostMapping("/orchestrator/chat")
    public ResponseEntity<Map<String, Object>> orchestrateChat(
            @RequestBody Map<String, Object> body,
            Authentication authentication,
            HttpServletRequest request) {
        return forwardJsonPost("/orchestrator/chat", body, authentication, request);
    }

    @PostMapping("/orchestrator/stream")
    public ResponseEntity<StreamingResponseBody> orchestrateStream(
            @RequestBody Map<String, Object> body,
            Authentication authentication,
            HttpServletRequest request) {

        String url = aiServiceConfig.getAiServiceUrl() + "/orchestrator/stream";
        String userId = getCurrentUserId(authentication);
        String jwtToken = extractJwtToken(request);
        body.putIfAbsent("user_id", userId);
        String jsonBody;
        try {
            jsonBody = objectMapper.writeValueAsString(body);
        } catch (Exception e) {
            log.error("JSON 序列化失败: {}", e.getMessage());
            return buildSseError("抱歉，请求参数处理失败，请稍后重试。");
        }

        log.debug("转发 LangGraph 流式编排: userId={}", userId);

        SecurityContext capturedContext = SecurityContextHolder.getContext();
        String secretHeader = aiServiceConfig.getInternalSecretHeader();
        String secretValue = aiServiceConfig.getInternalSecret();

        StreamingResponseBody stream = outputStream -> {
            if (capturedContext != null) {
                SecurityContextHolder.setContext(capturedContext);
            }

            HttpURLConnection conn = null;
            try {
                java.net.URL targetUrl = new java.net.URL(url);
                conn = (HttpURLConnection) targetUrl.openConnection();
                conn.setRequestMethod("POST");
                conn.setDoOutput(true);
                conn.setDoInput(true);
                conn.setConnectTimeout(5000);
                conn.setReadTimeout(300000);
                conn.setUseCaches(false);

                conn.setRequestProperty("Content-Type", "application/json");
                conn.setRequestProperty(secretHeader, secretValue);
                if (jwtToken != null && !jwtToken.isEmpty()) {
                    conn.setRequestProperty("Authorization", "Bearer " + jwtToken);
                }

                try (java.io.OutputStream os = conn.getOutputStream()) {
                    os.write(jsonBody.getBytes(StandardCharsets.UTF_8));
                    os.flush();
                }

                int status = conn.getResponseCode();
                log.debug("LangGraph 编排服务响应状态: {}", status);

                InputStream is = (status >= 200 && status < 300) ? conn.getInputStream() : conn.getErrorStream();
                if (is == null) {
                    log.error("LangGraph 编排服务无响应流，status={}", status);
                    writeSseMessage(outputStream, "抱歉，AI 编排服务无响应，请稍后重试。");
                    return;
                }

                try (InputStreamReader isr = new InputStreamReader(is, StandardCharsets.UTF_8);
                     BufferedReader br = new BufferedReader(isr)) {

                    String line;
                    boolean gotAnyData = false;
                    while ((line = br.readLine()) != null) {
                        if (line.startsWith("data:")) {
                            gotAnyData = true;
                            outputStream.write((line + "\n\n").getBytes(StandardCharsets.UTF_8));
                            outputStream.flush();
                        }
                    }

                    if (!gotAnyData) {
                        log.warn("LangGraph 编排服务未返回任何 SSE data 行");
                        writeSseMessage(outputStream, "AI 编排服务未返回有效内容，请稍后重试。");
                    }
                }

            } catch (java.net.ConnectException ce) {
                log.error("无法连接到 LangGraph 编排服务({}): {}", url, ce.getMessage());
                writeSseMessage(outputStream, "抱歉，AI 编排服务未启动，请联系管理员。");
            } catch (java.net.SocketTimeoutException te) {
                log.error("连接 LangGraph 编排服务超时: {}", te.getMessage());
                writeSseMessage(outputStream, "抱歉，AI 编排服务响应超时，请稍后重试。");
            } catch (Exception e) {
                log.error("LangGraph 流式编排异常: {}", e.getMessage(), e);
                writeSseMessage(outputStream, "抱歉，发生了错误，请稍后重试。");
            } finally {
                SecurityContextHolder.clearContext();
                if (conn != null) {
                    try {
                        conn.disconnect();
                    } catch (Exception ignored) {
                    }
                }
            }
        };

        HttpHeaders responseHeaders = new HttpHeaders();
        responseHeaders.setContentType(MediaType.TEXT_EVENT_STREAM);
        responseHeaders.setCacheControl(CacheControl.noCache());
        responseHeaders.setConnection("keep-alive");
        responseHeaders.set("X-Accel-Buffering", "no");

        return new ResponseEntity<>(stream, responseHeaders, HttpStatus.OK);
    }

    @GetMapping("/orchestrator/health")
    public ResponseEntity<Map<String, Object>> orchestratorHealth(HttpServletRequest request) {
        return forwardGet("/orchestrator/health", null, request);
    }

    @GetMapping("/orchestrator/history/{sessionId}")
    public ResponseEntity<Map<String, Object>> getOrchestratorHistory(
            @PathVariable String sessionId,
            Authentication authentication,
            HttpServletRequest request) {
        // 转发到 Python 服务的 conversation API
        return forwardGet("/conversations/" + sessionId, authentication, request);
    }

    // ============ 对话管理 (Conversations) ============

    @GetMapping("/conversations")
    public ResponseEntity<Map<String, Object>> getConversations(
            @RequestParam(required = false) String module,
            @RequestParam(required = false) String user_id,
            @RequestParam(defaultValue = "20") int limit,
            @RequestParam(defaultValue = "0") int offset,
            Authentication authentication,
            HttpServletRequest request) {
        
        // 从 JWT 中获取 user_id，如果前端没传的话
        String actualUserId = (user_id != null && !user_id.isEmpty()) ? user_id : getCurrentUserId(authentication);
        
        String path = "/conversations?user_id=" + actualUserId + 
                      (module != null ? "&module=" + module : "") + 
                      "&limit=" + limit + "&offset=" + offset;
        
        return forwardGet(path, authentication, request);
    }

    @GetMapping("/conversations/{sessionId}")
    public ResponseEntity<Map<String, Object>> getConversationDetail(
            @PathVariable String sessionId,
            Authentication authentication,
            HttpServletRequest request) {
        return forwardGet("/conversations/" + sessionId, authentication, request);
    }

    @DeleteMapping("/conversations/{sessionId}")
    public ResponseEntity<Map<String, Object>> deleteConversation(
            @PathVariable String sessionId,
            Authentication authentication,
            HttpServletRequest request) {
        return forwardDelete("/conversations/" + sessionId, authentication, request);
    }

    // ============ 健康检查 ============

    @GetMapping("/health")
    public ResponseEntity<Map<String, Object>> aiServiceHealth(HttpServletRequest request) {
        Map<String, Object> result = new HashMap<>();
        result.put("gateway", "healthy");
        result.put("gateway_service", "planhub-java-ai-gateway");
        
        // 检查 Python AI 服务是否可用
        try {
            Map<String, Object> pythonStatus = forwardGet("/health", null, request).getBody();
            result.put("ai_service", pythonStatus);
        } catch (Exception e) {
            Map<String, Object> unavailable = new HashMap<>();
            unavailable.put("status", "unavailable");
            unavailable.put("detail", e.getMessage());
            result.put("ai_service", unavailable);
        }
        
        return ResponseEntity.ok(result);
    }
}
