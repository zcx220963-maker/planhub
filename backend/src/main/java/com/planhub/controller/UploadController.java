package com.planhub.controller;

import com.planhub.dto.response.ApiResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

@Slf4j
@RestController
@RequestMapping("/api/upload")
public class UploadController {

    @Value("${upload.dir:./uploads}")
    private String uploadDir;

    /** 允许的图片 MIME 类型白名单 */
    private static final java.util.Set<String> ALLOWED_IMAGE_TYPES = java.util.Set.of(
            "image/jpeg", "image/png", "image/gif", "image/webp"
    );

    /** 允许的图片扩展名白名单 */
    private static final java.util.Set<String> ALLOWED_EXTENSIONS = java.util.Set.of(
            ".jpg", ".jpeg", ".png", ".gif", ".webp"
    );

    /** 单个文件最大 10MB */
    private static final long MAX_FILE_SIZE = 10 * 1024 * 1024;

    @PostMapping("/image")
    public ResponseEntity<ApiResponse<Map<String, String>>> uploadImage(
            @RequestParam("file") MultipartFile file,
            Authentication authentication) {
        try {
            // 校验文件类型
            String contentType = file.getContentType();
            if (contentType == null || !ALLOWED_IMAGE_TYPES.contains(contentType.toLowerCase())) {
                return ResponseEntity.badRequest()
                        .body(ApiResponse.error("不支持的文件类型: " + contentType));
            }

            // 校验文件扩展名（防止伪造 Content-Type）
            String originalFilename = file.getOriginalFilename();
            String extension = originalFilename != null && originalFilename.contains(".")
                    ? originalFilename.substring(originalFilename.lastIndexOf(".")).toLowerCase()
                    : "";
            if (!ALLOWED_EXTENSIONS.contains(extension)) {
                return ResponseEntity.badRequest()
                        .body(ApiResponse.error("不支持的文件扩展名: " + extension));
            }

            // 校验文件大小
            if (file.getSize() > MAX_FILE_SIZE) {
                return ResponseEntity.badRequest()
                        .body(ApiResponse.error("文件过大，最大允许 10MB"));
            }

            String filename = UUID.randomUUID().toString() + extension;

            Path uploadPath = Paths.get(uploadDir);
            if (!Files.exists(uploadPath)) {
                Files.createDirectories(uploadPath);
            }

            Path filePath = uploadPath.resolve(filename);
            Files.copy(file.getInputStream(), filePath);

            String fileUrl = "/uploads/" + filename;

            Map<String, String> result = new HashMap<>();
            result.put("url", fileUrl);

            return ResponseEntity.ok(ApiResponse.success(result, "图片上传成功"));
        } catch (IOException e) {
            log.error("图片上传失败", e);
            throw new RuntimeException("图片上传失败", e);
        }
    }
}
