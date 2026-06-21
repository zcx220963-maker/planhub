package com.planhub.controller;

import com.planhub.config.AiServiceConfig;
import com.planhub.entity.RagBm25Index;
import com.planhub.entity.RagDocument;
import com.planhub.exception.BusinessException;
import com.planhub.mapper.RagBm25IndexMapper;
import com.planhub.mapper.RagDocumentMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.*;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestTemplate;

import jakarta.servlet.http.HttpServletRequest;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * RAG 知识库管理 Controller（MySQL 存储 + 转发到 Python）
 *
 * 工作流程：
 * 1. 上传文档：先转发到 Python 切分/向量化，再写 MySQL 元数据
 * 2. 查询列表：从 MySQL 查询（保证 user_id 隔离）
 * 3. 删除文档：MySQL 软删除 + 通知 Python 清理 Chroma + 删 BM25 索引
 */
@Slf4j
@RestController
@RequestMapping("/api/ai/rag-v2")
@RequiredArgsConstructor
public class RagController {

    private final RestTemplate aiRestTemplate;
    private final AiServiceConfig aiServiceConfig;

    @Autowired
    private RagDocumentMapper ragDocumentMapper;

    @Autowired
    private RagBm25IndexMapper ragBm25IndexMapper;

    /**
     * 从 Authentication 中获取用户 ID
     */
    private Long getCurrentUserId(Authentication authentication) {
        if (authentication != null && authentication.getPrincipal() != null) {
            try {
                return Long.valueOf(String.valueOf(authentication.getPrincipal()));
            } catch (NumberFormatException e) {
                throw new BusinessException("用户ID格式错误");
            }
        }
        throw new BusinessException("未登录");
    }

    /**
     * 获取用户的所有 RAG 文档（从 MySQL）
     */
    @GetMapping("/documents")
    public ResponseEntity<Map<String, Object>> listDocuments(Authentication authentication) {
        Long userId = getCurrentUserId(authentication);
        List<RagDocument> docs = ragDocumentMapper.findActiveByUserId(userId);

        List<Map<String, Object>> result = docs.stream().map(d -> {
            Map<String, Object> map = new HashMap<>();
            map.put("id", d.getId());
            map.put("doc_id", String.valueOf(d.getId()));  // 兼容前端字段
            map.put("filename", d.getFilename());
            map.put("file_size", d.getFileSize());
            map.put("chunk_count", d.getChunkCount());
            map.put("created_at", d.getCreatedAt());
            return map;
        }).collect(Collectors.toList());

        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("documents", result);
        response.put("total", result.size());
        return ResponseEntity.ok(response);
    }

    /**
     * 删除 RAG 文档
     * 1. 校验归属
     * 2. 通知 Python 清理 Chroma
     * 3. 删 BM25 索引
     * 4. MySQL 软删除
     */
    @DeleteMapping("/documents/{docId}")
    public ResponseEntity<Map<String, Object>> deleteDocument(
            @PathVariable String docId,
            Authentication authentication) {
        Long userId = getCurrentUserId(authentication);

        // 1. 校验
        RagDocument doc = ragDocumentMapper.selectById(docId);
        if (doc == null || !"active".equals(doc.getStatus())) {
            throw new BusinessException("文档不存在");
        }
        if (!doc.getUserId().equals(userId)) {
            throw new BusinessException("无权删除此文档");
        }

        // 2. 通知 Python 清理 Chroma（用 doc_id 精确删除，需传 user_id 确保删除正确的用户 collection）
        try {
            String url = aiServiceConfig.getAiServiceUrl() + "/rag/internal/documents/" + docId + "?user_id=" + userId;
            HttpHeaders headers = new HttpHeaders();
            headers.set(aiServiceConfig.getInternalSecretHeader(), aiServiceConfig.getInternalSecret());
            HttpEntity<String> entity = new HttpEntity<>(headers);
            aiRestTemplate.exchange(url, HttpMethod.DELETE, entity, String.class);
            log.info("[RAG Delete] 已通知 Python 清理 Chroma docId={}, userId={}", docId, userId);
        } catch (Exception e) {
            log.error("[RAG Delete] 通知 Python 失败，继续删除 MySQL", e);
        }

        // 3. 删 BM25 倒排索引
        int bm25Deleted = ragBm25IndexMapper.deleteByDocId(docId);

        // 4. 软删除 MySQL
        ragDocumentMapper.softDeleteById(docId);

        Map<String, Object> details = new HashMap<>();
        details.put("bm25_chunks_deleted", bm25Deleted);
        details.put("mysql_soft_deleted", true);

        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("message", "文档已删除");
        response.put("details", details);
        return ResponseEntity.ok(response);
    }

    /**
     * 记录新上传的文档（Python 上传成功后回调此接口写入 MySQL）
     */
    @PostMapping("/documents/record")
    public ResponseEntity<Map<String, Object>> recordDocument(
            @RequestBody Map<String, Object> body,
            HttpServletRequest request) {
        // 内部密钥鉴权（Python 内部调用时使用，跳过 JWT）
        String internalSecret = request.getHeader(aiServiceConfig.getInternalSecretHeader());
        Long userId;
        if (internalSecret != null && aiServiceConfig.getInternalSecret().equals(internalSecret)) {
            // 内部调用：用 header 中的 user_id 或默认 1
            String uidHeader = request.getHeader("X-User-Id");
            userId = uidHeader != null ? Long.valueOf(uidHeader) : 1L;
        } else {
            // 外部调用：必须带 JWT
            throw new BusinessException("请登录后操作");
        }

        String filename = (String) body.getOrDefault("filename", "unknown");
        Long fileSize = body.get("file_size") != null
            ? ((Number) body.get("file_size")).longValue() : 0L;
        Integer chunkCount = body.get("chunk_count") != null
            ? ((Number) body.get("chunk_count")).intValue() : 0;

        RagDocument doc = RagDocument.builder()
            .id((String) body.get("doc_id"))  // Python 已生成 uuid doc_id
            .userId(userId)
            .filename(filename)
            .fileSize(fileSize)
            .chunkCount(chunkCount)
            .status("active")
            .build();
        ragDocumentMapper.insert(doc);

        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("doc_id", doc.getId());
        return ResponseEntity.ok(response);
    }

    /**
     * 内部接口 - 批量写入 BM25 倒排索引（由 Python AI 服务调用）
     */
    @PostMapping("/internal/bm25/batch")
    public ResponseEntity<Map<String, Object>> batchInsertBm25(@RequestBody Map<String, Object> body) {
        // 验证内部密钥
        HttpServletRequest request = ((org.springframework.web.context.request.ServletRequestAttributes)
            org.springframework.web.context.request.RequestContextHolder.currentRequestAttributes()).getRequest();
        String providedSecret = request.getHeader(aiServiceConfig.getInternalSecretHeader());
        if (!aiServiceConfig.getInternalSecret().equals(providedSecret)) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED)
                .body(Map.of("success", false, "error", "Invalid secret"));
        }

        @SuppressWarnings("unchecked")
        List<Map<String, Object>> items = (List<Map<String, Object>>) body.get("items");
        if (items == null || items.isEmpty()) {
            return ResponseEntity.ok(Map.of("success", true, "inserted", 0));
        }

        int inserted = 0;
        for (Map<String, Object> item : items) {
            try {
                RagBm25Index idx = new RagBm25Index();
                idx.setDocId(String.valueOf(item.get("doc_id")));
                idx.setChunkIndex(((Number) item.get("chunk_index")).intValue());
                idx.setTerm(String.valueOf(item.get("term")));
                idx.setTf(((Number) item.get("tf")).intValue());
                idx.setChunkLength(((Number) item.getOrDefault("chunk_length", 0)).intValue());
                idx.setContent((String) item.get("content"));
                idx.setDocName((String) item.get("doc_name"));
                ragBm25IndexMapper.insert(idx);
                inserted++;
            } catch (Exception e) {
                log.warn("[BM25 Insert] 单条失败: {}", e.getMessage());
            }
        }

        return ResponseEntity.ok(Map.of("success", true, "inserted", inserted));
    }
}
