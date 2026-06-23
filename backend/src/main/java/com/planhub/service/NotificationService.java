package com.planhub.service;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.planhub.entity.Notification;

public interface NotificationService {
    IPage<Notification> getNotifications(Long userId, int page, int size);

    long getUnreadCount(Long userId);

    void markAsRead(Long notificationId, Long userId);

    void markAllAsRead(Long userId);

    void deleteNotification(Long notificationId, Long userId);

    void markMultipleAsRead(java.util.List<Long> notificationIds, Long userId);

    void deleteMultipleNotifications(java.util.List<Long> notificationIds, Long userId);

    Notification createPostLikeNotification(Long postAuthorId, Long likerId, Long postId);

    Notification createPostCommentNotification(Long postAuthorId, Long commenterId, Long postId);

    Notification createCommentLikeNotification(Long commentAuthorId, Long likerId, Long commentId, Long postId);

    Notification createCommentReplyNotification(Long parentCommentAuthorId, Long replierId, Long commentId, Long postId);

    Notification createPostShareNotification(Long postAuthorId, Long sharerId, Long originalPostId);
}
