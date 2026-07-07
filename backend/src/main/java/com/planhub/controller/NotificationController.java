package com.planhub.controller;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.planhub.dto.response.ApiResponse;
import com.planhub.entity.Notification;
import com.planhub.service.NotificationService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/notifications")
@RequiredArgsConstructor
public class NotificationController {
    private final NotificationService notificationService;

    @GetMapping
    public ResponseEntity<ApiResponse<IPage<Notification>>> getNotifications(
            Authentication authentication,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int size) {
        Long userId = (Long) authentication.getPrincipal();
        IPage<Notification> notifications = notificationService.getNotifications(userId, page, size);
        return ResponseEntity.ok(ApiResponse.success(notifications));
    }

    @GetMapping("/unread-count")
    public ResponseEntity<ApiResponse<Long>> getUnreadCount(Authentication authentication) {
        Long userId = (Long) authentication.getPrincipal();
        long count = notificationService.getUnreadCount(userId);
        return ResponseEntity.ok(ApiResponse.success(count));
    }

    @PutMapping("/{notificationId}/read")
    public ResponseEntity<ApiResponse<Void>> markAsRead(
            Authentication authentication,
            @PathVariable Long notificationId) {
        Long userId = (Long) authentication.getPrincipal();
        notificationService.markAsRead(notificationId, userId);
        return ResponseEntity.ok(ApiResponse.success(null, "已标记为已读"));
    }

    @PutMapping("/read-all")
    public ResponseEntity<ApiResponse<Void>> markAllAsRead(Authentication authentication) {
        Long userId = (Long) authentication.getPrincipal();
        notificationService.markAllAsRead(userId);
        return ResponseEntity.ok(ApiResponse.success(null, "全部已标记为已读"));
    }

    @DeleteMapping("/{notificationId}")
    public ResponseEntity<ApiResponse<Void>> deleteNotification(
            Authentication authentication,
            @PathVariable Long notificationId) {
        Long userId = (Long) authentication.getPrincipal();
        notificationService.deleteNotification(notificationId, userId);
        return ResponseEntity.ok(ApiResponse.success(null, "删除成功"));
    }

    @PutMapping("/read-multiple")
    public ResponseEntity<ApiResponse<Void>> markMultipleAsRead(
            Authentication authentication,
            @RequestBody java.util.List<Long> notificationIds) {
        Long userId = (Long) authentication.getPrincipal();
        notificationService.markMultipleAsRead(notificationIds, userId);
        return ResponseEntity.ok(ApiResponse.success(null, "已标记为已读"));
    }

    @DeleteMapping("/batch")
    public ResponseEntity<ApiResponse<Void>> deleteMultipleNotifications(
            Authentication authentication,
            @RequestBody java.util.List<Long> notificationIds) {
        Long userId = (Long) authentication.getPrincipal();
        notificationService.deleteMultipleNotifications(notificationIds, userId);
        return ResponseEntity.ok(ApiResponse.success(null, "删除成功"));
    }
}
